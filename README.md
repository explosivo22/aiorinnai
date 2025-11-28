# aiorinnai - Python interface for the Rinnai Control-R API

[![PyPi](https://img.shields.io/pypi/v/aiorinnai?style=for-the-badge)](https://pypi.org/project/aiorinnai)
[![License](https://img.shields.io/github/license/explosivo22/aio-rinnaicontrolr?style=for-the-badge)](https://opensource.org/licenses/Apache-2.0)

Python library for communicating with the [Rinnai Control-R Water Heaters and control devices](https://www.rinnai.us/tankless-water-heater/accessories/wifi) via the Rinnai Control-R cloud API.

**WARNING**

* This library only works if you have migrated to the Rinnai 2.0 app. This will require a firmware update to your Control-R module.
* [iOS](https://apps.apple.com/us/app/rinnai-control-r-2-0/id1180734911?app=itunes&ign-mpt=uo%3D4)
* [Android](https://play.google.com/store/apps/details?id=com.controlr)

NOTE:

* This library is community supported, please submit changes and improvements.
* This is a very basic interface, not well thought out at this point, but works for the use cases that initially prompted spitting this out from.

## Supports

- Starting/stopping recirculation
- Setting temperature
- Turning water heater on/off
- Enabling/disabling vacation mode
- Maintenance data retrieval

## Installation

```bash
pip install aiorinnai
```

## Usage

### Basic Example

```python
import asyncio
from aiorinnai import API


async def main() -> None:
    """Run!"""
    async with API() as api:
        # Authenticate with your Rinnai account
        await api.async_login("<EMAIL>", "<PASSWORD>")

        # Get user account information (includes all devices)
        user_info = await api.user.get_info()

        # Get the first device
        device = user_info["devices"]["items"][0]
        print(f"Device: {device['device_name']}")

        # Get detailed device information
        device_info = await api.device.get_info(device["id"])

        # Start recirculation for 5 minutes
        await api.device.start_recirculation(device, 5)

        # Stop recirculation
        await api.device.stop_recirculation(device)

        # Set temperature (in degrees, increments of 5)
        await api.device.set_temperature(device, 120)

        # Turn water heater off
        await api.device.turn_off(device)

        # Turn water heater on
        await api.device.turn_on(device)

        # Enable vacation mode
        await api.device.enable_vacation_mode(device)

        # Disable vacation mode
        await api.device.disable_vacation_mode(device)


asyncio.run(main())
```

### With Connection Pooling (Recommended)

For better performance, you can provide your own `aiohttp.ClientSession` for connection pooling:

```python
import asyncio
from aiohttp import ClientSession
from aiorinnai import API


async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with ClientSession() as session:
        # Pass the session to the API constructor
        async with API(session=session) as api:
            await api.async_login("<EMAIL>", "<PASSWORD>")

            # Get user account information
            user_info = await api.user.get_info()

            # Get the first device
            device = user_info["devices"]["items"][0]

            # Start recirculation for 5 minutes
            await api.device.start_recirculation(device, 5)
            print("Recirculation started!")

            # Set temperature
            await api.device.set_temperature(device, 125)
            print("Temperature set!")


asyncio.run(main())
```

### Custom Timeout

You can configure request timeouts (default is 30 seconds):

```python
import asyncio
from aiorinnai import API


async def main() -> None:
    # Set a custom timeout of 60 seconds
    async with API(timeout=60) as api:
        await api.async_login("<EMAIL>", "<PASSWORD>")
        user_info = await api.user.get_info()


asyncio.run(main())
```

### Error Handling

The library provides specific exceptions for different error conditions:

```python
import asyncio
from aiorinnai import (
    API,
    Unauthenticated,
    UserNotFound,
    RequestError,
)


async def main() -> None:
    async with API() as api:
        try:
            await api.async_login("<EMAIL>", "<PASSWORD>")
            user_info = await api.user.get_info()

        except Unauthenticated:
            print("Invalid email or password")
        except UserNotFound:
            print("User account not found")
        except RequestError as err:
            print(f"API request failed: {err}")


asyncio.run(main())
```

## API Reference

### API Class

**Constructor:**
- `API(session=None, timeout=30)` - Create an API client
  - `session`: Optional `aiohttp.ClientSession` for connection pooling
  - `timeout`: Request timeout in seconds (default: 30)

**Methods:**
- `async_login(email, password)` - Authenticate with your Rinnai account
- `async_check_token()` - Check and refresh token if needed (called automatically)
- `close()` - Close the API client and release resources

**Properties:**
- `is_connected` - Returns `True` if connected with valid authentication

**Context Manager:**
- The API class supports `async with` for automatic resource cleanup

### Device Methods

- `get_info(device_id)` - Get detailed device information
- `set_temperature(device, temp)` - Set water temperature
- `start_recirculation(device, duration)` - Start recirculation pump (duration in minutes)
- `stop_recirculation(device)` - Stop recirculation pump
- `turn_on(device)` - Turn the water heater on
- `turn_off(device)` - Turn the water heater off
- `enable_vacation_mode(device)` - Enable vacation/holiday mode
- `disable_vacation_mode(device)` - Disable vacation mode
- `do_maintenance_retrieval(device)` - Trigger maintenance data retrieval

### User Methods

- `get_info()` - Get user account information including all devices

### Exceptions

- `RinnaiError` - Base exception for all errors
- `RequestError` - HTTP/connection failures
- `CloudError` - Base for authentication errors
- `Unauthenticated` - Invalid credentials
- `UserNotFound` - User account doesn't exist
- `UserNotConfirmed` - Email not confirmed
- `PasswordChangeRequired` - Password reset needed
- `UnknownError` - Unrecognized AWS error

## Known Issues

* Not all APIs supported

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
