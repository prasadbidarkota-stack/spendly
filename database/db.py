"""
Database access layer for Spendly.

get_db()   — returns a SQLite connection with row_factory and foreign keys enabled
init_db()  — creates all tables using CREATE TABLE IF NOT EXISTS
seed_db()  — inserts sample data for development
"""

import calendar
import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expense_tracker.db"
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """
    )
    db.commit()
    db.close()


def seed_db():
    db = get_db()

    existing = db.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    if existing:
        db.close()
        return

    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    today = date.today()
    year, month = today.year, today.month
    days_in_month = calendar.monthrange(year, month)[1]

    def _d(day_of_month):
        return date(year, month, min(day_of_month, days_in_month)).isoformat()

    sample_expenses = [
        (user_id, 4500.00, "Bills", "Electricity bill", _d(1)),
        (user_id, 3200.00, "Food", "Groceries", _d(3)),
        (user_id, 2050.00, "Health", "Pharmacy", _d(6)),
        (user_id, 1800.00, "Transport", "Cab fares", _d(9)),
        (user_id, 1200.00, "Entertainment", "Movie night", _d(13)),
        (user_id, 2600.00, "Shopping", "New shoes", _d(18)),
        (user_id, 850.00, "Food", "Dinner with friends", _d(24)),
        (user_id, 500.00, "Other", "Miscellaneous", _d(27)),
    ]
    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, description, date) "
        "VALUES (?, ?, ?, ?, ?)",
        sample_expenses,
    )

    db.commit()
    db.close()


if __name__ == "__main__":
    init_db()
    seed_db()
    print(f"Initialized database at {DB_PATH}")
