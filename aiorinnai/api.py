import json
from datetime import datetime, timedelta, time
from typing import Optional

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError, ServerTimeoutError

from .errors import RequestError
from .device import Device
from .user import User

from aiorinnai.aws_srp import AWSSRP

from aiorinnai.const import (
    POOL_ID,
    CLIENT_ID,
    POOL_REGION,
    LOGGER
)

class API(object):
    # Represents a Rinnai Water Heater, with methods for status and issuing commands

    def __init__(self, username: str, password: str, *, session: Optional[ClientSession] = None
    ) -> None:
        self._username: str = username
        self._password: str = password
        self._session: ClientSession = session
        self.token = {}

        self.device: Device = Device(self._request)

         # These endpoints will get instantiated post-authentication:
        self.user: Optional[User] = None

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        """Make a request against the API."""

        if self.token.get('expires_at') and datetime.now() >= self.token.get('expires_at', 0):
            logging.info("Requesting new access token to replace expired one")

            await self._refresh_token()

        use_running_session = self._session and not self._session.closed

        if use_running_session:
            session = self._session
        else:
            session = ClientSession(timeout=ClientTimeout(total=120))

        try:
            async with session.request(method, url, **kwargs) as resp:
                data: dict = await resp.json(content_type=None)
                resp.raise_for_status()
                return data

        except ClientError as err:
            raise RequestError(f"There was the following error while requesting {url}: {err}") from err
        finally:
            if not use_running_session:
                await session.close()

    async def _get_initial_token(self) -> None:
        """
        Authenticate and store the tokens
        """

        aws = AWSSRP(username=self._username, password=self._password, pool_id=POOL_ID,
                     client_id=CLIENT_ID, pool_region=POOL_REGION)

        await self._store_token(aws.authenticate_user())

        if not self.user:
            self.user = User(self._request, self._username)

    async def _store_token(self, js):
        self.token = js['AuthenticationResult']
        assert 'AccessToken' in self.token, self.token
        assert 'ExpiresIn' in self.token, self.token
        assert 'IdToken' in self.token, self.token
        assert 'RefreshToken' in self.token, self.token
        self.token['expires_at'] = datetime.now() + timedelta(seconds=self.token['ExpiresIn'])
        LOGGER.debug(f'received token, expires {self.token["expires_at"]}')

    async def _refresh_token(self):
        # Since we've stored the password there's no reason to actually use the
        # refresh token. If we wanted to do so, we could look at renew_access_token()
        # in https://github.com/capless/warrant/blob/master/warrant/__init__.py
        # We don't do that now to avoid unnecessary code paths (and their bugs).
        # NOTE: If Rinnai ever supports 2FA, that would be a reason to use
        # the refresh token instead of re-running the password verifier, but
        # that would also require other changes to this file.
        self._get_initial_token()

    @property
    def is_connected(self):
        """Connection status of client with Rinnai Cloud service"""
        return bool(self._access_token) and time.time() < self._expiry_date

async def async_get_api(
    username: str, password: str, *, session: Optional[ClientSession] = None
) -> API:
    wh = API(username,password)
    await wh._get_initial_token()
    return wh