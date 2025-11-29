"""User endpoint handlers for Rinnai account data.

This module provides the User class for retrieving user account
information and associated devices from the Rinnai cloud API.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from .const import (
    GET_PAYLOAD_HEADERS,
    GET_USER_QUERY,
    GRAPHQL_ENDPOINT,
    build_graphql_payload,
)
from .errors import RequestError

if TYPE_CHECKING:
    from .types import UserInfo

# Type alias for the request function
RequestFunc = Callable[..., Awaitable[dict[str, Any] | str]]


class User:
    """Handler for user-related API endpoints.

    Provides methods to retrieve user account information including
    associated devices and their current states.

    Attributes:
        _request: The authenticated request function from the API class.
        _user_id: The user's email address used for queries.
    """

    def __init__(self, request: RequestFunc, user_id: str) -> None:
        """Initialize the User handler.

        Args:
            request: The authenticated request function from the API class.
            user_id: The user's email address.
        """
        self._request: RequestFunc = request
        self._user_id: str = user_id

    async def get_info(self) -> UserInfo | None:
        """Retrieve the user's account information and devices.

        Returns:
            A UserInfo dictionary containing user account data, including:
            - User profile information (name, email, address, etc.)
            - List of associated devices with their current states
            - Device schedules and configuration

            Returns None if no user data is found.

        Raises:
            RequestError: If the API request fails or returns an error.
        """
        payload = build_graphql_payload(GET_USER_QUERY, {"email": self._user_id})

        response = await self._request(
            "post",
            GRAPHQL_ENDPOINT,
            data=payload,
            headers=GET_PAYLOAD_HEADERS,
        )

        if isinstance(response, str):
            return None

        # Check for GraphQL errors
        if "errors" in response:
            errors = response.get("errors", [])
            error_messages = [e.get("message", "Unknown error") for e in errors]
            raise RequestError(f"GraphQL errors: {'; '.join(error_messages)}")

        data = response.get("data")
        if data is None:
            return None

        user_by_email = data.get("getUserByEmail")
        if user_by_email is None:
            return None

        items: list[UserInfo] = user_by_email.get("items", [])
        if items:
            return items[0]

        return None
