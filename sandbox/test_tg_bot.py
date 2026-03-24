from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command, Filter
from aiogram.loggers import event
from dotenv import load_dotenv
import os
import sys
import asyncio
from aiogram.client.session.aiohttp import AiohttpSession
from typing import Any, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.bot import get_bot_by_tg_id, get_tgbots, tg_get_steps_to_send, MessageType
from services.botuser import get_user_by_tg_id, create_bot_user

load_dotenv()

dp = Dispatcher()


@dp.update.middleware()  # type: ignore
async def get_client_data(handler: Callable, event: types.Update, data: dict[str, Any]):
    if event.message and event.message.from_user and event.bot:
        bot_id = await get_bot_by_tg_id(event.bot.id)
        data["bot_id"] = bot_id
        user_id = await get_user_by_tg_id(bot_id, event.message.from_user.id)
        data["user_id"] = user_id
    return await handler(event, data)


class RegisteredUserFilter(Filter):
    async def __call__(self, event: types.Update, user_id: int | None) -> bool:
        return user_id is not None


@dp.message(CommandStart(), ~RegisteredUserFilter())
async def command_start_unregistered(message: types.Message, bot_id: int):
    if message.from_user:
        user_id = await create_bot_user(bot_id, tg_id=message.from_user.id)
        await message.reply("You have been registered successfully!")


@dp.message(~RegisteredUserFilter())
async def start_command(message: types.Message):
    await message.reply("Hello! Please register to use this bot. Send /start command.")


@dp.message()
async def default_handler(message: types.Message):
    await message.reply("Hello! This is a test bot.")


async def send_steps(bots: list[Bot]):
    for bot in bots:
        steps_to_send = await tg_get_steps_to_send(bot.id)
        for tg_id, messages in steps_to_send:
            for message in messages:
                try:
                    if message["type"] == MessageType.TEXT:
                        await bot.send_message(tg_id, message["content"])
                    elif message["type"] == MessageType.PHOTO:
                        await bot.send_photo(
                            tg_id,
                            photo=message["file_id"],
                            caption=message["caption"],
                        )
                    elif message["type"] == MessageType.VIDEO:
                        await bot.send_video(
                            tg_id,
                            video=message["file_id"],
                            caption=message["caption"],
                        )
                    elif message["type"] == MessageType.DOCUMENT:
                        await bot.send_document(
                            tg_id,
                            document=message["file_id"],
                            caption=message["caption"],
                        )
                except Exception as e:
                    print(f"Failed to send message to {tg_id}: {e}")


async def main():

    proxy_url = os.getenv("PROXY_URL")
    if proxy_url is None:
        raise ValueError("PROXY_URL environment variable not set")

    session = AiohttpSession(proxy=proxy_url)
    bots = get_tgbots(proxy_session=session)
    asyncio.create_task(send_steps(bots))
    await dp.start_polling(*bots)


if __name__ == "__main__":
    asyncio.run(main())
