# aiorinnai - Python interface for the Rinnai Control-R API

[![PyPi](https://img.shields.io/pypi/v/aiorinnai?style=for-the-badge)](https://pypi.org/project/aiorinnai)
[![CI](https://img.shields.io/github/actions/workflow/status/explosivo22/aiorinnai/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/explosivo22/aiorinnai/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/explosivo22/aiorinnai?style=for-the-badge)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/pypi/pyversions/aiorinnai?style=for-the-badge)](https://pypi.org/project/aiorinnai)

Python library for communicating with the [Rinnai Control-R Water Heaters and control devices](https://www.rinnai.us/tankless-water-heater/accessories/wifi) via the Rinnai Control-R cloud API.

**WARNING**

* This library only works if you have migrated to the Rinnai 2.0 app. This will require a firmware update to your Control-R module.
* [iOS](https://apps.apple.com/us/app/rinnai-control-r-2-0/id1180734911?app=itunes&ign-mpt=uo%3D4)
* [Android](https://play.google.com/store/apps/details?id=com.controlr)

> **Note:** This library is community supported. Contributions and improvements are welcome!

## Features

- **Secure Authentication** - AWS Cognito-based authentication with automatic token refresh
- **Temperature Control** - Set temperature in Fahrenheit or Celsius with automatic conversion
- **Recirculation Control** - Start/stop recirculation pump with configurable duration (1-60 minutes)
- **Device Management** - Turn water heater on/off, enable/disable vacation mode
- **Maintenance** - Trigger maintenance data retrieval
- **Input Validation** - Built-in validation for temperature (100-140°F) and duration ranges
- **Type Safety** - Full type hints with TypedDict definitions for API responses
- **Async/Await** - Built on aiohttp for efficient async operations
- **Retry Logic** - Configurable retry with exponential backoff for transient errors

## Installation

Requires Python 3.11 or higher.

```bash
pip install aiorinnai
```

## Quick Start

```python
import asyncio
from aiorinnai import API


async def main() -> None:
    async with API() as api:
        await api.async_login("<EMAIL>", "<PASSWORD>")

        user_info = await api.user.get_info()
        device = user_info["devices"]["items"][0]

        # Set temperature and start recirculation
        await api.device.set_temperature(device, 120)
        await api.device.start_recirculation(device, duration=5)


asyncio.run(main())
```

## Usage Examples

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
        response = await api.device.start_recirculation(device, 5)
        if response.success:
            print("Recirculation started!")

        # Stop recirculation
        await api.device.stop_recirculation(device)

        # Set temperature (100-140°F, increments of 5)
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

### Temperature Unit Support

Set temperature in Fahrenheit (default) or Celsius:

```python
import asyncio
from aiorinnai import API, TemperatureUnit


async def main() -> None:
    async with API() as api:
        await api.async_login("<EMAIL>", "<PASSWORD>")
        user_info = await api.user.get_info()
        device = user_info["devices"]["items"][0]

        # Set temperature in Fahrenheit (default)
        await api.device.set_temperature(device, 120)

        # Set temperature in Celsius (auto-converts to Fahrenheit)
        await api.device.set_temperature(device, 49, TemperatureUnit.CELSIUS)

        # Temperature conversion helpers
        fahrenheit = TemperatureUnit.celsius_to_fahrenheit(49)  # Returns 120
        celsius = TemperatureUnit.fahrenheit_to_celsius(120)    # Returns 48.89


asyncio.run(main())
```

### Handling API Responses

All device commands return an `APIResponse` object for consistent error handling:

```python
import asyncio
from aiorinnai import API, APIResponse


async def main() -> None:
    async with API() as api:
        await api.async_login("<EMAIL>", "<PASSWORD>")
        user_info = await api.user.get_info()
        device = user_info["devices"]["items"][0]

        # APIResponse provides success status and data/error info
        response: APIResponse = await api.device.set_temperature(device, 120)

        if response.success:
            print("Temperature set successfully!")
            print(f"Response data: {response.data}")
        else:
            print(f"Failed: {response.error}")


asyncio.run(main())
```

### With Connection Pooling (Recommended)

For better performance, provide your own `aiohttp.ClientSession`:

```python
import asyncio
from aiohttp import ClientSession
from aiorinnai import API


async def main() -> None:
    async with ClientSession() as session:
        async with API(session=session) as api:
            await api.async_login("<EMAIL>", "<PASSWORD>")
            user_info = await api.user.get_info()
            device = user_info["devices"]["items"][0]

            response = await api.device.start_recirculation(device, 5)
            if response.success:
                print("Recirculation started!")


asyncio.run(main())
```

### Custom Configuration

Configure timeouts, retry behavior, and more:

```python
import asyncio
from aiorinnai import API


async def main() -> None:
    # Full configuration options
    async with API(
        timeout=60.0,           # Request timeout in seconds (default: 30)
        retry_count=5,          # Number of retry attempts (default: 3)
        retry_delay=2.0,        # Initial delay between retries (default: 1.0)
        retry_multiplier=2.0,   # Exponential backoff multiplier (default: 2.0)
        executor_timeout=30.0,  # Timeout for blocking AWS calls (default: 30)
    ) as api:
        await api.async_login("<EMAIL>", "<PASSWORD>")
        user_info = await api.user.get_info()


asyncio.run(main())
```

### Token Persistence

For long-running applications (like Home Assistant integrations), you can persist tokens to avoid re-authenticating:

```python
import asyncio
from aiorinnai import API


async def main() -> None:
    async with API() as api:
        # Initial login
        await api.async_login("<EMAIL>", "<PASSWORD>")

        # Save tokens for later (store securely!)
        saved_tokens = {
            "email": api.username,
            "access_token": api.access_token,
            "refresh_token": api.refresh_token,
        }
        print(f"Tokens saved: {saved_tokens}")


async def restore_session() -> None:
    """Restore a session from saved tokens."""
    # Load your saved tokens
    saved_tokens = {
        "email": "user@example.com",
        "access_token": "...",
        "refresh_token": "...",
    }

    async with API() as api:
        # Restore session without password
        await api.async_renew_access_token(
            email=saved_tokens["email"],
            access_token=saved_tokens["access_token"],
            refresh_token=saved_tokens["refresh_token"],
        )

        # Now you can use the API
        user_info = await api.user.get_info()
        print(f"Restored session for: {user_info['email']}")


asyncio.run(main())
```

**Token Properties (read-only):**
- `api.id_token` - JWT ID token for API authentication
- `api.access_token` - JWT access token for Cognito operations
- `api.refresh_token` - Refresh token for obtaining new tokens

### Input Validation

The library validates inputs and raises `ValueError` for invalid values:

```python
import asyncio
from aiorinnai import API


async def main() -> None:
    async with API() as api:
        await api.async_login("<EMAIL>", "<PASSWORD>")
        user_info = await api.user.get_info()
        device = user_info["devices"]["items"][0]

        try:
            # Temperature must be 100-140°F
            await api.device.set_temperature(device, 99)  # Raises ValueError
        except ValueError as e:
            print(f"Invalid temperature: {e}")

        try:
            # Duration must be 1-60 minutes
            await api.device.start_recirculation(device, 0)  # Raises ValueError
        except ValueError as e:
            print(f"Invalid duration: {e}")

        try:
            # Device must have 'thing_name' attribute
            await api.device.turn_on({})  # Raises ValueError
        except ValueError as e:
            print(f"Invalid device: {e}")


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
        except asyncio.TimeoutError:
            print("Request timed out")


asyncio.run(main())
```

## API Reference

### API Class

**Constructor:**
```python
API(
    session: ClientSession | None = None,  # Optional aiohttp session
    timeout: float = 30.0,                 # Request timeout in seconds
    retry_count: int = 3,                  # Number of retry attempts
    retry_delay: float = 1.0,              # Initial retry delay in seconds
    retry_multiplier: float = 2.0,         # Exponential backoff multiplier
    executor_timeout: float = 30.0,        # Timeout for blocking AWS calls
)
```

**Methods:**
- `async_login(email, password)` - Authenticate with your Rinnai account
- `async_renew_access_token(email, access_token, refresh_token)` - Restore session from saved tokens
- `async_check_token()` - Check and refresh token if needed (called automatically)
- `close()` - Close the API client and release resources

**Properties:**
- `is_connected` - Returns `True` if connected with valid authentication
- `username` - The authenticated user's email address
- `id_token` - JWT ID token (read-only, for API authentication)
- `access_token` - JWT access token (read-only, for Cognito operations)
- `refresh_token` - Refresh token (read-only, for token renewal)

**Context Manager:**
- The API class supports `async with` for automatic resource cleanup

### Device Methods

All device methods return `APIResponse` with `success`, `data`, and `error` attributes.

| Method | Description | Validation |
|--------|-------------|------------|
| `get_info(device_id)` | Get detailed device information | - |
| `set_temperature(device, temp, unit=FAHRENHEIT)` | Set water temperature | 100-140°F or 38-60°C |
| `start_recirculation(device, duration)` | Start recirculation pump | 1-60 minutes |
| `stop_recirculation(device)` | Stop recirculation pump | - |
| `turn_on(device)` | Turn the water heater on | - |
| `turn_off(device)` | Turn the water heater off | - |
| `enable_vacation_mode(device)` | Enable vacation/holiday mode | - |
| `disable_vacation_mode(device)` | Disable vacation mode | - |
| `do_maintenance_retrieval(device)` | Trigger maintenance data retrieval | - |

### User Methods

- `get_info()` - Get user account information including all devices (returns `UserInfo | None`)

### Type Definitions

The library exports TypedDict definitions for type-safe access to API responses:

```python
from aiorinnai import (
    APIResponse,      # Dataclass: success, data, error
    DeviceInfo,       # TypedDict for device data
    ShadowData,       # TypedDict for device shadow state
    UserInfo,         # TypedDict for user account data
    TemperatureUnit,  # Enum: FAHRENHEIT, CELSIUS
)
```

### Exceptions

| Exception | Description |
|-----------|-------------|
| `RinnaiError` | Base exception for all errors |
| `RequestError` | HTTP/connection failures |
| `CloudError` | Base for authentication errors |
| `Unauthenticated` | Invalid credentials |
| `UserNotFound` | User account doesn't exist |
| `UserExists` | User already exists (during registration) |
| `UserNotConfirmed` | Email not confirmed |
| `PasswordChangeRequired` | Password reset needed |
| `UnknownError` | Unrecognized AWS error |

## Validation Ranges

| Parameter | Valid Range | Notes |
|-----------|-------------|-------|
| Temperature (°F) | 100-140 | Increments of 5 recommended |
| Temperature (°C) | 38-60 | Auto-converts to Fahrenheit |
| Recirculation Duration | 1-60 minutes | - |

## Known Issues

* Not all APIs supported

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/explosivo22/aiorinnai.git
cd aiorinnai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aiorinnai --cov-report=term-missing
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy aiorinnai
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
