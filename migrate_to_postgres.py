"""One-time data migration: local pawfolio.db (SQLite) -> hosted Supabase Postgres.

Run once, from the project root, after DATABASE_URL is set in .env:

    python migrate_to_postgres.py

Safe to re-run: refuses to touch Postgres if the profiles table there already has rows,
so it can't silently double-insert your data. Preserves every row's original id (so
existing foreign keys -- friend_profile_id, profile_vets, siblings, etc. -- keep pointing
at the right thing) and resets each table's auto-increment sequence afterward so new rows
created through the app keep numbering forward from where SQLite left off.
"""
import sqlite3
import sys

import db as db_module

SQLITE_PATH = "pawfolio.db"

# profiles and vets first (nothing else references anything but them); everything else
# can follow in any order since they only ever point back at those two.
TABLE_ORDER = [
    "profiles", "vets", "vaccinations", "medications", "friends", "surgeries",
    "vet_visits", "profile_vets", "baths", "food_refills", "boarding_stays",
    "siblings", "notification_log", "notified_events",
]


def _sqlite_rows(conn, table):
    conn.row_factory = sqlite3.Row
    cur = conn.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    return cols, [dict(r) for r in cur.fetchall()]


def main():
    if not db_module.DATABASE_URL:
        print("DATABASE_URL is not set -- add it to .env first (see .env.example). Aborting.")
        sys.exit(1)

    print("Ensuring the Postgres schema exists (tables, indexes)...")
    db_module.init_db()

    with db_module.get_conn() as pg:
        existing = pg.execute("SELECT COUNT(*) AS c FROM profiles").fetchone()["c"]
        if existing:
            print(
                f"Postgres already has {existing} row(s) in profiles -- refusing to run, to "
                "avoid duplicating data. If you really want to re-migrate from scratch, "
                "truncate the Postgres tables yourself first, then re-run this script."
            )
            sys.exit(1)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    total = 0
    with db_module.get_conn() as pg:
        for table in TABLE_ORDER:
            cols, rows = _sqlite_rows(sqlite_conn, table)
            if not rows:
                print(f"  {table}: 0 rows, skipping.")
                continue
            col_list = ", ".join(cols)
            placeholders = ", ".join(["%s"] * len(cols))
            for row in rows:
                pg.execute(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                    [row[c] for c in cols],
                )
            # Move the SERIAL sequence past the highest id we just inserted, so the next
            # row created through the app (which doesn't specify an id) doesn't collide
            # with one we just migrated.
            pg.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"(SELECT COALESCE(MAX(id), 1) FROM {table}))"
            )
            print(f"  {table}: migrated {len(rows)} row(s).")
            total += len(rows)
    sqlite_conn.close()
    print(f"\nDone -- {total} row(s) migrated from {SQLITE_PATH} into Postgres.")
    print("Verify in your Supabase dashboard (Table Editor) before deleting the local .db file.")


if __name__ == "__main__":
    main()
