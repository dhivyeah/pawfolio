import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import db as db_module


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Every test runs against a throwaway SQLite file, never the real pawfolio.db."""
    test_db_path = str(tmp_path / "test_pawfolio.db")
    test_photos_dir = str(tmp_path / "photos")
    os.makedirs(test_photos_dir, exist_ok=True)
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)
    monkeypatch.setattr(db_module, "PHOTOS_DIR", test_photos_dir)
    db_module.init_db()
    yield
