"""Type definitions for the aiorinnai library.

This module provides TypedDict definitions for API responses, a dataclass
for structured API responses, and a temperature unit enum with conversion helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, NotRequired, TypedDict


class TemperatureUnit(Enum):
    """Temperature unit enumeration with conversion helpers.

    Rinnai water heaters use Fahrenheit internally, so conversions
    are provided for Celsius input.
    """

    FAHRENHEIT = "fahrenheit"
    CELSIUS = "celsius"

    @staticmethod
    def celsius_to_fahrenheit(celsius: float) -> int:
        """Convert Celsius to Fahrenheit, rounded to nearest integer.

        Args:
            celsius: Temperature in degrees Celsius.

        Returns:
            Temperature in degrees Fahrenheit as an integer.

        Example:
            >>> TemperatureUnit.celsius_to_fahrenheit(40)
            104
            >>> TemperatureUnit.celsius_to_fahrenheit(60)
            140
        """
        return round((celsius * 9 / 5) + 32)

    @staticmethod
    def fahrenheit_to_celsius(fahrenheit: float) -> float:
        """Convert Fahrenheit to Celsius.

        Args:
            fahrenheit: Temperature in degrees Fahrenheit.

        Returns:
            Temperature in degrees Celsius.

        Example:
            >>> TemperatureUnit.fahrenheit_to_celsius(104)
            40.0
            >>> TemperatureUnit.fahrenheit_to_celsius(140)
            60.0
        """
        return (fahrenheit - 32) * 5 / 9


@dataclass
class APIResponse:
    """Structured response from API operations.

    Provides a consistent interface for all API call results,
    allowing callers to check success status and access either
    data or error information.

    Attributes:
        success: Whether the API call was successful.
        data: Response data if successful, None otherwise.
        error: Error message if unsuccessful, None otherwise.

    Example:
        ```python
        response = await device.set_temperature(dev, 120)
        if response.success:
            print("Temperature set successfully")
        else:
            print(f"Failed: {response.error}")
        ```
    """

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class ActivityInfo(TypedDict, total=False):
    """Device activity information from the API."""

    clientId: str
    serial_id: str
    timestamp: str
    eventType: str


class ShadowData(TypedDict, total=False):
    """Device shadow state from the Rinnai cloud.

    Contains the current and desired state for device settings
    like temperature, recirculation, and operation mode.
    """

    heater_serial_number: str
    ayla_dsn: str
    rinnai_registered: bool
    do_maintenance_retrieval: bool
    model: str
    module_log_level: str
    set_priority_status: bool
    set_recirculation_enable: bool
    set_recirculation_enabled: bool
    set_domestic_temperature: int
    set_operation_enabled: bool
    schedule: str
    schedule_holiday: bool
    schedule_enabled: bool
    do_zigbee: bool
    timezone: str
    timezone_encoded: str
    priority_status: bool
    recirculation_enabled: bool
    recirculation_duration: int
    lock_enabled: bool
    operation_enabled: bool
    module_firmware_version: str
    recirculation_not_configured: bool
    maximum_domestic_temperature: int
    minimum_domestic_temperature: int
    createdAt: str
    updatedAt: str


class DeviceInfoData(TypedDict, total=False):
    """Extended device information from the info field."""

    serial_id: str
    ayla_dsn: str
    name: str
    domestic_combustion: str
    domestic_temperature: int
    wifi_ssid: str
    wifi_signal_strength: int
    wifi_channel_frequency: str
    local_ip: str
    public_ip: str
    ap_mac_addr: str
    recirculation_temperature: int
    recirculation_duration: int
    zigbee_inventory: str
    zigbee_status: str
    lime_scale_error: str
    mc__total_calories: int
    type: str
    unix_time: int
    m01_water_flow_rate_raw: int
    do_maintenance_retrieval: bool
    firmware_version: str
    module_firmware_version: str
    error_code: str
    warning_code: str
    internal_temperature: int
    operation_hours: int
    recirculation_capable: bool
    maintenance_list: str
    model: str
    createdAt: str
    updatedAt: str


class MonitoringInfo(TypedDict, total=False):
    """Device monitoring information."""

    serial_id: str
    dealer_uuid: str
    user_uuid: str
    request_state: str
    createdAt: str
    updatedAt: str
    dealer: dict[str, Any]


class ScheduleItem(TypedDict, total=False):
    """Device schedule item."""

    id: str
    serial_id: str
    name: str
    schedule: str
    days: str
    times: str
    schedule_date: str
    active: bool
    createdAt: str
    updatedAt: str


class ScheduleList(TypedDict, total=False):
    """List of device schedules."""

    items: list[ScheduleItem]
    nextToken: str | None


class ErrorLogItem(TypedDict, total=False):
    """Device error log entry."""

    id: str
    serial_id: str
    ayla_dsn: str
    name: str
    lime_scale_error: str
    m01_water_flow_rate_raw: int
    m02_outlet_temperature: int
    m04_combustion_cycles: int
    m08_inlet_temperature: int
    error_code: str
    warning_code: str
    operation_hours: int
    active: bool
    createdAt: str
    updatedAt: str


class RegistrationItem(TypedDict, total=False):
    """Device registration entry."""

    serial: str
    dealer_id: str
    device_id: str
    user_uuid: str
    model: str
    gateway_dsn: str
    application_type: str
    recirculation_type: str
    install_datetime: str
    registration_type: str
    dealer_user_email: str
    active: bool
    createdAt: str
    updatedAt: str


class DeviceInfo(TypedDict, total=False):
    """Complete device information from the API.

    Contains all device details including shadow state, schedules,
    monitoring info, and registration data.
    """

    id: str
    thing_name: str
    device_name: str
    dealer_uuid: str
    city: str
    state: str
    street: str
    zip: str
    country: str
    firmware: str
    model: str
    dsn: str
    user_uuid: str
    connected_at: str
    key: str
    lat: float
    lng: float
    address: str
    vacation: bool
    createdAt: str
    updatedAt: str
    activity: ActivityInfo
    shadow: ShadowData
    monitoring: MonitoringInfo
    schedule: ScheduleList
    info: DeviceInfoData
    errorLogs: dict[str, Any]
    registration: dict[str, Any]


class DeviceList(TypedDict, total=False):
    """List of devices with pagination token."""

    items: list[DeviceInfo]
    nextToken: str | None


class UserInfo(TypedDict, total=False):
    """User account information from the API.

    Contains user profile data and associated devices.
    """

    id: str
    name: str
    email: str
    admin: bool
    approved: bool
    confirmed: bool
    aws_confirm: bool
    imported: bool
    country: str
    city: str
    state: str
    street: str
    zip: str
    company: str
    username: str
    firstname: str
    lastname: str
    st_accesstoken: str
    st_refreshtoken: str
    phone_country_code: str
    phone: str
    primary_contact: str
    terms_accepted: bool
    terms_accepted_at: str
    terms_email_sent_at: str
    terms_token: str
    roles: list[str]
    createdAt: str
    updatedAt: str
    devices: DeviceList


# Validation constants
MIN_TEMPERATURE_F = 100
MAX_TEMPERATURE_F = 140
MIN_TEMPERATURE_C = 38  # ~100°F
MAX_TEMPERATURE_C = 60  # ~140°F
MIN_RECIRCULATION_DURATION = 1
MAX_RECIRCULATION_DURATION = 60


def validate_temperature(
    temp: int | float,
    unit: TemperatureUnit = TemperatureUnit.FAHRENHEIT,
) -> int:
    """Validate and convert temperature to Fahrenheit.

    Args:
        temp: Temperature value to validate.
        unit: Temperature unit (Fahrenheit or Celsius).

    Returns:
        Temperature in Fahrenheit as an integer.

    Raises:
        ValueError: If temperature is outside valid range (100-140°F or ~38-60°C).
    """
    if unit == TemperatureUnit.CELSIUS:
        if not MIN_TEMPERATURE_C <= temp <= MAX_TEMPERATURE_C:
            raise ValueError(
                f"Temperature must be between {MIN_TEMPERATURE_C} and "
                f"{MAX_TEMPERATURE_C}°C, got {temp}°C"
            )
        return TemperatureUnit.celsius_to_fahrenheit(temp)
    else:
        if not MIN_TEMPERATURE_F <= temp <= MAX_TEMPERATURE_F:
            raise ValueError(
                f"Temperature must be between {MIN_TEMPERATURE_F} and "
                f"{MAX_TEMPERATURE_F}°F, got {temp}°F"
            )
        return int(temp)


def validate_duration(duration: int) -> int:
    """Validate recirculation duration.

    Args:
        duration: Duration in minutes.

    Returns:
        Validated duration.

    Raises:
        ValueError: If duration is outside valid range (1-60 minutes).
    """
    if not MIN_RECIRCULATION_DURATION <= duration <= MAX_RECIRCULATION_DURATION:
        raise ValueError(
            f"Duration must be between {MIN_RECIRCULATION_DURATION} and "
            f"{MAX_RECIRCULATION_DURATION} minutes, got {duration}"
        )
    return duration


def validate_thing_name(dev: dict[str, Any]) -> str:
    """Validate device has a thing_name.

    Args:
        dev: Device dictionary.

    Returns:
        The thing_name value.

    Raises:
        ValueError: If thing_name is missing or empty.
    """
    thing_name = dev.get("thing_name")
    if not thing_name:
        raise ValueError("Device must have a 'thing_name' attribute")
    return thing_name
