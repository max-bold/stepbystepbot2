from .db import Bot
from .db import session

from sqlmodel import select
from typing import Literal

from aiogram import Bot as TgBot
from maxapi import Bot as MaxBot


class TokenRegisterdError(ValueError):
    pass


from .utils import get_tgbot_id, get_maxbot_id


async def create_bot(
    owner_id: int,
    name: str,
    description: str | None = None,
    tg_token: str | None = None,
    max_token: str | None = None,
) -> Bot:
    """Create a new bot with given parameters and save it to the database

    Args:
        owner_id (int): ID of the user who will be the owner of the bot
        name (str): Name of the bot
        description (str | None, optional): Description of the bot. Defaults to None.
        tg_token (str | None, optional): Telegram token of the bot. Defaults to None.
        max_token (str | None, optional): Max token of the bot. Defaults to None.

    Raises:
        maxapi.exceptions.max.InvalidToken: On wrong Max token
        aiogram.utils.token.TokenValidationError: On wrong Telegram token
        aiogram.exceptions.TelegramUnauthorizedError: On Telegram token that is not bot token
        TokenRegisterdError: If bot with such token already exists

    Returns:
        Bot: The created bot instance
    """
    bot = Bot(
        name=name,
        description=description,
        tg_token=tg_token,
        max_token=max_token,
        owner_id=owner_id,
    )
    if tg_token is not None:
        if (
            session.exec(select(Bot).where(Bot.tg_token == tg_token)).first()
            is not None
        ):
            raise TokenRegisterdError("Bot with such Telegram token already exists")
        bot.tg_id = await get_tgbot_id(tg_token)

    if max_token is not None:
        if (
            session.exec(select(Bot).where(Bot.max_token == max_token)).first()
            is not None
        ):
            raise TokenRegisterdError("Bot with such Max token already exists")
        bot.max_id = await get_maxbot_id(max_token)

    session.add(bot)
    session.commit()
    session.refresh(bot)
    return bot


def get_tg_bot(id: str) -> Bot | None:
    return session.exec(select(Bot).where(Bot.tg_id == id)).first()


def get_max_bot(id: str) -> Bot | None:
    return session.exec(select(Bot).where(Bot.max_id == id)).first()


def get_tgbots() -> list[TgBot]:
    bots = session.exec(select(Bot).where(Bot.tg_token != None)).all()
    tg_bots = []
    for bot in bots:
        try:
            if bot.tg_token is None:
                continue
            tg_bot = TgBot(token=bot.tg_token)
            tg_bots.append(tg_bot)
        except Exception as e:
            print(f"Failed to create TgBot for bot {bot.id}: {e}")
    return tg_bots


def get_maxbots() -> list[MaxBot]:
    bots = session.exec(select(Bot).where(Bot.max_token != None)).all()
    max_bots = []
    for bot in bots:
        try:
            if bot.max_token is None:
                continue
            max_bot = MaxBot(token=bot.max_token)
            max_bots.append(max_bot)
        except Exception as e:
            print(f"Failed to create MaxBot for bot {bot.id}: {e}")
    return max_bots
