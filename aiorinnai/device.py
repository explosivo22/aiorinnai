"""Define /device endpoints."""
from typing import Awaitable, Callable

from .const import GET_DEVICE_PAYLOAD, GET_PAYLOAD_HEADERS, COMMAND_URL, COMMAND_HEADERS, SHADOW_ENDPOINT


class Device:  # pylint: disable=too-few-public-methods
    """Define an object to handle the endpoints."""

    def __init__(self, request: Callable[..., Awaitable], id_token: str) -> None:
        """Initialize."""
        self._request: Callable[..., Awaitable] = request
        self._id_token: str = id_token
        self.headers = {
            'User-Agent': 'okhttp/3.12.1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f"Bearer {self._id_token}",
            'Accept-Encoding': 'gzip',
            'Accept': 'application/json, text/plain, */*'
        }

    async def get_info(self, device_id: str) -> dict:
        """Return device specific data.
        :param device_id: Unique identifier for the device
        :type device_id: ``str``
        :rtype: ``dict``
        """
        payload = GET_DEVICE_PAYLOAD % (device_id)

        return await self._request("post", "https://s34ox7kri5dsvdr43bfgp6qh6i.appsync-api.us-east-1.amazonaws.com/graphql",data=payload,headers=GET_PAYLOAD_HEADERS)

    async def patch_recirculation(self, thing_name: str, duration: int) -> None:
        """Use the patch URL to make our requests"""
        data = '{"recirculation_duration": "%s","set_recirculation_enabled":true}' % duration

        return await self._request("patch", f"https://698suy4zs3.execute-api.us-east-1.amazonaws.com/Prod/thing/{thing_name}/shadow", headers=self.headers, data=data)

    async def patch_stop_recirculation(self, thing_name: str) -> None:
        """Use the patch URL to make our requests"""
        data = '{"set_recirculation_enabled":false}'

        return await self._request("patch", f"https://698suy4zs3.execute-api.us-east-1.amazonaws.com/Prod/thing/{thing_name}/shadow", headers=self.headers, data=data)

    async def patch_set_temperature(self, thing_name: str, temperature: int) -> None:
        """Use the patch URL to make our requests"""
        if temperature % 5 == 0:
            data = '{"set_domestic_temperature":%s}' % temperature

            return await self._request("patch", f"https://698suy4zs3.execute-api.us-east-1.amazonaws.com/Prod/thing/{thing_name}/shadow", headers=self.headers, data=data)

    async def patch_do_maintenance_retrieval(self, thing_name: str) -> None:
        data = '{"do_maintenance_retrieval":true}'

        return await self._request("patch", f"https://698suy4zs3.execute-api.us-east-1.amazonaws.com/Prod/thing/{thing_name}/shadow", headers=self.headers, data=data) 

    async def _set_shadow(self, dev, attribute, value):
        data = {
            'user': dev['user_uuid'],
            'thing': dev['thing_name'],
            'attribute': attribute,
            'value': value
        }
        headers = {
            'User-Agent': 'okhttp/3.12.1'
        }
        r = await self._request('post',SHADOW_ENDPOINT, data=data, headers=headers)
        return r

    async def set_temperature(self, dev, temp: int):
        await self._set_shadow(dev, 'set_priority_status', 'true')
        return await self._set_shadow(dev, 'set_domestic_temperature', str(temp))

    async def stop_recirculation(self, dev):
        return await self._set_shadow(dev, 'set_recirculation_enabled', 'false')

    async def start_recirculation(self, dev, duration: int):
        await self._set_shadow(dev, 'set_priority_status', 'true')
        await self._set_shadow(dev, 'recirculation_duration', str(duration))
        return await self._set_shadow(dev, 'set_recirculation_enabled', 'true')

    async def do_maintenance_retrieval(self, dev):
        return self._set_shadow(dev, 'do_maintenance_retrieval', 'true')