from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector

from aiogram import Bot
import os
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel

from maxapi import Bot as MaxBot

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
if DB_URL is None:
    raise ValueError("DATABASE_URL is not set in the environment variables.")

engine = create_engine(
    DB_URL,
    echo=True,
    pool_pre_ping=True,
)


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


def tgbot_proxy(token: str) -> Bot:
    proxy_url = os.getenv("PROXY_URL")
    if not proxy_url:
        raise ValueError("PROXY_URL environment variable not set")
    tg_session = SocksAiohttpSession(proxy_url=proxy_url)
    return Bot(token, tg_session)


async def get_tgbot_id(token: str) -> int:
    bot = tgbot_proxy(token)
    me = await bot.get_me()
    return me.id


async def get_maxbot_id(token: str) -> int:
    max_bot = MaxBot(token=token)
    max_bot_me = await max_bot.get_me()
    return max_bot_me.user_id

def crate_tables():
    SQLModel.metadata.create_all(engine)
