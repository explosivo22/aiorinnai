"""Tests for the aiorinnai library.

This module contains unit tests for the API client, device commands,
and user data retrieval with mocked HTTP responses.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientConnectorError, ClientSession
from aiohttp.client_reqrep import ConnectionKey

from aiorinnai import (
    API,
    APIResponse,
    Device,
    RequestError,
    TemperatureUnit,
    Unauthenticated,
    User,
    UserNotFound,
)
from aiorinnai.types import (
    validate_duration,
    validate_temperature,
    validate_thing_name,
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
            api.retry_delay = 0.01  # Speed up test
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
            api.retry_delay = 0.01  # Speed up test
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

        assert isinstance(result, APIResponse)
        assert result.success is True
        call_args = mock_request.call_args
        assert "set_domestic_temperature" in call_args.kwargs.get("data", "")

    @pytest.mark.asyncio
    async def test_start_recirculation(self) -> None:
        """Test starting recirculation pump."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)

        dev = {"thing_name": "rinnai-thing-123"}
        result = await device.start_recirculation(dev, duration=5)

        assert isinstance(result, APIResponse)
        assert result.success is True
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

        assert isinstance(result, APIResponse)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_turn_on_off(self) -> None:
        """Test turning device on and off."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)

        dev = {"thing_name": "rinnai-thing-123"}

        result_off = await device.turn_off(dev)
        result_on = await device.turn_on(dev)

        assert isinstance(result_off, APIResponse)
        assert isinstance(result_on, APIResponse)
        assert result_off.success is True
        assert result_on.success is True
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
            _ = api._get_session()
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


class TestInputValidation:
    """Tests for input validation functions."""

    def test_validate_temperature_fahrenheit_valid(self) -> None:
        """Test valid Fahrenheit temperatures."""
        assert validate_temperature(100, TemperatureUnit.FAHRENHEIT) == 100
        assert validate_temperature(120, TemperatureUnit.FAHRENHEIT) == 120
        assert validate_temperature(140, TemperatureUnit.FAHRENHEIT) == 140

    def test_validate_temperature_fahrenheit_invalid_low(self) -> None:
        """Test temperature below minimum raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_temperature(99, TemperatureUnit.FAHRENHEIT)
        assert "must be between 100 and 140°F" in str(exc_info.value)
        assert "got 99°F" in str(exc_info.value)

    def test_validate_temperature_fahrenheit_invalid_high(self) -> None:
        """Test temperature above maximum raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_temperature(141, TemperatureUnit.FAHRENHEIT)
        assert "must be between 100 and 140°F" in str(exc_info.value)
        assert "got 141°F" in str(exc_info.value)

    def test_validate_temperature_celsius_valid(self) -> None:
        """Test valid Celsius temperatures with conversion."""
        # 38°C ≈ 100°F
        result = validate_temperature(38, TemperatureUnit.CELSIUS)
        assert result == 100

        # 49°C ≈ 120°F
        result = validate_temperature(49, TemperatureUnit.CELSIUS)
        assert result == 120

        # 60°C = 140°F
        result = validate_temperature(60, TemperatureUnit.CELSIUS)
        assert result == 140

    def test_validate_temperature_celsius_invalid_low(self) -> None:
        """Test Celsius temperature below minimum raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_temperature(37, TemperatureUnit.CELSIUS)
        assert "must be between 38 and 60°C" in str(exc_info.value)

    def test_validate_temperature_celsius_invalid_high(self) -> None:
        """Test Celsius temperature above maximum raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_temperature(61, TemperatureUnit.CELSIUS)
        assert "must be between 38 and 60°C" in str(exc_info.value)

    def test_validate_duration_valid(self) -> None:
        """Test valid recirculation durations."""
        assert validate_duration(1) == 1
        assert validate_duration(30) == 30
        assert validate_duration(60) == 60

    def test_validate_duration_invalid_low(self) -> None:
        """Test duration below minimum raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_duration(0)
        assert "must be between 1 and 60 minutes" in str(exc_info.value)

    def test_validate_duration_invalid_high(self) -> None:
        """Test duration above maximum raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_duration(61)
        assert "must be between 1 and 60 minutes" in str(exc_info.value)

    def test_validate_thing_name_valid(self) -> None:
        """Test valid thing_name extraction."""
        dev = {"thing_name": "rinnai-thing-123"}
        assert validate_thing_name(dev) == "rinnai-thing-123"

    def test_validate_thing_name_missing(self) -> None:
        """Test missing thing_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_thing_name({})
        assert "must have a 'thing_name' attribute" in str(exc_info.value)

    def test_validate_thing_name_empty(self) -> None:
        """Test empty thing_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_thing_name({"thing_name": ""})
        assert "must have a 'thing_name' attribute" in str(exc_info.value)

    def test_validate_thing_name_none(self) -> None:
        """Test None thing_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_thing_name({"thing_name": None})
        assert "must have a 'thing_name' attribute" in str(exc_info.value)


class TestTemperatureUnitConversion:
    """Tests for temperature unit conversion helpers."""

    def test_celsius_to_fahrenheit(self) -> None:
        """Test Celsius to Fahrenheit conversion."""
        assert TemperatureUnit.celsius_to_fahrenheit(0) == 32
        assert TemperatureUnit.celsius_to_fahrenheit(100) == 212
        assert TemperatureUnit.celsius_to_fahrenheit(40) == 104
        assert TemperatureUnit.celsius_to_fahrenheit(60) == 140

    def test_fahrenheit_to_celsius(self) -> None:
        """Test Fahrenheit to Celsius conversion."""
        assert TemperatureUnit.fahrenheit_to_celsius(32) == 0
        assert TemperatureUnit.fahrenheit_to_celsius(212) == 100
        assert TemperatureUnit.fahrenheit_to_celsius(104) == 40
        assert TemperatureUnit.fahrenheit_to_celsius(140) == 60


class TestDeviceValidation:
    """Tests for device methods with input validation."""

    @pytest.mark.asyncio
    async def test_set_temperature_validation_error_low(self) -> None:
        """Test set_temperature with temperature below minimum."""
        mock_request = AsyncMock()
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        with pytest.raises(ValueError) as exc_info:
            await device.set_temperature(dev, 99)
        assert "must be between 100 and 140°F" in str(exc_info.value)
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_temperature_validation_error_high(self) -> None:
        """Test set_temperature with temperature above maximum."""
        mock_request = AsyncMock()
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        with pytest.raises(ValueError) as exc_info:
            await device.set_temperature(dev, 141)
        assert "must be between 100 and 140°F" in str(exc_info.value)
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_temperature_celsius(self) -> None:
        """Test set_temperature with Celsius unit."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        # 49°C ≈ 120°F
        result = await device.set_temperature(dev, 49, TemperatureUnit.CELSIUS)

        assert isinstance(result, APIResponse)
        assert result.success is True
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        data = call_args.kwargs.get("data", "")
        assert "120" in data  # Converted from 49°C

    @pytest.mark.asyncio
    async def test_start_recirculation_validation_error_low(self) -> None:
        """Test start_recirculation with duration below minimum."""
        mock_request = AsyncMock()
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        with pytest.raises(ValueError) as exc_info:
            await device.start_recirculation(dev, duration=0)
        assert "must be between 1 and 60 minutes" in str(exc_info.value)
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_recirculation_validation_error_high(self) -> None:
        """Test start_recirculation with duration above maximum."""
        mock_request = AsyncMock()
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        with pytest.raises(ValueError) as exc_info:
            await device.start_recirculation(dev, duration=61)
        assert "must be between 1 and 60 minutes" in str(exc_info.value)
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_shadow_missing_thing_name(self) -> None:
        """Test _set_shadow raises ValueError for missing thing_name."""
        mock_request = AsyncMock()
        device = Device(mock_request)

        with pytest.raises(ValueError) as exc_info:
            await device.turn_on({})
        assert "must have a 'thing_name' attribute" in str(exc_info.value)
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_enable_vacation_mode(self) -> None:
        """Test enabling vacation mode."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        result = await device.enable_vacation_mode(dev)

        assert isinstance(result, APIResponse)
        assert result.success is True
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        data = call_args.kwargs.get("data", "")
        assert "schedule_holiday" in data
        assert "true" in data.lower()

    @pytest.mark.asyncio
    async def test_disable_vacation_mode(self) -> None:
        """Test disabling vacation mode."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        result = await device.disable_vacation_mode(dev)

        assert isinstance(result, APIResponse)
        assert result.success is True
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        data = call_args.kwargs.get("data", "")
        assert "schedule_holiday" in data
        assert "schedule_enabled" in data

    @pytest.mark.asyncio
    async def test_do_maintenance_retrieval(self) -> None:
        """Test triggering maintenance retrieval."""
        mock_request = AsyncMock(return_value="success")
        device = Device(mock_request)
        dev = {"thing_name": "rinnai-thing-123"}

        result = await device.do_maintenance_retrieval(dev)

        assert isinstance(result, APIResponse)
        assert result.success is True
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        data = call_args.kwargs.get("data", "")
        assert "do_maintenance_retrieval" in data


class TestAPIConfiguration:
    """Tests for configurable API parameters."""

    def test_custom_retry_parameters(self) -> None:
        """Test API accepts custom retry configuration."""
        api = API(
            retry_count=5,
            retry_delay=2.0,
            retry_multiplier=3.0,
        )

        assert api.retry_count == 5
        assert api.retry_delay == 2.0
        assert api.retry_multiplier == 3.0

    def test_custom_executor_timeout(self) -> None:
        """Test API accepts custom executor timeout."""
        api = API(executor_timeout=60.0)
        assert api.executor_timeout == 60.0

    def test_default_retry_parameters(self) -> None:
        """Test API uses default retry configuration."""
        api = API()

        assert api.retry_count == 3
        assert api.retry_delay == 1.0
        assert api.retry_multiplier == 2.0
        assert api.executor_timeout == 30.0

    @pytest.mark.asyncio
    async def test_token_refresh_lock_separate_from_request_lock(
        self, mock_cognito: MagicMock
    ) -> None:
        """Test that token refresh lock is separate from request lock."""
        with patch("aiorinnai.api.pycognito.Cognito", return_value=mock_cognito):
            api = API()
            await api.async_login("test@example.com", "password")

            # Verify both locks exist and are different objects
            assert hasattr(api, "_request_lock")
            assert hasattr(api, "_token_refresh_lock")
            assert api._request_lock is not api._token_refresh_lock
            assert isinstance(api._request_lock, asyncio.Lock)
            assert isinstance(api._token_refresh_lock, asyncio.Lock)

            await api.close()


class TestAPIResponseDataclass:
    """Tests for the APIResponse dataclass."""

    def test_api_response_success(self) -> None:
        """Test creating a successful APIResponse."""
        response = APIResponse(success=True, data={"result": "ok"})
        assert response.success is True
        assert response.data == {"result": "ok"}
        assert response.error is None

    def test_api_response_failure(self) -> None:
        """Test creating a failed APIResponse."""
        response = APIResponse(success=False, error="Something went wrong")
        assert response.success is False
        assert response.data is None
        assert response.error == "Something went wrong"

    def test_api_response_defaults(self) -> None:
        """Test APIResponse default values."""
        response = APIResponse(success=True)
        assert response.success is True
        assert response.data is None
        assert response.error is None
