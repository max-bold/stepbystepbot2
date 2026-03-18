from .db import User
from sqlmodel import Session
from .utils import engine

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from sqlmodel import select

import secrets

from time import time

ph = PasswordHasher()

ACCESS_TOKEN_EXPIRY = 7 * 24 * 3600  # 1 week
REFRESH_TOKEN_EXPIRY = 15 * 60  # 15 minutes


async def create_user(
    username: str,
    password: str,
    first_name: str | None = None,
    last_name: str | None = None,
    e_mail: str | None = None,
) -> int:
    with Session(engine) as session:
        existing_user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if existing_user:
            raise ValueError("User with such username already exists")
        password_hash = ph.hash(password)
        user = User(
            username=username,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            e_mail=e_mail,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        if user.id is None:
            raise ValueError("Failed to create user")
        return user.id


class NoSuchUserError(Exception):
    pass


async def delete_user(user_id: int):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user is None:
            raise NoSuchUserError("No user with such ID")
        session.delete(user)
        session.commit()


class InvalidPasswordError(Exception):
    pass


async def login_user(username: str, password: str) -> tuple[str, str]:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise NoSuchUserError("No user with such username")
        elif user.password_hash is None:
            raise InvalidPasswordError("User has no password set")
        else:
            try:
                ph.verify(user.password_hash, password)
                # Generate new access and refresh tokens here and save them to the database
                access_token = secrets.token_urlsafe(32)
                refresh_token = secrets.token_urlsafe(32)
                user.access_token = access_token
                user.access_token_expiry = time() + ACCESS_TOKEN_EXPIRY
                user.refresh_token = refresh_token
                user.refresh_token_expiry = time() + REFRESH_TOKEN_EXPIRY
                session.add(user)
                session.commit()
                return access_token, refresh_token

            except VerifyMismatchError:
                raise InvalidPasswordError("Invalid password")


async def logout_user(access_token: str):
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.access_token == access_token)
        ).first()
        if user is not None:
            if user.access_token_expiry and user.access_token_expiry < time():
                raise InvalidPasswordError("Access token has expired")
            user.access_token = None
            user.refresh_token = None
            session.add(user)
            session.commit()
        else:
            raise NoSuchUserError("No user with such access token")


async def refresh_token(access_token: str) -> str:
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.access_token == access_token)
        ).first()
        if user is None:
            raise InvalidPasswordError("Invalid access or refresh token")
        if user.access_token_expiry and user.access_token_expiry < time():
            raise InvalidPasswordError("Access token has expired")
        new_refresh_token = secrets.token_urlsafe(32)
        user.refresh_token = new_refresh_token
        user.refresh_token_expiry = time() + REFRESH_TOKEN_EXPIRY
        session.add(user)
        session.commit()
        return new_refresh_token


async def get_user_by_refresh_token(refresh_token: str) -> User | None:
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.refresh_token == refresh_token)
        ).first()
        if user is None:
            return None
        if user.refresh_token_expiry and user.refresh_token_expiry < time():
            return None
        return user
