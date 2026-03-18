from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import JSON

from .utils import engine

from typing import Dict, Any

from enum import Enum


class BotAdmins(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bot_id: int = Field(foreign_key="bot.id")
    user_id: int = Field(foreign_key="user.id")


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    first_name: str | None = None
    last_name: str | None = None
    e_mail: str | None = None
    password_hash: str | None = None
    bots: list["Bot"] = Relationship(back_populates="owner")
    is_admin_of: list["Bot"] = Relationship(
        back_populates="admins", link_model=BotAdmins
    )
    access_token: str | None = None
    access_token_expiry: float | None = None
    refresh_token: str | None = None
    refresh_token_expiry: float | None = None


class PaymentMethodType(Enum):
    YOOKASSA = "yookassa"


class PaymentMethod(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    method: PaymentMethodType
    api_key: str
    store_id: str
    bot_id: int = Field(foreign_key="bot.id")


class Bot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    tg_token: str | None = None
    tg_id: int | None = None
    max_token: str | None = None
    max_id: int | None = None
    owner_id: int = Field(foreign_key="user.id")
    owner: "User" = Relationship(back_populates="bots")
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )
    admins: list["User"] = Relationship(
        back_populates="is_admin_of", link_model=BotAdmins
    )
    clients: list["Client"] = Relationship(back_populates="bot")
    default_chain_id: int | None = Field(foreign_key="stepchain.id")
    default_chain: "StepChain" = Relationship()
    payment_methods: list[PaymentMethod] = Relationship()


class StepChain(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    steps: list["Step"] = Relationship()


class StepType(Enum):
    NORMAL = "normal"
    INPUT = "input"
    CONDITION = "condition"
    PAYMENT = "payment"


class DelayType(Enum):
    FIXED = "fixed"
    PERIOD = "period"


class Step(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    chain_id: int = Field(foreign_key="stepchain.id")
    step_number: int
    name: str | None = None
    description: str | None = None
    messages: list["StepMessage"] = Relationship()
    step_type: StepType = StepType.NORMAL
    confirm_before: bool = False
    confirm_prompt: str | None = None
    confirm_btn_text: str | None = None
    payment_details: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
    )
    payment_prompt: str | None = None
    delay_type: DelayType | None = None
    delay_value: int | None = None


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


class StepMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    step_id: int = Field(foreign_key="step.id")
    message_number: int
    content: str | None = None
    caption: str | None = None
    tg_file_id: str | None = None
    max_file_id: str | None = None
    local_file_id: str | None = None
    message_type: MessageType = MessageType.TEXT


class ClientSource(Enum):
    TG = "telegram"
    MAX = "max"


class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship()
    bot_id: int = Field(foreign_key="bot.id")
    bot: Bot = Relationship()
    current_step: int = 0
    source: ClientSource


def create_tables():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_tables()
