"""Device endpoint handlers for Rinnai water heater commands.

This module provides the Device class for sending commands to Rinnai
water heaters via the shadow PATCH endpoint.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from .const import (
    GET_DEVICE_QUERY,
    GET_PAYLOAD_HEADERS,
    GRAPHQL_ENDPOINT,
    LOGGER,
    SHADOW_ENDPOINT_PATCH,
    build_graphql_payload,
)
from .types import (
    APIResponse,
    TemperatureUnit,
    validate_duration,
    validate_temperature,
    validate_thing_name,
)

# Type alias for the request function
RequestFunc = Callable[..., Awaitable[dict[str, Any] | str]]


class Device:
    """Handler for device-related API endpoints.

    Provides methods to retrieve device information and send commands
    to Rinnai water heaters.

    Attributes:
        _request: The authenticated request function from the API class.
    """

    def __init__(self, request: RequestFunc) -> None:
        """Initialize the Device handler.

        Args:
            request: The authenticated request function from the API class.
        """
        self._request: RequestFunc = request

    async def get_info(self, device_id: str) -> dict[str, Any]:
        """Retrieve detailed information about a specific device.

        Args:
            device_id: The unique identifier for the device.

        Returns:
            A dictionary containing the device's current state, shadow data,
            schedules, and other configuration.

        Raises:
            RequestError: If the API request fails.
        """
        payload = build_graphql_payload(GET_DEVICE_QUERY, {"id": device_id})

        response = await self._request(
            "post",
            GRAPHQL_ENDPOINT,
            data=payload,
            headers=GET_PAYLOAD_HEADERS,
        )

        if isinstance(response, str):
            return {}

        return response

    async def _set_shadow(
        self,
        dev: dict[str, Any],
        settings: dict[str, Any],
    ) -> APIResponse:
        """Send a shadow update to modify device state.

        Args:
            dev: The device dictionary containing 'thing_name'.
            settings: The settings to update on the device shadow.

        Returns:
            APIResponse with success status and data/error information.

        Raises:
            ValueError: If device is missing 'thing_name'.
            RequestError: If the API request fails.
        """
        thing_name = validate_thing_name(dev)
        data = json.dumps(settings)
        LOGGER.debug("Setting shadow for %s: %s", thing_name, data)

        headers = {
            "User-Agent": "okhttp/3.12.1",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip",
            "Accept": "application/json, text/plain, */*",
        }

        result = await self._request(
            "patch",
            SHADOW_ENDPOINT_PATCH.format(thing_name=thing_name),
            data=data,
            headers=headers,
        )

        if isinstance(result, str) and result == "success":
            return APIResponse(success=True, data={"result": "success"})
        elif isinstance(result, dict):
            return APIResponse(success=True, data=result)
        else:
            return APIResponse(success=False, error=f"Unexpected response: {result}")

    async def set_temperature(
        self,
        dev: dict[str, Any],
        temp: int | float,
        unit: TemperatureUnit = TemperatureUnit.FAHRENHEIT,
    ) -> APIResponse:
        """Set the target water temperature.

        Args:
            dev: The device dictionary containing 'thing_name'.
            temp: The target temperature (100-140°F or ~38-60°C).
            unit: Temperature unit (default: Fahrenheit).

        Returns:
            APIResponse confirming the temperature change.

        Raises:
            ValueError: If temperature is outside valid range or device
                missing thing_name.
            RequestError: If the API request fails.

        Example:
            ```python
            # Set temperature in Fahrenheit (default)
            await device.set_temperature(dev, 120)

            # Set temperature in Celsius
            await device.set_temperature(dev, 49, TemperatureUnit.CELSIUS)
            ```
        """
        validated_temp = validate_temperature(temp, unit)
        return await self._set_shadow(
            dev,
            {"set_priority_status": True, "set_domestic_temperature": validated_temp},
        )

    async def stop_recirculation(
        self,
        dev: dict[str, Any],
    ) -> APIResponse:
        """Stop the water recirculation pump.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            APIResponse confirming recirculation was stopped.

        Raises:
            ValueError: If device is missing thing_name.
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"set_recirculation_enabled": False})

    async def start_recirculation(
        self,
        dev: dict[str, Any],
        duration: int,
    ) -> APIResponse:
        """Start the water recirculation pump for a specified duration.

        Args:
            dev: The device dictionary containing 'thing_name'.
            duration: The recirculation duration in minutes (1-60).

        Returns:
            APIResponse confirming recirculation was started.

        Raises:
            ValueError: If duration is outside valid range (1-60) or device
                missing thing_name.
            RequestError: If the API request fails.
        """
        validated_duration = validate_duration(duration)
        return await self._set_shadow(
            dev,
            {
                "recirculation_duration": str(validated_duration),
                "set_recirculation_enabled": True,
            },
        )

    async def do_maintenance_retrieval(
        self,
        dev: dict[str, Any],
    ) -> APIResponse:
        """Trigger maintenance data retrieval from the device.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            APIResponse confirming the maintenance retrieval request.

        Raises:
            ValueError: If device is missing thing_name.
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"do_maintenance_retrieval": True})

    async def enable_vacation_mode(
        self,
        dev: dict[str, Any],
    ) -> APIResponse:
        """Enable vacation/holiday mode on the device.

        When enabled, the water heater operates in an energy-saving mode.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            APIResponse confirming vacation mode was enabled.

        Raises:
            ValueError: If device is missing thing_name.
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"schedule_holiday": True})

    async def disable_vacation_mode(
        self,
        dev: dict[str, Any],
    ) -> APIResponse:
        """Disable vacation/holiday mode on the device.

        Restores normal scheduled operation.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            APIResponse confirming vacation mode was disabled.

        Raises:
            ValueError: If device is missing thing_name.
            RequestError: If the API request fails.
        """
        return await self._set_shadow(
            dev,
            {"schedule_holiday": False, "schedule_enabled": True},
        )

    async def turn_off(
        self,
        dev: dict[str, Any],
    ) -> APIResponse:
        """Turn off the water heater.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            APIResponse confirming the device was turned off.

        Raises:
            ValueError: If device is missing thing_name.
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"set_operation_enabled": False})

    async def turn_on(
        self,
        dev: dict[str, Any],
    ) -> APIResponse:
        """Turn on the water heater.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            APIResponse confirming the device was turned on.

        Raises:
            ValueError: If device is missing thing_name.
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"set_operation_enabled": True})
