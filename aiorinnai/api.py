import asyncio
from functools import lru_cache, partial

import boto3
import botocore
from botocore.exceptions import BotoCoreError, ClientError
import pycognito
import attr

from typing import Any, Optional
from urllib.parse import urlparse

from aiohttp import ClientSession
from aiohttp.client_exceptions import (
    ClientResponseError, 
    ClientConnectorError, 
    ServerConnectionError, 
    ClientPayloadError
)

from .errors import RequestError
from .device import Device
from .user import User

from aiorinnai.const import (
    POOL_ID,
    CLIENT_ID,
    POOL_REGION,
    LOGGER
)

class CloudError(Exception):
    """Base class for cloud related errors."""


class Unauthenticated(CloudError):
    """Raised when authentication failed."""


class UserNotFound(CloudError):
    """Raised when a user is not found."""


class UserExists(CloudError):
    """Raised when a username already exists."""


class UserNotConfirmed(CloudError):
    """Raised when a user has not confirmed email yet."""


class PasswordChangeRequired(CloudError):
    """Raised when a password change is required."""

    # https://github.com/PyCQA/pylint/issues/1085
    # pylint: disable=useless-super-delegation
    def __init__(self, message: str = "Password change required.") -> None:
        """Initialize a password change required error."""
        super().__init__(message)

class UnknownError(CloudError):
    """Raised when an unknown error occurs."""

AWS_EXCEPTIONS: dict[str, type[CloudError]] = {
    "UserNotFoundException": UserNotFound,
    "UserNotConfirmedException": UserNotConfirmed,
    "UsernameExistsException": UserExists,
    "NotAuthorizedException": Unauthenticated,
    "PasswordResetRequiredException": PasswordChangeRequired,
}

@attr.s
class API(object):
    # Represents a Rinnai Water Heater, with methods for status and issuing commands

    username = attr.ib(default=None)
    code_type = attr.ib(default=None)

    id_token = attr.ib(default=None)
    access_token = attr.ib(default=None)
    refresh_token = attr.ib(default=None)
    client_secret = attr.ib(default=None)
    expires_at = attr.ib(default=None)

    access_key = attr.ib(default=None)
    secret_key = attr.ib(default=None)
    client_callback = attr.ib(default=None)

    user_pool_id = POOL_ID
    client_id = CLIENT_ID
    pool_region = POOL_REGION
    aws = None
    loop = None
    session: boto3.Session | None = None
    _request_lock = asyncio.Lock()

    device: Optional[Device] = None
    user: Optional[User] = None

    def get_session(self):
        return ClientSession()

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        """Make a request against the API."""
        await self.async_check_token()

        kwargs.setdefault("headers", {})
        kwargs["headers"].update(
            {
                "Host": urlparse(url).netloc,
                #"User-Agent": DEFAULT_HEADER_USER_AGENT,
                #"Accept-Encoding": DEFAULT_HEADER_ACCEPT_ENCODING
            }
        )

        if self.id_token:
            kwargs["headers"]["Authorization"] = "Bearer {}".format(self.id_token)

        session = self.get_session()

        try:
            async with session.request(method, url, **kwargs) as resp:
                data: dict = await resp.json(content_type=None)
                resp.raise_for_status()
                return data

        except ClientResponseError as err:
            raise RequestError(f"There was a response error while requesting {url}: {err}") from err
        except ClientConnectorError as err:
            raise RequestError(f"There was a client connection error while requesting {url}: {err}") from err
        except ServerConnectionError as err:
            raise RequestError(f"There was a server connection error while requesting {url}: {err}") from err
        except ClientPayloadError as err:
            raise RequestError(f"There was a client payload error while requesting {url}: {err}") from err
        except ClientError as err:
            raise RequestError(f"There was the following error while requesting {url}: {err}") from err
        finally:
            await session.close()

    async def update_token(
            self,
            id_token: str,
            access_token: str,
            refresh_token: str | None = None,
    ) -> asyncio.Task | None:
        self.id_token = id_token
        self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token

        if not self.device:
                self.device = Device(self._request)

        if not self.user:
            self.user = User(self._request)

        return None

    async def async_login(self, email: str, password: str = None, access_token: str = None, refresh_token: str = None) -> None:
        self.loop = asyncio.get_event_loop()

        try:
            cognito = await self.loop.run_in_executor(None, partial(self._create_cognito_client, username=email),)
            await self.loop.run_in_executor(None, partial(cognito.authenticate,password=password),)

            task = await self.update_token(cognito.id_token, cognito.access_token, cognito.refresh_token)

            if task:
                await task

        except ClientError as err:
            raise _map_aws_exception(err) from err
        
        except BotoCoreError as err:
            raise UnknownError from err

    async def async_check_token(self) -> None:
        """Check that the token is valid and renew if necessary."""
        async with self._request_lock:
            cognito = await self._async_authenticated_cognito()
            if not cognito.check_token(renew=False):
                return

            try:
                await self.async_renew_access_token()
            except (Unauthenticated, UserNotFound) as err:
                LOGGER.error("Unable to refresh token: %s", err)

                raise

    async def async_renew_access_token(self, access_token: str = None, refresh_token: str = None) -> None:
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        if access_token is not None:
            self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token

        cognito = await self._async_authenticated_cognito()

        try:
            await self.loop.run_in_executor(None, cognito.renew_access_token)
            await self.update_token(cognito.id_token, cognito.access_token)

        except ClientError as err:
            raise _map_aws_exception(err) from err

        except BotoCoreError as err:
            raise UnknownError from err
        
    async def _async_authenticated_cognito(self) -> pycognito.Cognito:
        """Return an authenticated cognito instance."""
        if self.access_token is None or self.refresh_token is None:
            raise Unauthenticated("No authentication found")

        return await self.loop.run_in_executor(
            None,
            partial(
                self._create_cognito_client,
                access_token=self.access_token,
                refresh_token=self.refresh_token,
            ),
        )

    def _create_cognito_client(self, **kwargs: Any) -> pycognito.Cognito:
        """Create a new cognito client.

        NOTE: This will do I/O
        """
        if self.session is None:
            self.session = boto3.session.Session()

        return _cached_cognito(
            user_pool_id=self.user_pool_id,
            client_id=self.client_id,
            user_pool_region=self.pool_region,
            botocore_config=botocore.config.Config(signature_version=botocore.UNSIGNED),
            session=self.session,
            **kwargs,
        )
    
def _map_aws_exception(err: ClientError) -> CloudError:
    """Map AWS exception to our exceptions."""
    ex = AWS_EXCEPTIONS.get(err.response["Error"]["Code"], UnknownError)
    print(ex)
    return ex(err.response["Error"]["Message"])

@lru_cache(maxsize=2)
def _cached_cognito(
    user_pool_id: str,
    client_id: str,
    user_pool_region: str,
    botocore_config: Any,
    session: Any,
    **kwargs: Any,
) -> pycognito.Cognito:
    """Create a cached cognito client.

    NOTE: This will do I/O
    """
    return pycognito.Cognito(
        user_pool_id=user_pool_id,
        client_id=client_id,
        user_pool_region=user_pool_region,
        botocore_config=botocore_config,
        session=session,
        **kwargs,
    )