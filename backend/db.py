from ast import For
from stat import FILE_ATTRIBUTE_DEVICE
from tkinter import N

from dotenv import load_dotenv
from os import getenv

from sqlmodel import create_engine, SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB


from typing import Dict, Any

load_dotenv()

DB_URL = getenv("DATABASE_URL")

if DB_URL is None:
    raise ValueError("DATABASE_URL is not set in the environment variables.")


class Owner(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    first_name: str = "User"
    last_name: str | None = None
    e_mail: str | None = None
    passwordhash: str
    bots: list["Bot"] = Relationship(back_populates="owner")


class Bot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    tg_token: str | None = None
    max_token: str | None = None
    owner_id: int = Field(foreign_key="owner.id")
    owner: Owner = Relationship(back_populates="bots")
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False)
    )
    steps: list["Step"] = Relationship(back_populates="bot")

class Step(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bot_id: int = Field(foreign_key="bot.id")
    bot: Bot = Relationship(back_populates="steps")
    step_number: int
    name: str|None = None
    description: str|None = None
    messages: list["StepMessage"] = Relationship(back_populates="step")

class StepMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    step_id: int = Field(foreign_key="step.id")
    step: Step = Relationship(back_populates="messages")
    message_number: int
    content: str|None = None
    caption: str | None = None
    tg_file_id: str | None = None
    max_file_id: str | None = None


engine = create_engine(
    DB_URL,
    echo=True,  # логирование SQL (удобно на dev)
    pool_pre_ping=True,  # чтобы соединения не тухли
)

SQLModel.metadata.create_all(engine)
