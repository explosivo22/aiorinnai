# aiorinnai - Python interface for the Rinnai Control-R API

[![PyPi](https://img.shields.io/pypi/v/aiorinnai?style=for-the-badge)](https://pypi.org/project/aiorinnai)
[![License](https://img.shields.io/github/license/explosivo22/aio-rinnaicontrolr?style=for-the-badge)](https://opensource.org/licenses/Apache-2.0)

Python library for communicating with the [Rinnai Control-R Water Heaters and control devices](https://www.rinnai.us/tankless-water-heater/accessories/wifi) via the Rinnai Control-R cloud API.

***NOTICE***
* This library only works if you have migrated to the Rinnai 2.0 app.  This will require a firmware update to your Control-R module.
* [IOS](https://apps.apple.com/us/app/rinnai-control-r-2-0/id1180734911?app=itunes&ign-mpt=uo%3D4)
* [Android](https://play.google.com/store/apps/details?id=com.controlr)

NOTE:

* This library is community supported, please submit changes and improvements.
* This is a very basic interface, not well thought out at this point, but works for the use cases that initially prompted spitting this out from.

## Supports

- starting/stop recirculation
- setting temperature

## Installation

```
pip install aiorinnai==0.2.1a9
```

## Examples

```python
import asyncio

from aiohttp import ClientSession

from aiorinnai import async_get_api


async def main() -> None:
    """Run!"""
    api = await async_get_api("<EMAIL>", "<PASSWORD>")

    # Get user account information:
    user_info = await api.user.get_info()

    # Get device information
    first_device_id = user_info["devices"]["items"][0]["id"]
    device_info = await api.device.get_info(first_device_id)

    #Start Recirculation
    #Last variable is duration in minutes
    start_recirculation = await api.device.start_recirculation(user_info["id"], first_device_id, 5)

    print(start_recirculation)

    #Stop Recirculation
    stop_recirculation = await api.device.stop_recirculation(user_info["id"], first_device_id)

    print(stop_recirculation)

    #Set Temperature
    #Last variable is the temperature in increments of 5
    set_temperature = await api.device.set_temperature(user_info["id"], first_device_id, 130)


asyncio.run(main())

```
By default, the library creates a new connection to Rinnai with each coroutine. If you are calling a large number of coroutines (or merely want to squeeze out every second of runtime savings possible), an aiohttp ClientSession can be used for connection pooling:

```python
import asyncio

from aiohttp import ClientSession

from aiorinnai import async_get_api


async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with ClientSession() as websession:
        api = await async_get_api("<EMAIL>", "<PASSWORD>", session=websession)

    # Get user account information:
    user_info = await api.user.get_info()

    # Get device information
    first_device_id = user_info["devices"]["items"][0]["id"]
    device_info = await api.device.get_info(first_device_id)

    #Start Recirculation
    #Last variable is duration in minutes
    start_recirculation = await api.device.start_recirculation(user_info["id"], first_device_id, 5)

    print(start_recirculation)

    #Stop Recirculation
    stop_recirculation = await api.device.stop_recirculation(user_info["id"], first_device_id)

    print(stop_recirculation)

    #Set Temperature
    #Last variable is the temperature in increments of 5
    set_temperature = await api.device.set_temperature(user_info["id"], first_device_id, 130)


asyncio.run(main())
```

## Known Issues

* not all APIs supported
