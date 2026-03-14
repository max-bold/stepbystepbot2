from maxapi import Bot
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

# token = os.getenv("MAX_BOT_TOKEN")
token = "dfdfdfd"
if token is None:
    raise ValueError("MAX_BOT_TOKEN environment variable not set")

bot = Bot(token=token)


async def main():
    me = await bot.get_me()
    print(f"Bot ID: {me.user_id}, {type(me.user_id)}")

asyncio.run(main())