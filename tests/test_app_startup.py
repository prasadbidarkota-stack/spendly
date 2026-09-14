import importlib
import sys


def test_app_imports_and_initializes_isolated_db(tmp_path, monkeypatch):
    import database.db as db_module

    db_file = tmp_path / "startup_test.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file))

    sys.modules.pop("app", None)
    try:
        app_module = importlib.import_module("app")
        assert db_file.exists()
        assert app_module.app.url_map is not None
    finally:
        sys.modules.pop("app", None)
