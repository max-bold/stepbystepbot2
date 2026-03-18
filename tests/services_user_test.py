import importlib
import os
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from sqlmodel import SQLModel, Session, create_engine

os.environ.setdefault("DATABASE_URL", "sqlite://")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.db import User


def _load_user_module() -> Any:
    module = importlib.import_module("services.user")
    return importlib.reload(module)


class UserServiceTests(unittest.TestCase):
    def setUp(self):
        self.user_module = _load_user_module()
        self.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.engine_patcher = patch.object(self.user_module, "engine", self.engine)
        self.engine_patcher.start()

    def tearDown(self):
        self.engine_patcher.stop()
        self.session.close()
        SQLModel.metadata.drop_all(self.engine)

    def test_create_user_success(self):
        user = self.user_module.create_user(
            username="alice",
            password="secret",
            first_name="Alice",
            last_name="Smith",
            e_mail="alice@example.com",
        )

        self.assertEqual(user.username, "alice")
        self.assertIsNotNone(user.id)
        self.assertIsNotNone(user.password_hash)
        assert user.password_hash is not None
        self.assertTrue(self.user_module.ph.verify(user.password_hash, "secret"))

    def test_create_user_duplicate_username_raises(self):
        self.user_module.create_user(username="alice", password="secret")

        with self.assertRaises(ValueError):
            self.user_module.create_user(username="alice", password="secret2")

    def test_delete_user_success(self):
        user = self.user_module.create_user(username="alice", password="secret")
        assert user.id is not None

        self.user_module.delete_user(user.id)

        deleted = self.session.get(User, user.id)
        self.assertIsNone(deleted)

    def test_delete_user_missing_raises(self):
        with self.assertRaises(self.user_module.NoSuchUserError):
            self.user_module.delete_user(999)

    def test_login_user_success_sets_tokens_and_expiry(self):
        self.user_module.create_user(username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            access_token, refresh_token = self.user_module.login_user("alice", "secret")

        self.assertEqual(access_token, "access_1")
        self.assertEqual(refresh_token, "refresh_1")
        user = self.session.exec(
            self.user_module.select(User).where(User.username == "alice")
        ).first()
        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.access_token, "access_1")
        self.assertEqual(user.refresh_token, "refresh_1")
        self.assertEqual(
            user.access_token_expiry, 1000.0 + self.user_module.ACCESS_TOKEN_EXPIRY
        )
        self.assertEqual(
            user.refresh_token_expiry, 1000.0 + self.user_module.REFRESH_TOKEN_EXPIRY
        )

    def test_login_user_missing_raises(self):
        with self.assertRaises(self.user_module.NoSuchUserError):
            self.user_module.login_user("unknown", "secret")

    def test_login_user_without_password_raises(self):
        user = User(username="alice", password_hash=None)
        self.session.add(user)
        self.session.commit()

        with self.assertRaises(self.user_module.InvalidPasswordError):
            self.user_module.login_user("alice", "secret")

    def test_login_user_wrong_password_raises(self):
        self.user_module.create_user(username="alice", password="secret")

        with self.assertRaises(self.user_module.InvalidPasswordError):
            self.user_module.login_user("alice", "wrong")

    def test_logout_user_success_clears_tokens(self):
        self.user_module.create_user(username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user("alice", "secret")

        with patch.object(self.user_module, "time", return_value=1001.0):
            self.user_module.logout_user("access_1")

        user = self.session.exec(
            self.user_module.select(User).where(User.username == "alice")
        ).first()
        self.assertIsNotNone(user)
        assert user is not None
        self.assertIsNone(user.access_token)
        self.assertIsNone(user.refresh_token)

    def test_logout_user_missing_raises(self):
        with self.assertRaises(self.user_module.NoSuchUserError):
            self.user_module.logout_user("missing")

    def test_logout_user_expired_token_raises(self):
        self.user_module.create_user(username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user("alice", "secret")

        with patch.object(
            self.user_module,
            "time",
            return_value=1000.0 + self.user_module.ACCESS_TOKEN_EXPIRY + 1,
        ):
            with self.assertRaises(self.user_module.InvalidPasswordError):
                self.user_module.logout_user("access_1")

    def test_refresh_token_success(self):
        self.user_module.create_user(username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user("alice", "secret")

        with patch.object(
            self.user_module.secrets, "token_urlsafe", return_value="refresh_2"
        ), patch.object(self.user_module, "time", return_value=1001.0):
            token = self.user_module.refresh_token("access_1")

        self.assertEqual(token, "refresh_2")
        user = self.session.exec(
            self.user_module.select(User).where(User.username == "alice")
        ).first()
        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.refresh_token, "refresh_2")
        self.assertEqual(
            user.refresh_token_expiry, 1001.0 + self.user_module.REFRESH_TOKEN_EXPIRY
        )

    def test_refresh_token_invalid_user_raises(self):
        with self.assertRaises(self.user_module.InvalidPasswordError):
            self.user_module.refresh_token("missing")

    def test_refresh_token_expired_access_raises(self):
        self.user_module.create_user(username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user("alice", "secret")

        with patch.object(
            self.user_module,
            "time",
            return_value=1000.0 + self.user_module.ACCESS_TOKEN_EXPIRY + 1,
        ):
            with self.assertRaises(self.user_module.InvalidPasswordError):
                self.user_module.refresh_token("access_1")

    def test_get_user_by_refresh_token_not_found(self):
        result = self.user_module.get_user_by_refresh_token("missing")
        self.assertIsNone(result)

    def test_get_user_by_refresh_token_expired_returns_none(self):
        self.user_module.create_user(username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user("alice", "secret")

        with patch.object(
            self.user_module,
            "time",
            return_value=1000.0 + self.user_module.REFRESH_TOKEN_EXPIRY + 1,
        ):
            user = self.user_module.get_user_by_refresh_token("refresh_1")

        self.assertIsNone(user)

    def test_get_user_by_refresh_token_success(self):
        self.user_module.create_user(username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user("alice", "secret")

        with patch.object(self.user_module, "time", return_value=1001.0):
            user = self.user_module.get_user_by_refresh_token("refresh_1")

        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.username, "alice")


if __name__ == "__main__":
    unittest.main()
