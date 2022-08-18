"""Define /device endpoints."""
import json

from typing import Awaitable, Callable

from .const import GET_DEVICE_PAYLOAD, GET_PAYLOAD_HEADERS, COMMAND_URL, COMMAND_HEADERS, SHADOW_ENDPOINT_PATCH


class Device:  # pylint: disable=too-few-public-methods
    """Define an object to handle the endpoints."""

    def __init__(self, request: Callable[..., Awaitable]) -> None:
        """Initialize."""
        self._request: Callable[..., Awaitable] = request

    async def get_info(self, device_id: str) -> dict:
        """Return device specific data.
        :param device_id: Unique identifier for the device
        :type device_id: ``str``
        :rtype: ``dict``
        """
        payload = GET_DEVICE_PAYLOAD % (device_id)

        return await self._request("post", "https://s34ox7kri5dsvdr43bfgp6qh6i.appsync-api.us-east-1.amazonaws.com/graphql",data=payload,headers=GET_PAYLOAD_HEADERS)

    async def _set_shadow(self, dev, settings: dict):
        data = json.dumps(settings)

        headers = {
            'User-Agent': 'okhttp/3.12.1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip',
            'Accept': 'application/json, text/plain, */*',
        }
        r = await self._request('patch', SHADOW_ENDPOINT_PATCH % (dev['thing_name']), data=data, headers=headers)
        return r

    async def set_temperature(self, dev, temp: int):
        return await self._set_shadow(dev, {'set_priority_status': True, 'set_domestic_temperature': temp})

    async def stop_recirculation(self, dev):
        return await self._set_shadow(dev, {'set_recirculation_enabled': False})

    async def start_recirculation(self, dev, duration: int):
        return await self._set_shadow(dev, {"recirculation_duration": str(duration), "set_recirculation_enabled": True})

    async def do_maintenance_retrieval(self, dev):
        return await self._set_shadow(dev, {'do_maintenance_retrieval': True})