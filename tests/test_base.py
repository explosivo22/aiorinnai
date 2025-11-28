"""Tests for the aiorinnai library.

This module contains unit tests for the API client, device commands,
and user data retrieval with mocked HTTP responses.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientConnectorError, ClientResponseError, ClientSession
from aiohttp.client_reqrep import ConnectionKey

from aiorinnai import (
    API,
    Device,
    RequestError,
    Unauthenticated,
    UnknownError,
    User,
    UserNotFound,
)


# Sample response data
SAMPLE_USER_RESPONSE: dict[str, Any] = {
    "data": {
        "getUserByEmail": {
            "items": [
                {
                    "id": "user-123",
                    "email": "test@example.com",
                    "name": "Test User",
                    "devices": {
                        "items": [
                            {
                                "id": "device-456",
                                "thing_name": "rinnai-thing-123",
                                "device_name": "Water Heater",
                                "shadow": {
                                    "set_domestic_temperature": 120,
                                    "recirculation_enabled": False,
                                    "operation_enabled": True,
                                },
                            }
                        ]
                    },
                }
            ]
        }
    }
}

SAMPLE_DEVICE_RESPONSE: dict[str, Any] = {
    "data": {
        "getDevice": {
            "id": "device-456",
            "thing_name": "rinnai-thing-123",
            "device_name": "Water Heater",
            "shadow": {
                "set_domestic_temperature": 120,
                "recirculation_enabled": False,
                "operation_enabled": True,
            },
        }
    }
}


@pytest.fixture
def mock_cognito() -> MagicMock:
    """Create a mock Cognito client."""
    cognito = MagicMock()
    cognito.id_token = "mock_id_token"
    cognito.access_token = "mock_access_token"
    cognito.refresh_token = "mock_refresh_token"
    cognito.check_token.return_value = False  # Token is valid
    return cognito


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock aiohttp ClientSession."""
    session = AsyncMock(spec=ClientSession)
    session.closed = False
    return session


class TestAPILogin:
    """Tests for API authentication."""

    @pytest.mark.asyncio
    async def test_login_success(self, mock_cognito: MagicMock) -> None:
        """Test successful login flow."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            api = API()
            await api.async_login("test@example.com", "password123")

            assert api.username == "test@example.com"
            assert api._id_token == "mock_id_token"
            assert api._access_token == "mock_access_token"
            assert api._refresh_token == "mock_refresh_token"
            assert api.device is not None
            assert api.user is not None

            await api.close()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self) -> None:
        """Test login with invalid credentials raises Unauthenticated."""
        from botocore.exceptions import ClientError

        error_response = {
            "Error": {
                "Code": "NotAuthorizedException",
                "Message": "Incorrect username or password.",
            }
        }

        with patch("aiorinnai.api.pycognito.Cognito") as mock_cog:
            mock_cog.return_value.authenticate.side_effect = ClientError(
                error_response, "authenticate"
            )

            api = API()
            with pytest.raises(Unauthenticated) as exc_info:
                await api.async_login("test@example.com", "wrong_password")

            assert "Incorrect username or password" in str(exc_info.value)
            await api.close()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self) -> None:
        """Test login with non-existent user raises UserNotFound."""
        from botocore.exceptions import ClientError

        error_response = {
            "Error": {
                "Code": "UserNotFoundException",
                "Message": "User does not exist.",
            }
        }

        with patch("aiorinnai.api.pycognito.Cognito") as mock_cog:
            mock_cog.return_value.authenticate.side_effect = ClientError(
                error_response, "authenticate"
            )

            api = API()
            with pytest.raises(UserNotFound) as exc_info:
                await api.async_login("nonexistent@example.com", "password")

            assert "User does not exist" in str(exc_info.value)
            await api.close()


class TestAPIRequest:
    """Tests for the API request method with retry logic."""

    @pytest.mark.asyncio
    async def test_request_success(self, mock_cognito: MagicMock) -> None:
        """Test successful API request."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            api = API()
            await api.async_login("test@example.com", "password")

            # Mock the session request with proper async context manager
            mock_response = MagicMock()
            mock_response.text = AsyncMock(return_value='{"result": "ok"}')
            mock_response.json = AsyncMock(return_value={"result": "ok"})
            mock_response.raise_for_status = MagicMock()

            async def mock_context_manager(*args: Any, **kwargs: Any) -> Any:
                return mock_response

            with patch.object(api, "_get_session") as mock_get_session:
                mock_session = MagicMock()
                mock_cm = MagicMock()
                mock_cm.__aenter__ = mock_context_manager
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_session.request.return_value = mock_cm
                mock_get_session.return_value = mock_session

                result = await api._request("get", "https://api.example.com/test")
                assert result == {"result": "ok"}

            await api.close()

    @pytest.mark.asyncio
    async def test_request_retry_on_connection_error(
        self, mock_cognito: MagicMock
    ) -> None:
        """Test that transient connection errors trigger retries."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            api = API()
            api._retry_delay = 0.01  # Speed up test
            await api.async_login("test@example.com", "password")

            # Create a connection error
            conn_key = ConnectionKey(
                host="api.example.com",
                port=443,
                is_ssl=True,
                ssl=None,
                proxy=None,
                proxy_auth=None,
                proxy_headers_hash=None,
            )
            connection_error = ClientConnectorError(conn_key, OSError("Connection refused"))

            mock_response = MagicMock()
            mock_response.text = AsyncMock(return_value='{"result": "ok"}')
            mock_response.json = AsyncMock(return_value={"result": "ok"})
            mock_response.raise_for_status = MagicMock()

            call_count = 0

            async def mock_aenter(*args: Any, **kwargs: Any) -> Any:
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise connection_error
                return mock_response

            with patch.object(api, "_get_session") as mock_get_session:
                mock_session = MagicMock()
                mock_cm = MagicMock()
                mock_cm.__aenter__ = mock_aenter
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_session.request.return_value = mock_cm
                mock_get_session.return_value = mock_session

                # Should succeed after retries
                result = await api._request("get", "https://api.example.com/test")
                assert result == {"result": "ok"}
                assert call_count == 3  # Failed twice, succeeded on third

            await api.close()

    @pytest.mark.asyncio
    async def test_request_fails_after_max_retries(
        self, mock_cognito: MagicMock
    ) -> None:
        """Test that request fails after exhausting retries."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            api = API()
            api._retry_delay = 0.01  # Speed up test
            await api.async_login("test@example.com", "password")

            conn_key = ConnectionKey(
                host="api.example.com",
                port=443,
                is_ssl=True,
                ssl=None,
                proxy=None,
                proxy_auth=None,
                proxy_headers_hash=None,
            )
            connection_error = ClientConnectorError(conn_key, OSError("Connection refused"))

            async def mock_aenter(*args: Any, **kwargs: Any) -> Any:
                raise connection_error

            with patch.object(api, "_get_session") as mock_get_session:
                mock_session = MagicMock()
                mock_cm = MagicMock()
                mock_cm.__aenter__ = mock_aenter
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_session.request.return_value = mock_cm
                mock_get_session.return_value = mock_session

                with pytest.raises(RequestError) as exc_info:
                    await api._request("get", "https://api.example.com/test")

                assert "failed after 3 attempts" in str(exc_info.value)

            await api.close()


class TestDevice:
    """Tests for device commands."""

    @pytest.mark.asyncio
    async def test_get_info(self) -> None:
        """Test retrieving device information."""
        mock_request = AsyncMock(return_value=SAMPLE_DEVICE_RESPONSE)
        device = Device(mock_request)

        result = await device.get_info("device-456")

        assert result == SAMPLE_DEVICE_RESPONSE
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_temperature(self) -> None:
        """Test setting water temperature."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)

        dev = {"thing_name": "rinnai-thing-123"}
        result = await device.set_temperature(dev, 125)

        assert result == "success"
        call_args = mock_request.call_args
        assert "set_domestic_temperature" in call_args.kwargs.get("data", "")

    @pytest.mark.asyncio
    async def test_start_recirculation(self) -> None:
        """Test starting recirculation pump."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)

        dev = {"thing_name": "rinnai-thing-123"}
        result = await device.start_recirculation(dev, duration=5)

        assert result == "success"
        call_args = mock_request.call_args
        data = call_args.kwargs.get("data", "")
        assert "set_recirculation_enabled" in data
        assert '"5"' in data  # Duration is sent as string

    @pytest.mark.asyncio
    async def test_stop_recirculation(self) -> None:
        """Test stopping recirculation pump."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)

        dev = {"thing_name": "rinnai-thing-123"}
        result = await device.stop_recirculation(dev)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_turn_on_off(self) -> None:
        """Test turning device on and off."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)

        dev = {"thing_name": "rinnai-thing-123"}

        await device.turn_off(dev)
        await device.turn_on(dev)

        assert mock_request.call_count == 2


class TestUser:
    """Tests for user data retrieval."""

    @pytest.mark.asyncio
    async def test_get_info(self) -> None:
        """Test retrieving user information."""
        mock_request = AsyncMock(return_value=SAMPLE_USER_RESPONSE)
        user = User(mock_request, "test@example.com")

        result = await user.get_info()

        assert result is not None
        assert result["email"] == "test@example.com"
        assert "devices" in result

    @pytest.mark.asyncio
    async def test_get_info_empty_response(self) -> None:
        """Test get_info returns None when no user data found."""
        empty_response: dict[str, Any] = {
            "data": {"getUserByEmail": {"items": []}}
        }
        mock_request = AsyncMock(return_value=empty_response)
        user = User(mock_request, "unknown@example.com")

        result = await user.get_info()

        assert result is None


class TestSessionManagement:
    """Tests for session lifecycle management."""

    @pytest.mark.asyncio
    async def test_session_created_internally(self) -> None:
        """Test that session is created if not provided."""
        api = API()
        session = api._get_session()

        assert session is not None
        assert api._owns_session is True

        await api.close()

    @pytest.mark.asyncio
    async def test_provided_session_not_closed(self) -> None:
        """Test that externally provided session is not closed by API."""
        external_session = AsyncMock(spec=ClientSession)
        external_session.closed = False

        api = API(session=external_session)

        assert api._session is external_session
        assert api._owns_session is False

        await api.close()

        external_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_internal_session_closed(self, mock_cognito: MagicMock) -> None:
        """Test that internally created session is closed."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            api = API()
            await api.async_login("test@example.com", "password")

            # Force internal session creation
            session = api._get_session()
            assert api._owns_session is True

            await api.close()
            # Session should be set to None after close
            assert api._session is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_cognito: MagicMock) -> None:
        """Test API works as async context manager."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            async with API() as api:
                await api.async_login("test@example.com", "password")
                # Force session creation
                _ = api._get_session()
                assert api.is_connected is True

            # After exiting context, session should be closed
            assert api._session is None

    @pytest.mark.asyncio
    async def test_is_connected_property(self, mock_cognito: MagicMock) -> None:
        """Test is_connected property reflects connection state."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            api = API()

            # Not connected before login (no session, no tokens)
            assert api.is_connected is False

            await api.async_login("test@example.com", "password")
            # Still not connected until session is created
            assert api.is_connected is False

            # Create session - now connected
            _ = api._get_session()
            assert api.is_connected is True

            await api.close()
            # Not connected after close
            assert api.is_connected is False

    @pytest.mark.asyncio
    async def test_custom_timeout(self) -> None:
        """Test that custom timeout is applied."""
        api = API(timeout=60.0)
        assert api.timeout == 60.0

        session = api._get_session()
        # Verify timeout was set (session.timeout.total should be 60)
        assert session.timeout.total == 60.0

        await api.close()
