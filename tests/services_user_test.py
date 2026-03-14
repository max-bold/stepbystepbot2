import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from sqlmodel import Field, SQLModel, Session, create_engine


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    first_name: str | None = None
    last_name: str | None = None
    e_mail: str | None = None
    password_hash: str | None = None
    access_token: str | None = None
    access_token_expiry: float | None = None
    refresh_token: str | None = None
    refresh_token_expiry: float | None = None


def _load_user_module() -> Any:
    module_name = "services_user_under_test"
    module_path = Path(__file__).resolve().parents[1] / "services" / "user.py"

    if module_name in sys.modules:
        del sys.modules[module_name]

    fake_db_module = types.ModuleType("db")
    setattr(fake_db_module, "User", User)
    sys.modules["db"] = fake_db_module

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {module_name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UserServiceTests(unittest.TestCase):
    def setUp(self):
        self.user_module = _load_user_module()
        self.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        SQLModel.metadata.drop_all(self.engine)

    def test_create_user_success(self):
        user = self.user_module.create_user(
            self.session,
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
        self.user_module.create_user(self.session, username="alice", password="secret")

        with self.assertRaises(ValueError):
            self.user_module.create_user(
                self.session, username="alice", password="secret2"
            )

    def test_delete_user_success(self):
        user = self.user_module.create_user(
            self.session, username="alice", password="secret"
        )
        assert user.id is not None

        self.user_module.delete_user(self.session, user.id)

        deleted = self.session.get(User, user.id)
        self.assertIsNone(deleted)

    def test_delete_user_missing_raises(self):
        with self.assertRaises(self.user_module.NoSuchUserError):
            self.user_module.delete_user(self.session, 999)

    def test_login_user_success_sets_tokens_and_expiry(self):
        self.user_module.create_user(self.session, username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            access_token, refresh_token = self.user_module.login_user(
                self.session, "alice", "secret"
            )

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
            self.user_module.login_user(self.session, "unknown", "secret")

    def test_login_user_without_password_raises(self):
        user = User(username="alice", password_hash=None)
        self.session.add(user)
        self.session.commit()

        with self.assertRaises(self.user_module.InvalidPasswordError):
            self.user_module.login_user(self.session, "alice", "secret")

    def test_login_user_wrong_password_raises(self):
        self.user_module.create_user(self.session, username="alice", password="secret")

        with self.assertRaises(self.user_module.InvalidPasswordError):
            self.user_module.login_user(self.session, "alice", "wrong")

    def test_logout_user_success_clears_tokens(self):
        self.user_module.create_user(self.session, username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user(self.session, "alice", "secret")

        with patch.object(self.user_module, "time", return_value=1001.0):
            self.user_module.logout_user(self.session, "access_1")

        user = self.session.exec(
            self.user_module.select(User).where(User.username == "alice")
        ).first()
        self.assertIsNotNone(user)
        assert user is not None
        self.assertIsNone(user.access_token)
        self.assertIsNone(user.refresh_token)

    def test_logout_user_missing_raises(self):
        with self.assertRaises(self.user_module.NoSuchUserError):
            self.user_module.logout_user(self.session, "missing")

    def test_logout_user_expired_token_raises(self):
        self.user_module.create_user(self.session, username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user(self.session, "alice", "secret")

        with patch.object(
            self.user_module,
            "time",
            return_value=1000.0 + self.user_module.ACCESS_TOKEN_EXPIRY + 1,
        ):
            with self.assertRaises(self.user_module.InvalidPasswordError):
                self.user_module.logout_user(self.session, "access_1")

    def test_refresh_token_success(self):
        self.user_module.create_user(self.session, username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user(self.session, "alice", "secret")

        with patch.object(
            self.user_module.secrets, "token_urlsafe", return_value="refresh_2"
        ), patch.object(self.user_module, "time", return_value=1001.0):
            token = self.user_module.refresh_token(self.session, "access_1")

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
            self.user_module.refresh_token(self.session, "missing")

    def test_refresh_token_expired_access_raises(self):
        self.user_module.create_user(self.session, username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user(self.session, "alice", "secret")

        with patch.object(
            self.user_module,
            "time",
            return_value=1000.0 + self.user_module.ACCESS_TOKEN_EXPIRY + 1,
        ):
            with self.assertRaises(self.user_module.InvalidPasswordError):
                self.user_module.refresh_token(self.session, "access_1")

    def test_get_user_by_refresh_token_not_found(self):
        result = self.user_module.get_user_by_refresh_token(self.session, "missing")
        self.assertIsNone(result)

    def test_get_user_by_refresh_token_expired_returns_none(self):
        self.user_module.create_user(self.session, username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user(self.session, "alice", "secret")

        with patch.object(
            self.user_module,
            "time",
            return_value=1000.0 + self.user_module.REFRESH_TOKEN_EXPIRY + 1,
        ):
            user = self.user_module.get_user_by_refresh_token(self.session, "refresh_1")

        self.assertIsNone(user)

    def test_get_user_by_refresh_token_success(self):
        self.user_module.create_user(self.session, username="alice", password="secret")
        with patch.object(
            self.user_module.secrets,
            "token_urlsafe",
            side_effect=["access_1", "refresh_1"],
        ), patch.object(self.user_module, "time", return_value=1000.0):
            self.user_module.login_user(self.session, "alice", "secret")

        with patch.object(self.user_module, "time", return_value=1001.0):
            user = self.user_module.get_user_by_refresh_token(self.session, "refresh_1")

        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.username, "alice")


if __name__ == "__main__":
    unittest.main()
