from dotenv import load_dotenv
from os import getenv

from sqlmodel import create_engine, SQLModel, Field, Relationship, Column, Session
from sqlalchemy import JSON


from typing import Dict, Any

load_dotenv()

DB_URL = getenv("DATABASE_URL")

if DB_URL is None:
    raise ValueError("DATABASE_URL is not set in the environment variables.")


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
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    steps: list["Step"] = Relationship(back_populates="bot")
    admins: list["User"] = Relationship(
        back_populates="is_admin_of", link_model=BotAdmins
    )
    clients: list["Client"] = Relationship(back_populates="bot")


class Step(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bot_id: int = Field(foreign_key="bot.id")
    bot: Bot = Relationship(back_populates="steps")
    step_number: int
    name: str | None = None
    description: str | None = None
    messages: list["StepMessage"] = Relationship(back_populates="step")


class StepMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    step_id: int = Field(foreign_key="step.id")
    step: Step = Relationship(back_populates="messages")
    message_number: int
    content: str | None = None
    caption: str | None = None
    tg_file_id: str | None = None
    max_file_id: str | None = None


class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship()
    bot_id: int = Field(foreign_key="bot.id")
    bot: Bot = Relationship()
    current_step: int = 0

load_dotenv()
DB_URL = getenv("DATABASE_URL")
if DB_URL is None:
    raise ValueError("DATABASE_URL is not set in the environment variables.")
engine = create_engine(
    DB_URL,
    echo=True,  # логирование SQL (удобно на dev)
    pool_pre_ping=True,  # чтобы соединения не тухли
)

session = Session(engine)

def crate_tables():
    
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    crate_tables()
