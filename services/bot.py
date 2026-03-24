from .db import Bot, StepChain, BotUser, Step, MessageType

from sqlmodel import Session, select
from typing import Literal

from aiogram import Bot as TgBot
from aiogram.client.session.aiohttp import AiohttpSession
from maxapi import Bot as MaxBot

from .utils import get_tgbot_id, get_maxbot_id
from .utils import engine

from enum import Enum

class BotType(Enum):
    TG = "telegram"
    MAX = "max"

class TokenRegisteredError(ValueError):
    pass


async def create_chain() -> int:
    with Session(engine) as session:
        chain = StepChain()
        session.add(chain)
        session.commit()
        session.refresh(chain)
        if chain.id is None:
            raise ValueError("Failed to create chain")
        return chain.id


async def create_bot(
    owner_id: int,
    name: str,
    description: str | None = None,
    tg_token: str | None = None,
    max_token: str | None = None,
) -> int:
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
        TokenRegisteredError: If bot with such token already exists

    Returns:
        int|None: The ID of the created bot instance, or None if creation failed
    """
    with Session(engine) as session:
        chain_id = await create_chain()
        bot = Bot(
            name=name,
            description=description,
            tg_token=tg_token,
            max_token=max_token,
            owner_id=owner_id,
            default_chain_id=chain_id,
        )
        if tg_token is not None:
            if (
                session.exec(select(Bot).where(Bot.tg_token == tg_token)).first()
                is not None
            ):
                raise TokenRegisteredError("Bot with such Telegram token already exists")
            bot.tg_id = await get_tgbot_id(tg_token)

        if max_token is not None:
            if (
                session.exec(select(Bot).where(Bot.max_token == max_token)).first()
                is not None
            ):
                raise TokenRegisteredError("Bot with such Max token already exists")
            bot.max_id = await get_maxbot_id(max_token)
        session.add(bot)
        session.commit()
        session.refresh(bot)
        if bot.id is None:
            raise ValueError("Failed to create bot")
        return bot.id


def get_tgbots(proxy_session: AiohttpSession | None = None) -> list[TgBot]:
    with Session(engine) as session:
        bots = session.exec(select(Bot).where(Bot.tg_token != None)).all()
    tg_bots = []
    for bot in bots:
        try:
            if bot.tg_token is None:
                continue
            tg_bot = TgBot(token=bot.tg_token, session=proxy_session)
            tg_bots.append(tg_bot)
        except Exception as e:
            raise RuntimeError(f"Failed to create TgBot for bot {bot.id}: {e}")
    return tg_bots


def get_maxbots() -> list[MaxBot]:
    with Session(engine) as session:
        bots = session.exec(select(Bot).where(Bot.max_token != None)).all()
    max_bots = []
    for bot in bots:
        try:
            if bot.max_token is None:
                continue
            max_bot = MaxBot(token=bot.max_token)
            max_bots.append(max_bot)
        except Exception as e:
            raise RuntimeError(f"Failed to create MaxBot for bot {bot.id}: {e}")
    return max_bots


async def get_default_chain(bot_id: int) -> int:
    with Session(engine) as session:
        bot = session.get(Bot, bot_id)
        if bot is None:
            raise ValueError("No such bot")
        if bot.default_chain_id is None:
            raise ValueError("Bot has no default chain")
        return bot.default_chain_id


async def get_bot_by_tg_id(tg_id: int) -> int:
    with Session(engine) as session:
        bot = session.exec(select(Bot).where(Bot.tg_id == tg_id)).first()
        if bot is None or bot.id is None:
            raise ValueError("No such bot")
        return bot.id


async def tg_get_steps_to_send(tg_bot_id: int) -> list:
    with Session(engine) as session:
        bot = session.exec(select(Bot).where(Bot.tg_id == tg_bot_id)).first()
        if bot is None:
            raise ValueError("Bot not found")
        bot_users = session.exec(select(BotUser).where(BotUser.bot_id == bot.id)).all()
        steps_to_send = []
        for bot_user in bot_users:
            current_step = session.exec(
                select(Step).where(
                    Step.chain_id == bot_user.current_chain_id,
                    Step.step_number == bot_user.current_step,
                )
            ).first()
            if current_step is not None:
                messages = []
                for message in current_step.messages:
                    messages.append(
                        {
                            "type": message.message_type,
                            "content": message.content,
                            "caption": message.caption,
                            "file_id": message.tg_file_id,
                        }
                    )
                steps_to_send.append((bot_user.tg_id, messages))
        return steps_to_send
