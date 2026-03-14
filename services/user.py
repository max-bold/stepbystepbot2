from db import User
# from db import session
from sqlmodel import Session

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from sqlmodel import select

import secrets

from time import time

ph = PasswordHasher()

ACCESS_TOKEN_EXPIRY = 7 * 24 * 3600  # 1 week
REFRESH_TOKEN_EXPIRY = 15 * 60  # 15 minutes


def create_user(
    session: Session,
    username: str,
    password: str,
    first_name: str | None = None,
    last_name: str | None = None,
    e_mail: str | None = None,
) -> User:
    # First of all lets check if user with such username already exists
    existing_user = session.exec(select(User).where(User.username == username)).first()
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
    return user


class NoSuchUserError(Exception):
    pass


def delete_user(session: Session, user_id: int):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if user is None:
        raise NoSuchUserError("No user with such ID")
    session.delete(user)
    session.commit()


class InvalidPasswordError(Exception):
    pass


def login_user(session: Session, username: str, password: str) -> tuple[str, str]:
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


def logout_user(session: Session, access_token: str):
    user = session.exec(select(User).where(User.access_token == access_token)).first()
    if user is not None:
        if user.access_token_expiry and user.access_token_expiry < time():
            raise InvalidPasswordError("Access token has expired")
        user.access_token = None
        user.refresh_token = None
        session.add(user)
        session.commit()
    else:
        raise NoSuchUserError("No user with such access token")


def refresh_token(session: Session, access_token: str) -> str:
    user = session.exec(select(User).where(User.access_token == access_token)).first()
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


def get_user_by_refresh_token(session: Session, refresh_token: str) -> User | None:
    user = session.exec(select(User).where(User.refresh_token == refresh_token)).first()
    if user is None:
        return None
    if user.refresh_token_expiry and user.refresh_token_expiry < time():
        return None
    return user
