"""aiorinnai - Async Python library for the Rinnai Control-R API.

This library provides an async interface for authenticating with and
controlling Rinnai water heaters via the Rinnai Control-R cloud service.

Example:
    ```python
    import asyncio
    from aiorinnai import API

    async def main():
        api = API()
        await api.async_login("user@example.com", "password")

        # Get user info with all devices
        user_info = await api.user.get_info()

        # Control a device
        device = user_info["devices"]["items"][0]
        await api.device.start_recirculation(device, duration=5)

        await api.close()

    asyncio.run(main())
    ```
"""

from aiorinnai.api import API
from aiorinnai.device import Device
from aiorinnai.errors import (
    AWS_EXCEPTIONS,
    CloudError,
    PasswordChangeRequired,
    RequestError,
    RinnaiError,
    Unauthenticated,
    UnknownError,
    UserExists,
    UserNotConfirmed,
    UserNotFound,
)
from aiorinnai.types import (
    APIResponse,
    DeviceInfo,
    ShadowData,
    TemperatureUnit,
    UserInfo,
)
from aiorinnai.user import User

__version__ = "0.5.1"

__all__ = [
    # Core classes
    "API",
    "Device",
    "User",
    # Type definitions
    "APIResponse",
    "DeviceInfo",
    "ShadowData",
    "TemperatureUnit",
    "UserInfo",
    # Base exceptions
    "RinnaiError",
    "RequestError",
    # Cloud/Auth exceptions
    "CloudError",
    "Unauthenticated",
    "UserNotFound",
    "UserExists",
    "UserNotConfirmed",
    "PasswordChangeRequired",
    "UnknownError",
    # Utilities
    "AWS_EXCEPTIONS",
]