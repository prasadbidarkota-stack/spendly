import sqlite3
from datetime import datetime

import pytest
from werkzeug.security import check_password_hash

import database.db as db_module
from database.db import get_db, init_db, seed_db

FIXED_CATEGORIES = {
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
}


# --------------------------------------------------------------------- #
# get_db()
# --------------------------------------------------------------------- #

def test_get_db_row_factory_is_sqlite_row(temp_db_path):
    conn = get_db()
    assert conn.row_factory is sqlite3.Row
    conn.close()


def test_get_db_enables_foreign_keys(temp_db_path):
    conn = get_db()
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_get_db_creates_file_at_db_path(initialized_db):
    assert initialized_db.exists()


# --------------------------------------------------------------------- #
# init_db()
# --------------------------------------------------------------------- #

def test_users_table_schema(initialized_db):
    conn = get_db()
    columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(users)")}
    conn.close()

    assert set(columns) == {"id", "name", "email", "password_hash", "created_at"}
    assert columns["id"]["pk"] == 1
    assert columns["name"]["notnull"] == 1
    assert columns["email"]["notnull"] == 1
    assert columns["password_hash"]["notnull"] == 1


def test_users_email_is_unique(initialized_db):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("A", "dup@example.com", "hash1"),
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("B", "dup@example.com", "hash2"),
        )
    conn.close()


def test_expenses_table_schema(initialized_db):
    conn = get_db()
    columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(expenses)")}
    conn.close()

    assert set(columns) == {
        "id",
        "user_id",
        "amount",
        "category",
        "date",
        "description",
        "created_at",
    }
    assert columns["user_id"]["notnull"] == 1
    assert columns["amount"]["notnull"] == 1
    assert columns["category"]["notnull"] == 1
    assert columns["date"]["notnull"] == 1
    assert columns["description"]["notnull"] == 0


def test_expenses_foreign_key_to_users(initialized_db):
    conn = get_db()
    fks = conn.execute("PRAGMA foreign_key_list(expenses)").fetchall()
    conn.close()

    assert len(fks) == 1
    assert fks[0]["table"] == "users"
    assert fks[0]["from"] == "user_id"
    assert fks[0]["to"] == "id"


def test_amount_column_is_real(initialized_db):
    conn = get_db()
    columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(expenses)")}
    conn.close()

    assert columns["amount"]["type"].upper() == "REAL"


def test_init_db_is_idempotent(initialized_db):
    init_db()  # should not raise
    conn = get_db()
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    conn.close()
    assert {"users", "expenses"}.issubset(tables)


# --------------------------------------------------------------------- #
# seed_db()
# --------------------------------------------------------------------- #

def test_seed_db_inserts_demo_user_with_hashed_password(seeded_db):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()

    assert user is not None
    assert user["name"] == "Demo User"
    assert user["password_hash"] != "demo123"
    assert check_password_hash(user["password_hash"], "demo123") is True


def test_seed_db_inserts_eight_expenses_for_demo_user(seeded_db):
    conn = get_db()
    user_id = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()["id"]
    expenses = conn.execute("SELECT * FROM expenses").fetchall()
    conn.close()

    assert len(expenses) == 8
    assert all(e["user_id"] == user_id for e in expenses)


def test_seed_db_expenses_cover_fixed_category_list(seeded_db):
    conn = get_db()
    categories = {row["category"] for row in conn.execute("SELECT DISTINCT category FROM expenses")}
    conn.close()

    assert categories.issubset(FIXED_CATEGORIES)
    assert categories == FIXED_CATEGORIES  # all 7 covered by the seed data


def test_seed_db_expense_dates_are_valid_iso_format(seeded_db):
    conn = get_db()
    dates = [row["date"] for row in conn.execute("SELECT date FROM expenses")]
    conn.close()

    for d in dates:
        datetime.strptime(d, "%Y-%m-%d")


def test_seed_db_dates_within_current_month(seeded_db):
    today = datetime.today()
    conn = get_db()
    dates = [row["date"] for row in conn.execute("SELECT date FROM expenses")]
    conn.close()

    for d in dates:
        parsed = datetime.strptime(d, "%Y-%m-%d")
        assert (parsed.year, parsed.month) == (today.year, today.month)


def test_seed_db_is_idempotent_no_duplicate_rows(seeded_db):
    seed_db()  # second call should be a no-op

    conn = get_db()
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    expense_count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()

    assert user_count == 1
    assert expense_count == 8


# --------------------------------------------------------------------- #
# Error handling (spec Section 13)
# --------------------------------------------------------------------- #

def test_duplicate_email_insert_raises_integrity_error(seeded_db):
    conn = get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Someone Else", "demo@spendly.com", "irrelevant"),
        )
    conn.close()


def test_expense_with_invalid_user_id_raises_integrity_error(initialized_db):
    conn = get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (999999, 10.0, "Other", "2026-01-01"),
        )
    conn.close()


def test_invalid_query_raises_operational_error(initialized_db):
    conn = get_db()
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT * FROM does_not_exist")
    conn.close()
