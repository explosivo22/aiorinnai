"""Rinnai Control-R API client with AWS Cognito authentication.

This module provides the main API class for authenticating with the Rinnai
cloud service and making authenticated requests to device and user endpoints.
"""
from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, cast

import attr
import boto3
import botocore
import pycognito
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientPayloadError,
    ClientResponseError,
    ServerConnectionError,
)
from botocore.exceptions import BotoCoreError, ClientError
from urllib.parse import urlparse

from .const import CLIENT_ID, LOGGER, POOL_ID, POOL_REGION
from .device import Device
from .errors import (
    AWS_EXCEPTIONS,
    CloudError,
    PasswordChangeRequired,
    RequestError,
    Unauthenticated,
    UnknownError,
    UserExists,
    UserNotConfirmed,
    UserNotFound,
)
from .user import User

# Retry configuration for transient network errors
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_RETRY_MULTIPLIER = 2.0

# Default request timeout in seconds
DEFAULT_TIMEOUT = 30.0

# Default executor timeout in seconds
DEFAULT_EXECUTOR_TIMEOUT = 30.0

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (ClientConnectorError, ServerConnectionError)


@attr.s
class API:
    """Rinnai Control-R API client.

    Handles authentication via AWS Cognito and provides methods to interact
    with Rinnai water heater devices through GraphQL and shadow endpoints.

    Args:
        session: Optional aiohttp ClientSession for connection pooling.
            If not provided, a session will be created internally.
        timeout: Request timeout in seconds. Defaults to 30 seconds.
        retry_count: Number of retry attempts for transient errors. Defaults to 3.
        retry_delay: Initial delay between retries in seconds. Defaults to 1.0.
        retry_multiplier: Multiplier for exponential backoff. Defaults to 2.0.
        executor_timeout: Timeout for blocking executor calls in seconds. Defaults to 30.0.

    Attributes:
        username: The user's email address used for authentication.
        device: Device endpoint handler for device commands. Available after login.
        user: User endpoint handler for user data. Available after login.

    Example:
        ```python
        # As context manager (recommended)
        async with API() as api:
            await api.async_login("user@example.com", "password")
            user_info = await api.user.get_info()

        # With custom session for connection pooling
        async with aiohttp.ClientSession() as session:
            async with API(session=session) as api:
                await api.async_login("user@example.com", "password")
                user_info = await api.user.get_info()

        # With custom retry configuration
        async with API(retry_count=5, retry_delay=2.0) as api:
            await api.async_login("user@example.com", "password")
        ```
    """

    # Public constructor parameters
    session: ClientSession | None = attr.ib(default=None)
    timeout: float = attr.ib(default=DEFAULT_TIMEOUT)
    retry_count: int = attr.ib(default=DEFAULT_RETRY_COUNT)
    retry_delay: float = attr.ib(default=DEFAULT_RETRY_DELAY)
    retry_multiplier: float = attr.ib(default=DEFAULT_RETRY_MULTIPLIER)
    executor_timeout: float = attr.ib(default=DEFAULT_EXECUTOR_TIMEOUT)

    # Authentication credentials
    username: str | None = attr.ib(default=None, init=False)
    _code_type: str | None = attr.ib(default=None, init=False)

    # JWT tokens from Cognito
    _id_token: str | None = attr.ib(default=None, init=False)
    _access_token: str | None = attr.ib(default=None, init=False)
    _refresh_token: str | None = attr.ib(default=None, init=False)
    _client_secret: str | None = attr.ib(default=None, init=False)

    # AWS Cognito configuration
    _user_pool_id: str = attr.ib(default=POOL_ID, init=False)
    _client_id: str = attr.ib(default=CLIENT_ID, init=False)
    _pool_region: str = attr.ib(default=POOL_REGION, init=False)

    # Session management (internal)
    _session: ClientSession | None = attr.ib(default=None, init=False)
    _owns_session: bool = attr.ib(default=False, init=False)
    _boto_session: boto3.Session | None = attr.ib(default=None, init=False)
    _request_lock: asyncio.Lock = attr.ib(factory=asyncio.Lock, init=False)
    _token_refresh_lock: asyncio.Lock = attr.ib(factory=asyncio.Lock, init=False)

    # Endpoint handlers (initialized after login)
    device: Device | None = attr.ib(default=None, init=False)
    user: User | None = attr.ib(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        """Initialize session ownership after attrs construction."""
        if self.session is not None:
            self._session = self.session
            self._owns_session = False
        else:
            self._owns_session = True

    async def __aenter__(self) -> "API":
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager and close resources."""
        await self.close()

    @property
    def is_connected(self) -> bool:
        """Check if the API client has an active session and valid tokens.

        Returns:
            True if connected with valid authentication tokens, False otherwise.
        """
        return (
            self._session is not None
            and not self._session.closed
            and self._id_token is not None
        )

    def _get_session(self) -> ClientSession:
        """Get or create an aiohttp ClientSession.

        Returns:
            The active ClientSession for making HTTP requests.

        Raises:
            RuntimeError: If called after the session has been closed.
        """
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                timeout=ClientTimeout(total=self.timeout)
            )
            self._owns_session = True
        return self._session

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any] | str:
        """Make an authenticated request against the API with retry logic.

        Automatically refreshes the JWT token if needed before making the request.
        Implements exponential backoff retry for transient network errors.

        Args:
            method: HTTP method (get, post, patch, etc.).
            url: The full URL to request.
            **kwargs: Additional arguments passed to aiohttp request.

        Returns:
            The JSON response as a dictionary, or "success" string for simple responses.

        Raises:
            RequestError: If the request fails after all retry attempts.
        """
        await self.async_check_token()

        kwargs.setdefault("headers", {})
        kwargs["headers"]["Host"] = urlparse(url).netloc

        if self._id_token:
            kwargs["headers"]["Authorization"] = f"Bearer {self._id_token}"

        session = self._get_session()
        last_error: Exception | None = None
        delay = self.retry_delay

        for attempt in range(self.retry_count):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    text = await resp.text()
                    if text == "success":
                        return text
                    data: dict[str, Any] = await resp.json(content_type=None)
                    resp.raise_for_status()
                    return data

            except RETRYABLE_EXCEPTIONS as err:
                last_error = err
                if attempt < self.retry_count - 1:
                    LOGGER.debug(
                        "Transient error on attempt %d/%d for %s: %s. Retrying in %.1fs",
                        attempt + 1,
                        self.retry_count,
                        url,
                        err,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= self.retry_multiplier
                continue

            except ClientResponseError as err:
                raise RequestError(
                    f"HTTP {err.status} response error for {url}: {err.message}"
                ) from err

            except ClientPayloadError as err:
                raise RequestError(
                    f"Payload error while requesting {url}: {err}"
                ) from err

            except ClientError as err:
                raise RequestError(
                    f"Client error while requesting {url}: {err}"
                ) from err

        # All retries exhausted
        raise RequestError(
            f"Request to {url} failed after {self.retry_count} attempts: {last_error}"
        ) from last_error

    async def _update_token(
        self,
        id_token: str,
        access_token: str,
        refresh_token: str | None = None,
    ) -> None:
        """Update stored authentication tokens and initialize endpoint handlers.

        Args:
            id_token: The JWT ID token from Cognito.
            access_token: The JWT access token from Cognito.
            refresh_token: Optional refresh token for token renewal.
        """
        self._id_token = id_token
        self._access_token = access_token
        if refresh_token is not None:
            self._refresh_token = refresh_token

        if not self.device:
            self.device = Device(self._request)

        if not self.user and self.username:
            self.user = User(self._request, self.username)

    async def async_login(
        self,
        email: str,
        password: str,
    ) -> None:
        """Authenticate with the Rinnai API using email and password.

        Performs SRP authentication against AWS Cognito and stores the
        resulting JWT tokens for subsequent API calls.

        Args:
            email: The user's email address.
            password: The user's password.

        Raises:
            Unauthenticated: If credentials are invalid.
            UserNotFound: If the user account doesn't exist.
            UserNotConfirmed: If the user hasn't confirmed their email.
            PasswordChangeRequired: If a password reset is required.
            UnknownError: For other AWS Cognito errors.
            asyncio.TimeoutError: If the Cognito request times out.
        """
        loop = asyncio.get_running_loop()
        self.username = email

        try:
            cognito = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    partial(self._create_cognito_client, username=email),
                ),
                timeout=self.executor_timeout,
            )
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    partial(cognito.authenticate, password=password),
                ),
                timeout=self.executor_timeout,
            )

            await self._update_token(
                cast(str, cognito.id_token),
                cast(str, cognito.access_token),
                cast(str, cognito.refresh_token),
            )

        except ClientError as err:
            raise _map_aws_exception(err) from err

        except BotoCoreError as err:
            raise UnknownError(str(err)) from err

    async def async_check_token(self) -> None:
        """Check token validity and refresh if necessary.

        This method is called automatically before each API request.
        Uses a dedicated token refresh lock to prevent concurrent refresh attempts
        while allowing other operations to proceed.

        Raises:
            Unauthenticated: If token refresh fails due to invalid credentials.
            UserNotFound: If the user account no longer exists.
        """
        async with self._token_refresh_lock:
            if self._access_token is None or self._refresh_token is None:
                return  # No tokens to check

            cognito = await self._async_authenticated_cognito()
            if not cognito.check_token(renew=False):
                return

            try:
                await self.async_renew_access_token()
            except (Unauthenticated, UserNotFound) as err:
                LOGGER.error("Unable to refresh token: %s", err)
                raise

    async def async_renew_access_token(
        self,
        email: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Renew the access token using the refresh token.

        Args:
            email: Optional email to update (uses stored value if None).
            access_token: Optional access token to update.
            refresh_token: Optional refresh token to update.

        Raises:
            Unauthenticated: If the refresh token is invalid.
            UnknownError: For other AWS errors.
            asyncio.TimeoutError: If the Cognito request times out.
        """
        loop = asyncio.get_running_loop()
        if email is not None:
            self.username = email
        if access_token is not None:
            self._access_token = access_token
        if refresh_token is not None:
            self._refresh_token = refresh_token

        cognito = await self._async_authenticated_cognito()

        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, cognito.renew_access_token),
                timeout=self.executor_timeout,
            )
            await self._update_token(
                cast(str, cognito.id_token),
                cast(str, cognito.access_token),
            )

        except ClientError as err:
            raise _map_aws_exception(err) from err

        except BotoCoreError as err:
            raise UnknownError(str(err)) from err

    async def _async_authenticated_cognito(self) -> pycognito.Cognito:
        """Get an authenticated Cognito client instance.

        Returns:
            A pycognito.Cognito instance configured with current tokens.

        Raises:
            Unauthenticated: If no authentication tokens are available.
            asyncio.TimeoutError: If the Cognito client creation times out.
        """
        if self._access_token is None or self._refresh_token is None:
            raise Unauthenticated("No authentication tokens available")

        loop = asyncio.get_running_loop()

        return await asyncio.wait_for(
            loop.run_in_executor(
                None,
                partial(
                    self._create_cognito_client,
                    access_token=self._access_token,
                    refresh_token=self._refresh_token,
                ),
            ),
            timeout=self.executor_timeout,
        )

    def _create_cognito_client(self, **kwargs: Any) -> pycognito.Cognito:
        """Create a new Cognito client instance.

        Note: This method performs blocking I/O and should be called
        via run_in_executor.

        Args:
            **kwargs: Arguments passed to pycognito.Cognito constructor.

        Returns:
            A configured pycognito.Cognito instance.
        """
        if self._boto_session is None:
            self._boto_session = boto3.session.Session()

        return pycognito.Cognito(
            user_pool_id=self._user_pool_id,
            client_id=self._client_id,
            user_pool_region=self._pool_region,
            botocore_config=botocore.config.Config(
                signature_version=botocore.UNSIGNED
            ),
            session=self._boto_session,
            **kwargs,
        )

    async def close(self) -> None:
        """Close the API client and release resources.

        This method should be called when the API client is no longer needed.
        Only closes the ClientSession if it was created internally.
        """
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None


def _map_aws_exception(err: ClientError) -> CloudError:
    """Map an AWS ClientError to the appropriate CloudError subclass.

    Args:
        err: The AWS ClientError to map.

    Returns:
        An appropriate CloudError subclass instance.
    """
    error_code = err.response.get("Error", {}).get("Code", "")
    error_message = err.response.get("Error", {}).get("Message", str(err))

    exception_class = AWS_EXCEPTIONS.get(error_code, UnknownError)
    LOGGER.debug("Mapped AWS error %s to %s", error_code, exception_class.__name__)

    return exception_class(error_message)


# Re-export exceptions for backward compatibility
__all__ = [
    "API",
    "CloudError",
    "PasswordChangeRequired",
    "Unauthenticated",
    "UnknownError",
    "UserExists",
    "UserNotConfirmed",
    "UserNotFound",
]