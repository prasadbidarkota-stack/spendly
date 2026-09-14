import database.db as db_module
import pytest


@pytest.fixture
def temp_db_path(tmp_path, monkeypatch):
    """Redirect database.db.DB_PATH to an isolated file for this test only."""
    db_file = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file))
    return db_file


@pytest.fixture
def initialized_db(temp_db_path):
    """A temp DB with schema created but not seeded."""
    db_module.init_db()
    return temp_db_path


@pytest.fixture
def seeded_db(initialized_db):
    """A temp DB with schema created and demo data seeded."""
    db_module.seed_db()
    return initialized_db
