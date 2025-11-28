"""Device endpoint handlers for Rinnai water heater commands.

This module provides the Device class for sending commands to Rinnai
water heaters via the shadow PATCH endpoint.
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from .const import (
    GET_DEVICE_PAYLOAD,
    GET_PAYLOAD_HEADERS,
    GRAPHQL_ENDPOINT,
    LOGGER,
    SHADOW_ENDPOINT_PATCH,
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
        payload = GET_DEVICE_PAYLOAD % (device_id)

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
    ) -> dict[str, Any] | str:
        """Send a shadow update to modify device state.

        Args:
            dev: The device dictionary containing 'thing_name'.
            settings: The settings to update on the device shadow.

        Returns:
            The API response, typically "success" or a dictionary.

        Raises:
            RequestError: If the API request fails.
        """
        data = json.dumps(settings)
        LOGGER.debug("Setting shadow for %s: %s", dev.get("thing_name"), data)

        headers = {
            "User-Agent": "okhttp/3.12.1",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip",
            "Accept": "application/json, text/plain, */*",
        }

        result = await self._request(
            "patch",
            SHADOW_ENDPOINT_PATCH % (dev["thing_name"]),
            data=data,
            headers=headers,
        )
        return result

    async def set_temperature(
        self,
        dev: dict[str, Any],
        temp: int,
    ) -> dict[str, Any] | str:
        """Set the target water temperature.

        Args:
            dev: The device dictionary containing 'thing_name'.
            temp: The target temperature in degrees (device-specific units).

        Returns:
            The API response confirming the temperature change.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(
            dev,
            {"set_priority_status": True, "set_domestic_temperature": temp},
        )

    async def stop_recirculation(
        self,
        dev: dict[str, Any],
    ) -> dict[str, Any] | str:
        """Stop the water recirculation pump.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            The API response confirming recirculation was stopped.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"set_recirculation_enabled": False})

    async def start_recirculation(
        self,
        dev: dict[str, Any],
        duration: int,
    ) -> dict[str, Any] | str:
        """Start the water recirculation pump for a specified duration.

        Args:
            dev: The device dictionary containing 'thing_name'.
            duration: The recirculation duration in minutes.

        Returns:
            The API response confirming recirculation was started.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(
            dev,
            {"recirculation_duration": str(duration), "set_recirculation_enabled": True},
        )

    async def do_maintenance_retrieval(
        self,
        dev: dict[str, Any],
    ) -> dict[str, Any] | str:
        """Trigger maintenance data retrieval from the device.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            The API response confirming the maintenance retrieval request.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"do_maintenance_retrieval": True})

    async def enable_vacation_mode(
        self,
        dev: dict[str, Any],
    ) -> dict[str, Any] | str:
        """Enable vacation/holiday mode on the device.

        When enabled, the water heater operates in an energy-saving mode.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            The API response confirming vacation mode was enabled.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"schedule_holiday": True})

    async def disable_vacation_mode(
        self,
        dev: dict[str, Any],
    ) -> dict[str, Any] | str:
        """Disable vacation/holiday mode on the device.

        Restores normal scheduled operation.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            The API response confirming vacation mode was disabled.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(
            dev,
            {"schedule_holiday": False, "schedule_enabled": True},
        )

    async def turn_off(
        self,
        dev: dict[str, Any],
    ) -> dict[str, Any] | str:
        """Turn off the water heater.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            The API response confirming the device was turned off.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"set_operation_enabled": False})

    async def turn_on(
        self,
        dev: dict[str, Any],
    ) -> dict[str, Any] | str:
        """Turn on the water heater.

        Args:
            dev: The device dictionary containing 'thing_name'.

        Returns:
            The API response confirming the device was turned on.

        Raises:
            RequestError: If the API request fails.
        """
        return await self._set_shadow(dev, {"set_operation_enabled": True})