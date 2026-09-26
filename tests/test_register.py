import sqlite3
import sys

import pytest
from werkzeug.security import check_password_hash

import database.db as db_module


VALID = {"name": "Test User", "email": "test@example.com", "password": "password123"}
DUPLICATE_MSG = "An account with that email already exists."


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    sys.modules.pop("app", None)
    import app as module  # init_db + seed_db run against the tmp DB

    module.app.config["TESTING"] = True
    yield module
    sys.modules.pop("app", None)


@pytest.fixture
def client(app_module):
    with app_module.app.test_client() as c:
        yield c


def user_rows(email):
    db = db_module.get_db()
    try:
        return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchall()
    finally:
        db.close()


def user_count():
    db = db_module.get_db()
    try:
        return db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        db.close()


def test_get_register_shows_form(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b'<form method="POST" action="/register">' in resp.data
    assert b"auth-error" not in resp.data


def test_register_success_redirects_to_login(client):
    resp = client.post("/register", data=VALID)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")

    page = client.get("/login")
    assert b'<div class="auth-success">Account created. Please sign in.</div>' in page.data


def test_register_stores_hashed_password(client):
    client.post("/register", data=VALID)
    rows = user_rows("test@example.com")
    assert len(rows) == 1
    stored = rows[0]["password_hash"]
    assert stored != "password123"
    assert stored.startswith("scrypt:")
    assert check_password_hash(stored, "password123")
    assert rows[0]["name"] == "Test User"


def test_register_normalises_email(client):
    client.post("/register", data={**VALID, "email": "  Test@Example.COM "})
    assert len(user_rows("test@example.com")) == 1


def test_duplicate_email_rejected(client):
    client.post("/register", data=VALID)
    before = user_count()
    resp = client.post("/register", data=VALID)
    assert resp.status_code == 400
    assert DUPLICATE_MSG.encode() in resp.data
    assert user_count() == before


def test_duplicate_email_case_insensitive(client):
    client.post("/register", data=VALID)
    before = user_count()
    resp = client.post("/register", data={**VALID, "email": "TEST@example.com"})
    assert resp.status_code == 400
    assert DUPLICATE_MSG.encode() in resp.data
    assert user_count() == before


def test_seeded_demo_user_is_duplicate(client):
    resp = client.post("/register", data={**VALID, "email": "demo@spendly.com"})
    assert resp.status_code == 400
    assert DUPLICATE_MSG.encode() in resp.data


def test_short_password_rejected(client):
    resp = client.post("/register", data={**VALID, "password": "1234567"})
    assert resp.status_code == 400
    assert b"Password must be at least 8 characters." in resp.data
    assert user_rows("test@example.com") == []


@pytest.mark.parametrize("email", ["nope", "a@b", "@b.com", "a@", "a.b@c"])
def test_invalid_email_rejected(client, email):
    resp = client.post("/register", data={**VALID, "email": email})
    assert resp.status_code == 400
    assert b"Please enter a valid email address." in resp.data


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": "   "},
        {"email": ""},
        {"email": "   "},
        {"password": ""},
    ],
)
def test_blank_fields_rejected(client, overrides):
    resp = client.post("/register", data={**VALID, **overrides})
    assert resp.status_code == 400
    assert b"All fields are required." in resp.data


@pytest.mark.parametrize("missing", ["name", "email", "password"])
def test_missing_field_rejected(client, missing):
    data = {k: v for k, v in VALID.items() if k != missing}
    resp = client.post("/register", data=data)
    assert resp.status_code == 400
    assert b"All fields are required." in resp.data


def test_error_refills_name_and_email_not_password(client):
    resp = client.post("/register", data={**VALID, "password": "short1"})
    assert resp.status_code == 400
    assert b'value="Test User"' in resp.data
    assert b'value="test@example.com"' in resp.data
    assert b"short1" not in resp.data


def test_integrity_error_backstop(app_module, client, monkeypatch):
    """Simulate a race: the duplicate SELECT misses, but the INSERT hits UNIQUE."""
    real_get_db = app_module.get_db

    class RacyConnection:
        def __init__(self, conn):
            self._conn = conn

        def execute(self, sql, params=()):
            cursor = self._conn.execute(sql, params)
            if sql.lstrip().upper().startswith("SELECT ID FROM USERS"):
                return self._conn.execute("SELECT id FROM users WHERE 0")
            return cursor

        def __getattr__(self, name):
            return getattr(self._conn, name)

    monkeypatch.setattr(app_module, "get_db", lambda: RacyConnection(real_get_db()))
    before = user_count()
    resp = client.post("/register", data={**VALID, "email": "demo@spendly.com"})
    assert resp.status_code == 400
    assert DUPLICATE_MSG.encode() in resp.data
    assert user_count() == before


def test_no_session_set(client):
    client.post("/register", data=VALID)
    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert [k for k in sess.keys() if k != "_flashes"] == []


@pytest.mark.parametrize("path", ["/", "/login", "/terms", "/privacy"])
def test_other_pages_still_load(client, path):
    assert client.get(path).status_code == 200
