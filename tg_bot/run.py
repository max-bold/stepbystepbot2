import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.bot import get_tgbots, create_bot
from services.user import create_user
from aiogram import Bot, Dispatcher, types

dp = Dispatcher()


async def main():
    tg_bots = get_tgbots()
    if not tg_bots:
        print(
            "No Telegram bots found in the database. Please add a bot with a valid Telegram token."
        )
        return
    await dp.start_polling(*tg_bots)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
