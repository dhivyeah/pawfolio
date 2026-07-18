import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import psycopg2
import db as db_module


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    """Every test runs against a throwaway Postgres schema on the same Supabase database,
    never the real `public` schema. Needs DATABASE_URL set (same as the app) -- there's no
    local-file fallback anymore now that Pawfolio is Postgres-only. Each test gets its own
    uniquely-named schema so tests can run in parallel and never see each other's data,
    then the schema is dropped afterward rather than left to accumulate."""
    if not db_module.DATABASE_URL:
        pytest.skip("DATABASE_URL not set -- tests need a live Postgres connection now that Pawfolio is Postgres-only.")

    test_schema = f"test_{uuid.uuid4().hex[:16]}"
    monkeypatch.setattr(db_module, "DB_SCHEMA", test_schema)
    db_module.init_db()
    yield
    conn = psycopg2.connect(db_module.DATABASE_URL)
    conn.autocommit = True
    conn.cursor().execute(f'DROP SCHEMA IF EXISTS "{test_schema}" CASCADE')
    conn.close()


@pytest.fixture
def owner_id():
    """A fake-but-consistent owner id for tests -- Phase 4's owner_id column is a plain
    UUID (not a foreign key into Supabase's own auth.users table, see db.py's init_db()
    for why), so any well-formed UUID works here without needing a real Supabase Auth
    user to exist for every test run."""
    return str(uuid.uuid4())
