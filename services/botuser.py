from .db import BotUser
from sqlmodel import Session, select
from .utils import engine
from .bot import Bot
from .steps import Step, MessageType
from enum import Enum


class BotUserSource(Enum):
    TG = "telegram"
    MAX = "max"


async def get_user_by_tg_id(bot_id: int, tg_id: int) -> int | None:
    with Session(engine) as session:
        statement = select(BotUser).where(
            BotUser.bot_id == bot_id, BotUser.tg_id == tg_id
        )
        result = session.exec(statement).first()
        if result is None:
            return None
        else:
            return result.id


async def get_user_by_max_id(bot_id: int, max_id: int) -> int | None:
    with Session(engine) as session:
        statement = select(BotUser).where(
            BotUser.bot_id == bot_id, BotUser.max_id == max_id
        )
        result = session.exec(statement).first()
        if result is None:
            return None
        else:
            return result.id


async def create_bot_user(
    bot_id: int,
    tg_id: int | None = None,
    max_id: int | None = None,
) -> int:
    with Session(engine) as session:
        bot = session.get(Bot, bot_id)
        if bot is None:
            raise ValueError("Bot not found")
        default_chain_id = bot.default_chain_id
        if default_chain_id is None:
            raise ValueError("Bot has no default chain")
        bot_user = BotUser(
            bot_id=bot_id,
            tg_id=tg_id,
            max_id=max_id,
            current_chain_id=default_chain_id,
        )
        session.add(bot_user)
        session.commit()
        session.refresh(bot_user)
        if bot_user.id is None:
            raise ValueError("Failed to create bot user")
        return bot_user.id


async def get_user_data(tg_id: int | None = None, max_id: int | None = None) -> dict:
    with Session(engine) as session:
        if tg_id is not None:
            statement = select(BotUser).where(BotUser.tg_id == tg_id)
        elif max_id is not None:
            statement = select(BotUser).where(BotUser.max_id == max_id)
        else:
            raise ValueError("Either tg_id or max_id must be provided")
        user = session.exec(statement).first()
        if user is None:
            return {"registered": False}
        else:
            return {"registered": True}
