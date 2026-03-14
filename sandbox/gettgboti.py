from aiogram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector


class SocksAiohttpSession(AiohttpSession):
    def __init__(self, *, proxy_url: str, **kwargs):
        super().__init__(**kwargs)
        self._proxy_url = proxy_url
        self._connector: ProxyConnector | None = None
        self._client: ClientSession | None = None

    async def create_session(self) -> ClientSession:
        if self._client and not self._client.closed:
            return self._client
        if self._connector is None:
            self._connector = ProxyConnector.from_url(self._proxy_url)
        self._client = ClientSession(connector=self._connector)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.closed:
            await self._client.close()
        self._client = None
        if self._connector is not None:
            await self._connector.close()
        self._connector = None
        await super().close()


token = os.getenv("TG_BOT_TOKEN")
if token is None:
    raise ValueError("TG_BOT_TOKEN environment variable not set")

token = "8465319608:AAFD9NqiMk0D1-kTHMnIpoNXKlC6mblJmjU"
proxy_url = os.getenv("PROXY_URL")
if not proxy_url:
    raise ValueError("PROXY_URL environment variable not set")

tg_session = SocksAiohttpSession(proxy_url=proxy_url)
bot = Bot(token, tg_session)


async def main():
    me = await bot.get_me()
    print(f"Bot ID: {me.id}, {type(me.id)}")


import asyncio

asyncio.run(main())
