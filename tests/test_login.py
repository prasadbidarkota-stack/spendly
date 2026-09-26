import sys

import pytest

import database.db as db_module


DEMO = {"email": "demo@spendly.com", "password": "demo123"}
INVALID_MSG = "Invalid email or password."
REQUIRED_MSG = "Email and password are required."


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


def login(client, **overrides):
    return client.post("/login", data={**DEMO, **overrides})


def demo_user_id():
    db = db_module.get_db()
    try:
        return db.execute(
            "SELECT id FROM users WHERE email = ?", (DEMO["email"],)
        ).fetchone()["id"]
    finally:
        db.close()


def session_data(client):
    with client.session_transaction() as sess:
        return dict(sess)


def test_get_login_shows_form(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b'<form method="POST" action="/login">' in resp.data
    assert b"auth-error" not in resp.data


def test_login_success_redirects_to_profile(client):
    resp = login(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")
    sess = session_data(client)
    assert sess["user_id"] == demo_user_id()
    assert sess["user_name"] == "Demo User"


def test_login_session_has_only_expected_keys(client):
    login(client)
    assert set(session_data(client)) == {"user_id", "user_name"}


def test_login_normalises_email(client):
    resp = login(client, email="  Demo@Spendly.com ")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_registered_user_can_login(client):
    creds = {"email": "new@example.com", "password": "password123"}
    client.post("/register", data={"name": "New User", **creds})
    resp = client.post("/login", data=creds)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")
    assert session_data(client)["user_name"] == "New User"


def test_wrong_password_rejected(client):
    resp = login(client, password="not-the-password")
    assert resp.status_code == 401
    assert INVALID_MSG.encode() in resp.data
    assert b'value="demo@spendly.com"' in resp.data
    assert b"not-the-password" not in resp.data
    assert "user_id" not in session_data(client)


def test_unknown_email_same_message(client):
    resp = login(client, email="nobody@example.com")
    assert resp.status_code == 401
    assert INVALID_MSG.encode() in resp.data
    assert "user_id" not in session_data(client)


@pytest.mark.parametrize(
    "data",
    [
        {"email": "", "password": "demo123"},
        {"email": "demo@spendly.com", "password": ""},
        {"email": "   ", "password": "demo123"},
        {"password": "demo123"},
        {"email": "demo@spendly.com"},
    ],
)
def test_blank_fields_rejected(client, data):
    resp = client.post("/login", data=data)
    assert resp.status_code == 400
    assert REQUIRED_MSG.encode() in resp.data


def test_login_page_redirects_when_logged_in(client):
    login(client)
    resp = client.get("/login")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_register_page_redirects_when_logged_in(client):
    login(client)
    resp = client.get("/register")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_navbar_logged_in(client):
    login(client)
    resp = client.get("/")
    assert b"Demo User" in resp.data
    assert b"Sign out" in resp.data
    assert b"Get started" not in resp.data


def test_navbar_logged_out(client):
    resp = client.get("/")
    assert b"Sign in" in resp.data
    assert b"Get started" in resp.data
    assert b"Sign out" not in resp.data


def test_logout_clears_session_and_flashes(client):
    login(client)
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    assert "user_id" not in session_data(client)

    page = client.get("/login")
    assert b'<div class="auth-success">You have been signed out.</div>' in page.data


def test_logout_when_logged_out(client):
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_login_page_available_after_logout(client):
    login(client)
    client.get("/logout")
    resp = client.get("/login")
    assert resp.status_code == 200


@pytest.mark.parametrize("path", ["/", "/register", "/terms", "/privacy"])
def test_other_pages_still_load(client, path):
    assert client.get(path).status_code == 200
