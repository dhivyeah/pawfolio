"""Postgres data access layer for Pawfolio (hosted on Supabase), via psycopg2. No ORM.

Was SQLite; migrated to hosted Postgres so the app can run on Streamlit Community Cloud
without a local file for storage. See migrate_to_postgres.py for the one-time data move
from an existing local pawfolio.db, and README/KNOWN_ISSUES for the deployment notes.
"""
import os
import re
from datetime import date, datetime, timedelta
from contextlib import contextmanager

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")

# Which Postgres schema to operate in. Defaults to "public" (the real app data);
# tests point this at a throwaway per-test schema instead (see tests/conftest.py) so
# they never touch real data, without needing a second database.
_SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

# Every db.py function opens its own `with get_conn() as conn:` block -- a page like the
# dashboard makes 15-20+ of these per load (one per record type, per dog). Against local
# SQLite that was practically free. Against hosted Postgres, each one used to be a fresh
# TCP+TLS handshake to Supabase (~300ms measured), so a dashboard load added up to ~20s.
# A small connection pool fixes that: borrowing an already-open connection is a
# microsecond-scale lock/dict operation instead of a network round-trip. Threaded because
# a Streamlit process can be serving more than one browser session at once.
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to your .env file (see .env.example) -- "
                "it's the Supabase Postgres connection string, and Pawfolio has no local "
                "SQLite fallback anymore."
            )
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10, DATABASE_URL, cursor_factory=RealDictCursor
        )
    return _pool


class _ConnWrapper:
    """Thin convenience layer so call sites can keep writing `conn.execute(sql, params)`
    the way they did against sqlite3's connection-level `.execute()` shorthand, instead of
    every one of the ~50 call sites in this file having to open its own cursor. Not a
    SQL-dialect translator -- every query string below already uses Postgres's own `%s`
    placeholders, not sqlite3's `?`."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur


class PawfolioDBError(Exception):
    """Raised for any database problem, carrying a message that's safe to show a real
    visitor. The actual underlying error -- which can include hostnames, resolved IPs,
    and other connection details -- is always logged server-side via print() first (so
    it's still visible in Streamlit Cloud's logs for debugging) and never included in
    this exception's own message or allowed to reach the UI as a raw traceback."""


@contextmanager
def get_conn():
    if not _SCHEMA_RE.match(DB_SCHEMA):
        raise RuntimeError(f"Invalid DB_SCHEMA {DB_SCHEMA!r} -- expected a plain identifier.")
    try:
        pool = _get_pool()
        raw_conn = pool.getconn()
    except Exception as e:
        print(f"[db] Could not get a database connection: {e}", flush=True)
        raise PawfolioDBError("Couldn't connect to the database right now.") from None

    conn = _ConnWrapper(raw_conn)
    try:
        # Re-applied on every borrow (not just once when the connection was first opened)
        # since a pooled connection can outlive any single caller's idea of which schema
        # is current -- tests borrow the same pool but each pick their own DB_SCHEMA.
        conn.execute(f'SET search_path TO "{DB_SCHEMA}"')
        yield conn
        raw_conn.commit()
    except psycopg2.Error as e:
        raw_conn.rollback()
        print(f"[db] Database error: {e}", flush=True)
        raise PawfolioDBError("Something went wrong talking to the database.") from None
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        pool.putconn(raw_conn)


def _ensure_column_sql(table: str, column: str, column_def: str) -> str:
    """Additive migration helper: add a column to an existing table if it isn't there yet.
    Postgres's own IF NOT EXISTS makes this a one-liner -- no need for sqlite3's PRAGMA
    table_info introspection dance. Returns SQL text rather than executing it directly so
    init_db() can batch it in with everything else into one round-trip (see below)."""
    return f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_def};"


def init_db():
    # Every statement here is schema DDL with no parameters, so they can all be sent to
    # Postgres as one semicolon-separated script instead of one round-trip each -- on a
    # fresh session this used to be ~20 sequential network round-trips (each carrying real
    # latency to Supabase) before a single query had even run. init_db() itself runs on
    # every fresh session (see app.py's session gate), so that cost was paid on every new
    # visit, not just the very first ever.
    statements = [
        f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}";',
        """CREATE TABLE IF NOT EXISTS profiles (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            photo_path TEXT,
            dob TEXT,
            dob_estimated INTEGER DEFAULT 0,
            breed TEXT,
            profile_type TEXT NOT NULL CHECK (profile_type IN ('my_dog', 'community_dog')),
            date_added TEXT NOT NULL,
            hangout_location TEXT,
            reg_id TEXT,
            reg_last_renewed TEXT,
            reg_next_due TEXT,
            likes TEXT,
            dislikes TEXT,
            favorite_toys TEXT,
            favorite_foods TEXT,
            foods_to_avoid TEXT,
            favorite_games TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS vaccinations (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            vaccine_name TEXT NOT NULL,
            date_given TEXT,
            next_due_date TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS medications (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            med_name TEXT NOT NULL,
            dosage TEXT,
            frequency TEXT,
            start_date TEXT,
            end_date TEXT,
            ongoing INTEGER DEFAULT 0
        );""",
        """CREATE TABLE IF NOT EXISTS friends (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            friend_name TEXT NOT NULL,
            friend_birthday TEXT,
            notes TEXT
        );""",
        # A friend can either be freeform (friend_name/friend_birthday typed in directly) or
        # a link to another real profile already in Pawfolio — friend_profile_id set, name/
        # birthday looked up live from that profile instead so it can't go stale.
        _ensure_column_sql("friends", "friend_profile_id", "INTEGER REFERENCES profiles(id) ON DELETE CASCADE"),

        # ---- Additive migration: expand Health group on the existing profiles table ----
        _ensure_column_sql("profiles", "spay_neuter_status", "TEXT DEFAULT 'unknown'"),
        _ensure_column_sql("profiles", "spay_neuter_date", "TEXT"),
        _ensure_column_sql("profiles", "nickname", "TEXT"),
        _ensure_column_sql("profiles", "other_notes", "TEXT"),

        """CREATE TABLE IF NOT EXISTS surgeries (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            surgery_name TEXT NOT NULL,
            surgery_date TEXT,
            notes TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS vet_visits (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            visit_date TEXT,
            reason TEXT,
            notes TEXT
        );""",

        # ---- Shared vet directory, reusable across profiles ----
        """CREATE TABLE IF NOT EXISTS vets (
            id SERIAL PRIMARY KEY,
            vet_name TEXT NOT NULL,
            clinic_name TEXT,
            phone TEXT,
            address TEXT,
            notes TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS profile_vets (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            vet_id INTEGER NOT NULL REFERENCES vets(id) ON DELETE CASCADE,
            is_primary INTEGER DEFAULT 0
        );""",
        # Belt-and-suspenders against the same vet being linked to the same profile twice
        # (the application-level guard is in link_vet_to_profile). IF NOT EXISTS makes this
        # safe to re-run; a genuine duplicate-data conflict is left to raise loudly rather
        # than being silently swallowed, since that would indicate real corruption worth
        # seeing rather than hiding.
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_profile_vets_unique ON profile_vets(profile_id, vet_id);",

        # ---- Sibling links between two profiles (symmetric, stored once per pair) ----
        """CREATE TABLE IF NOT EXISTS siblings (
            id SERIAL PRIMARY KEY,
            profile_id_a INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            profile_id_b INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(profile_id_a, profile_id_b)
        );""",

        # ---- Care & Logistics group ----
        """CREATE TABLE IF NOT EXISTS baths (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            bath_date TEXT,
            next_due_date TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS food_refills (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            food_type TEXT,
            last_refill_date TEXT,
            next_refill_date TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS boarding_stays (
            id SERIAL PRIMARY KEY,
            profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            facility_name TEXT,
            check_in_date TEXT,
            check_out_date TEXT,
            notes TEXT
        );""",

        # ---- Email digest notifications ----
        # notified_events remembers which (event_type, record_id, state_key, milestone)
        # combos have already been included in a sent digest. state_key is the event's due
        # date for date-bound events, or the occurrence date for annual ones (birthdays) --
        # see notifications.event_state_key. milestone is which countdown checkpoint (7/3/1/0
        # days out) this notification was for -- see notifications.MILESTONES -- so an item
        # is emailed once as it crosses into "due in 7 days," once again at "3 days," etc.,
        # rather than a single one-time notification. When the underlying record changes (due
        # date edited) or a birthday rolls to its next occurrence, state_key changes too, so
        # the whole countdown starts fresh.
        """CREATE TABLE IF NOT EXISTS notified_events (
            id SERIAL PRIMARY KEY,
            event_type TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            state_key TEXT NOT NULL,
            milestone INTEGER NOT NULL,
            notified_at TEXT NOT NULL
        );""",
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_notified_events_unique
           ON notified_events(event_type, record_id, state_key, milestone);""",
        # notification_log caps digest sending to once per day regardless of how many new
        # events show up -- only gets a row when a digest was actually, successfully sent.
        """CREATE TABLE IF NOT EXISTS notification_log (
            id SERIAL PRIMARY KEY,
            sent_at TEXT NOT NULL
        );""",
    ]
    with get_conn() as conn:
        conn.execute("\n".join(statements))


# ---------- Profiles ----------

def create_profile(data: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO profiles (
                name, nickname, photo_path, dob, dob_estimated, breed, profile_type, date_added,
                hangout_location, reg_id, reg_last_renewed, reg_next_due,
                likes, dislikes, favorite_toys, favorite_foods, foods_to_avoid, favorite_games,
                spay_neuter_status, spay_neuter_date, other_notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            data.get("name"), data.get("nickname"), data.get("photo_path"), data.get("dob"),
            int(data.get("dob_estimated", 0)), data.get("breed"), data.get("profile_type"),
            data.get("date_added", date.today().isoformat()), data.get("hangout_location"),
            data.get("reg_id"), data.get("reg_last_renewed"), data.get("reg_next_due"),
            data.get("likes"), data.get("dislikes"), data.get("favorite_toys"),
            data.get("favorite_foods"), data.get("foods_to_avoid"), data.get("favorite_games"),
            data.get("spay_neuter_status", "unknown"), data.get("spay_neuter_date"),
            data.get("other_notes"),
        ))
        return cur.fetchone()["id"]


def update_profile(profile_id: int, data: dict):
    fields = [
        "name", "nickname", "photo_path", "dob", "dob_estimated", "breed", "profile_type",
        "hangout_location", "reg_id", "reg_last_renewed", "reg_next_due",
        "likes", "dislikes", "favorite_toys", "favorite_foods", "foods_to_avoid", "favorite_games",
        "spay_neuter_status", "spay_neuter_date", "other_notes"
    ]
    set_clause = ", ".join(f"{f} = %s" for f in fields)
    values = [data.get(f) for f in fields]
    values.append(profile_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE profiles SET {set_clause} WHERE id = %s", values)


def delete_profile(profile_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM profiles WHERE id = %s", (profile_id,))


def get_profile(profile_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = %s", (profile_id,)).fetchone()
        return dict(row) if row else None


def get_all_profiles(profile_type: str = None):
    with get_conn() as conn:
        if profile_type:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE profile_type = %s ORDER BY LOWER(name)",
                (profile_type,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM profiles ORDER BY LOWER(name)").fetchall()
        return [dict(r) for r in rows]


def get_recently_added_profiles(days: int = 7):
    """Profiles added within the last `days` days, most recent first."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM profiles WHERE date_added >= %s ORDER BY date_added DESC, id DESC",
            (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Vaccinations ----------

def add_vaccination(profile_id, vaccine_name, date_given, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO vaccinations (profile_id, vaccine_name, date_given, next_due_date) VALUES (%s,%s,%s,%s)",
            (profile_id, vaccine_name, date_given, next_due_date)
        )


def get_vaccinations(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM vaccinations WHERE profile_id = %s ORDER BY next_due_date IS NULL, next_due_date",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_vaccination(vacc_id, vaccine_name, date_given, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vaccinations SET vaccine_name=%s, date_given=%s, next_due_date=%s WHERE id=%s",
            (vaccine_name, date_given, next_due_date, vacc_id)
        )


def delete_vaccination(vacc_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM vaccinations WHERE id = %s", (vacc_id,))


# ---------- Medications ----------

def add_medication(profile_id, med_name, dosage, frequency, start_date, end_date, ongoing):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO medications (profile_id, med_name, dosage, frequency, start_date, end_date, ongoing)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (profile_id, med_name, dosage, frequency, start_date, end_date, int(ongoing))
        )


def get_medications(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM medications WHERE profile_id = %s ORDER BY ongoing DESC, end_date",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_medication(med_id, med_name, dosage, frequency, start_date, end_date, ongoing):
    with get_conn() as conn:
        conn.execute(
            """UPDATE medications SET med_name=%s, dosage=%s, frequency=%s, start_date=%s, end_date=%s, ongoing=%s
               WHERE id=%s""",
            (med_name, dosage, frequency, start_date, end_date, int(ongoing), med_id)
        )


def delete_medication(med_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM medications WHERE id = %s", (med_id,))


# ---------- Friends ----------

def add_friend(profile_id, friend_name, friend_birthday, notes, friend_profile_id=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO friends (profile_id, friend_name, friend_birthday, notes, friend_profile_id)
               VALUES (%s,%s,%s,%s,%s)""",
            (profile_id, friend_name, friend_birthday, notes, friend_profile_id)
        )


def get_friends(profile_id):
    """Friends for a profile. A friend may be freeform (friend_name/friend_birthday typed in
    directly) or a link to another real profile (friend_profile_id set) — for linked friends,
    linked_name/linked_photo_path/linked_dob come live from that profile so they can't go
    stale if the other profile's own name or photo changes later."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT f.*, p.name AS linked_name, p.photo_path AS linked_photo_path, p.dob AS linked_dob
            FROM friends f
            LEFT JOIN profiles p ON p.id = f.friend_profile_id
            WHERE f.profile_id = %s
            ORDER BY LOWER(COALESCE(p.name, f.friend_name))
        """, (profile_id,)).fetchall()
        return [dict(r) for r in rows]


def update_friend(friend_id, friend_name, friend_birthday, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE friends SET friend_name=%s, friend_birthday=%s, notes=%s WHERE id=%s",
            (friend_name, friend_birthday, notes, friend_id)
        )


def delete_friend(friend_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM friends WHERE id = %s", (friend_id,))


# ---------- Siblings ----------
# Symmetric relationship between two profiles, stored once per pair with the lower id
# always in profile_id_a so (A, B) and (B, A) can't both be inserted as separate rows.

def add_sibling(profile_id, other_profile_id):
    a, b = sorted((profile_id, other_profile_id))
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM siblings WHERE profile_id_a = %s AND profile_id_b = %s", (a, b)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO siblings (profile_id_a, profile_id_b) VALUES (%s, %s) RETURNING id", (a, b)
        )
        return cur.fetchone()["id"]


def get_siblings(profile_id):
    """Sibling profiles linked to this one, joined with their current name/photo."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.id AS link_id, p.id AS sibling_id, p.name AS sibling_name,
                   p.photo_path AS sibling_photo_path
            FROM siblings s
            JOIN profiles p ON p.id = CASE WHEN s.profile_id_a = %s THEN s.profile_id_b ELSE s.profile_id_a END
            WHERE s.profile_id_a = %s OR s.profile_id_b = %s
            ORDER BY LOWER(p.name)
        """, (profile_id, profile_id, profile_id)).fetchall()
        return [dict(r) for r in rows]


def remove_sibling(link_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM siblings WHERE id = %s", (link_id,))


def count_incoming_links(profile_id):
    """How many *other* profiles reference this one as a linked friend, plus how many
    sibling links it has. Both cascade-delete silently (ON DELETE CASCADE) if this
    profile is deleted — used to warn about that before it happens, since it's not
    obvious from this profile's own page that deleting it also edits other profiles."""
    with get_conn() as conn:
        friend_refs = conn.execute(
            "SELECT COUNT(*) AS c FROM friends WHERE friend_profile_id = %s", (profile_id,)
        ).fetchone()["c"]
    sibling_refs = len(get_siblings(profile_id))
    return friend_refs, sibling_refs


# ---------- Surgeries ----------

def add_surgery(profile_id, surgery_name, surgery_date, notes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO surgeries (profile_id, surgery_name, surgery_date, notes) VALUES (%s,%s,%s,%s)",
            (profile_id, surgery_name, surgery_date, notes)
        )


def get_surgeries(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM surgeries WHERE profile_id = %s ORDER BY surgery_date IS NULL, surgery_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_surgery(surgery_id, surgery_name, surgery_date, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE surgeries SET surgery_name=%s, surgery_date=%s, notes=%s WHERE id=%s",
            (surgery_name, surgery_date, notes, surgery_id)
        )


def delete_surgery(surgery_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM surgeries WHERE id = %s", (surgery_id,))


# ---------- Vet visits (history) ----------

def add_vet_visit(profile_id, visit_date, reason, notes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO vet_visits (profile_id, visit_date, reason, notes) VALUES (%s,%s,%s,%s)",
            (profile_id, visit_date, reason, notes)
        )


def get_vet_visits(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM vet_visits WHERE profile_id = %s ORDER BY visit_date IS NULL, visit_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_vet_visit(visit_id, visit_date, reason, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vet_visits SET visit_date=%s, reason=%s, notes=%s WHERE id=%s",
            (visit_date, reason, notes, visit_id)
        )


def delete_vet_visit(visit_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM vet_visits WHERE id = %s", (visit_id,))


# ---------- Vets (shared directory) ----------

def create_vet(vet_name, clinic_name, phone, address, notes):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO vets (vet_name, clinic_name, phone, address, notes) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (vet_name, clinic_name, phone, address, notes)
        )
        return cur.fetchone()["id"]


def get_all_vets():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM vets ORDER BY LOWER(vet_name)").fetchall()
        return [dict(r) for r in rows]


def get_vet(vet_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM vets WHERE id = %s", (vet_id,)).fetchone()
        return dict(row) if row else None


def update_vet(vet_id, vet_name, clinic_name, phone, address, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vets SET vet_name=%s, clinic_name=%s, phone=%s, address=%s, notes=%s WHERE id=%s",
            (vet_name, clinic_name, phone, address, notes, vet_id)
        )


def delete_vet(vet_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM vets WHERE id = %s", (vet_id,))


def link_vet_to_profile(profile_id, vet_id, is_primary=False):
    """Links a vet to a profile. If this vet is already linked to this profile, promotes
    it to primary if requested instead of creating a duplicate link."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM profile_vets WHERE profile_id = %s AND vet_id = %s",
            (profile_id, vet_id)
        ).fetchone()
        if is_primary:
            conn.execute("UPDATE profile_vets SET is_primary = 0 WHERE profile_id = %s", (profile_id,))
        if existing:
            if is_primary:
                conn.execute("UPDATE profile_vets SET is_primary = 1 WHERE id = %s", (existing["id"],))
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO profile_vets (profile_id, vet_id, is_primary) VALUES (%s,%s,%s) RETURNING id",
            (profile_id, vet_id, int(is_primary))
        )
        return cur.fetchone()["id"]


def unlink_vet_from_profile(profile_vet_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM profile_vets WHERE id = %s", (profile_vet_id,))


def set_primary_vet(profile_id, profile_vet_id):
    with get_conn() as conn:
        conn.execute("UPDATE profile_vets SET is_primary = 0 WHERE profile_id = %s", (profile_id,))
        conn.execute("UPDATE profile_vets SET is_primary = 1 WHERE id = %s", (profile_vet_id,))


def get_vets_for_profile(profile_id):
    """Vets linked to this profile, joined with vet details. Primary vet first."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT profile_vets.id AS link_id, profile_vets.is_primary AS is_primary,
                   vets.id AS vet_id, vets.vet_name, vets.clinic_name, vets.phone,
                   vets.address, vets.notes
            FROM profile_vets
            JOIN vets ON vets.id = profile_vets.vet_id
            WHERE profile_vets.profile_id = %s
            ORDER BY profile_vets.is_primary DESC, LOWER(vets.vet_name)
        """, (profile_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------- Baths ----------

def add_bath(profile_id, bath_date, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO baths (profile_id, bath_date, next_due_date) VALUES (%s,%s,%s)",
            (profile_id, bath_date, next_due_date)
        )


def get_baths(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM baths WHERE profile_id = %s ORDER BY next_due_date IS NULL, next_due_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_bath(bath_id, bath_date, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "UPDATE baths SET bath_date=%s, next_due_date=%s WHERE id=%s",
            (bath_date, next_due_date, bath_id)
        )


def delete_bath(bath_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM baths WHERE id = %s", (bath_id,))


# ---------- Food refills ----------

def add_food_refill(profile_id, food_type, last_refill_date, next_refill_date):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO food_refills (profile_id, food_type, last_refill_date, next_refill_date) VALUES (%s,%s,%s,%s)",
            (profile_id, food_type, last_refill_date, next_refill_date)
        )


def get_food_refills(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM food_refills WHERE profile_id = %s ORDER BY next_refill_date IS NULL, next_refill_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_food_refill(refill_id, food_type, last_refill_date, next_refill_date):
    with get_conn() as conn:
        conn.execute(
            "UPDATE food_refills SET food_type=%s, last_refill_date=%s, next_refill_date=%s WHERE id=%s",
            (food_type, last_refill_date, next_refill_date, refill_id)
        )


def delete_food_refill(refill_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM food_refills WHERE id = %s", (refill_id,))


# ---------- Boarding stays (history) ----------

def add_boarding_stay(profile_id, facility_name, check_in_date, check_out_date, notes):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO boarding_stays (profile_id, facility_name, check_in_date, check_out_date, notes)
               VALUES (%s,%s,%s,%s,%s)""",
            (profile_id, facility_name, check_in_date, check_out_date, notes)
        )


def get_boarding_stays(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM boarding_stays WHERE profile_id = %s ORDER BY check_in_date IS NULL, check_in_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_boarding_stay(stay_id, facility_name, check_in_date, check_out_date, notes):
    with get_conn() as conn:
        conn.execute(
            """UPDATE boarding_stays SET facility_name=%s, check_in_date=%s, check_out_date=%s, notes=%s
               WHERE id=%s""",
            (facility_name, check_in_date, check_out_date, notes, stay_id)
        )


def delete_boarding_stay(stay_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM boarding_stays WHERE id = %s", (stay_id,))


# ---------- Dashboard helpers ----------

def calc_age_str(dob: str, estimated: bool) -> str:
    """Human readable age like '2y 3m' from an ISO dob string."""
    if not dob:
        return "Unknown age"
    try:
        birth = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        return "Unknown age"
    today = date.today()
    years = today.year - birth.year
    months = today.month - birth.month
    if today.day < birth.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    prefix = "~" if estimated else ""
    if years <= 0:
        return f"{prefix}{months}mo old"
    if months == 0:
        return f"{prefix}{years}y old"
    return f"{prefix}{years}y {months}mo old"


def _next_annual_occurrence(iso_date: str, today: date):
    """Given an ISO date string (birthday-like), return (days_until_next_occurrence, age_turning)."""
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    except ValueError:
        return None, None
    try:
        next_occ = d.replace(year=today.year)
    except ValueError:
        # Feb 29 on a non-leap year
        next_occ = d.replace(year=today.year, day=28)
    if next_occ < today:
        try:
            next_occ = d.replace(year=today.year + 1)
        except ValueError:
            next_occ = d.replace(year=today.year + 1, day=28)
    days_until = (next_occ - today).days
    age_turning = next_occ.year - d.year
    return days_until, age_turning


def get_upcoming_events(horizon_days: int = 30):
    """Gather all upcoming/overdue events across every profile, sorted soonest/most overdue first.

    Fetches each record type once across every profile (6 queries total) rather than once
    per profile per type (6 x N queries) -- against local SQLite that distinction was free,
    but against hosted Postgres each query is a real network round-trip, so the old
    per-profile-per-type loop turned a 3-profile dashboard into ~19 round-trips and a
    20-profile one into ~120. Grouping happens in Python afterward via profiles_by_id
    instead of in the query, so every event's shape and the horizon/ongoing/linked-friend
    filtering rules below are unchanged from the per-profile version this replaced."""
    events = []
    today = date.today()
    profiles = get_all_profiles()
    profiles_by_id = {p["id"]: p for p in profiles}

    with get_conn() as conn:
        all_vaccinations = conn.execute(
            "SELECT * FROM vaccinations WHERE next_due_date IS NOT NULL"
        ).fetchall()
        all_medications = conn.execute(
            "SELECT * FROM medications WHERE ongoing = 0 AND end_date IS NOT NULL"
        ).fetchall()
        all_friends = conn.execute(
            "SELECT * FROM friends WHERE friend_profile_id IS NULL AND friend_birthday IS NOT NULL"
        ).fetchall()
        all_baths = conn.execute(
            "SELECT * FROM baths WHERE next_due_date IS NOT NULL"
        ).fetchall()
        all_food_refills = conn.execute(
            "SELECT * FROM food_refills WHERE next_refill_date IS NOT NULL"
        ).fetchall()
        all_boarding_stays = conn.execute(
            "SELECT * FROM boarding_stays WHERE check_in_date IS NOT NULL"
        ).fetchall()

    for v in all_vaccinations:
        p = profiles_by_id.get(v["profile_id"])
        if not p:
            continue
        try:
            due = datetime.strptime(v["next_due_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (due - today).days
        if days <= horizon_days:
            events.append({
                "type": "vaccination",
                "record_id": v["id"],
                "profile_name": p["name"],
                "profile_id": p["id"],
                "profile_type": p["profile_type"],
                "detail": v["vaccine_name"],
                "days_until": days,
                "due_date": v["next_due_date"],
            })

    for m in all_medications:
        p = profiles_by_id.get(m["profile_id"])
        if not p:
            continue
        try:
            end = datetime.strptime(m["end_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (end - today).days
        if days <= horizon_days:
            events.append({
                "type": "medication",
                "record_id": m["id"],
                "profile_name": p["name"],
                "profile_id": p["id"],
                "profile_type": p["profile_type"],
                "detail": m["med_name"],
                "days_until": days,
                "due_date": m["end_date"],
            })

    for f in all_friends:
        p = profiles_by_id.get(f["profile_id"])
        if not p:
            continue
        days, _turning = _next_annual_occurrence(f["friend_birthday"], today)
        if days is not None and days <= horizon_days:
            events.append({
                "type": "friend_birthday",
                "record_id": f["id"],
                "profile_name": p["name"],
                "profile_id": p["id"],
                "profile_type": p["profile_type"],
                "detail": f["friend_name"],
                "days_until": days,
                "due_date": None,
            })

    for b in all_baths:
        p = profiles_by_id.get(b["profile_id"])
        if not p:
            continue
        try:
            due = datetime.strptime(b["next_due_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (due - today).days
        if days <= horizon_days:
            events.append({
                "type": "bath",
                "record_id": b["id"],
                "profile_name": p["name"],
                "profile_id": p["id"],
                "profile_type": p["profile_type"],
                "detail": "bath",
                "days_until": days,
                "due_date": b["next_due_date"],
            })

    for fr in all_food_refills:
        p = profiles_by_id.get(fr["profile_id"])
        if not p:
            continue
        try:
            due = datetime.strptime(fr["next_refill_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (due - today).days
        if days <= horizon_days:
            events.append({
                "type": "food_refill",
                "record_id": fr["id"],
                "profile_name": p["name"],
                "profile_id": p["id"],
                "profile_type": p["profile_type"],
                "detail": fr["food_type"] or "food",
                "days_until": days,
                "due_date": fr["next_refill_date"],
            })

    for bs in all_boarding_stays:
        p = profiles_by_id.get(bs["profile_id"])
        if not p:
            continue
        try:
            check_in = datetime.strptime(bs["check_in_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (check_in - today).days
        if 0 <= days <= horizon_days:
            events.append({
                "type": "boarding_checkin",
                "record_id": bs["id"],
                "profile_name": p["name"],
                "profile_id": p["id"],
                "profile_type": p["profile_type"],
                "detail": bs["facility_name"] or "boarding",
                "days_until": days,
                "due_date": bs["check_in_date"],
            })

    # Registration and own-birthday are already fields on the profile itself -- no extra
    # query needed, just a pass over the (already-fetched) profile list.
    for p in profiles:
        if p["reg_next_due"]:
            try:
                due = datetime.strptime(p["reg_next_due"], "%Y-%m-%d").date()
                days = (due - today).days
                if days <= horizon_days:
                    events.append({
                        "type": "registration",
                        "record_id": p["id"],
                        "profile_name": p["name"],
                        "profile_id": p["id"],
                        "profile_type": p["profile_type"],
                        "detail": p["reg_id"] or "registration",
                        "days_until": days,
                        "due_date": p["reg_next_due"],
                    })
            except ValueError:
                pass

        if p["dob"]:
            days, turning = _next_annual_occurrence(p["dob"], today)
            if days is not None and days <= horizon_days:
                events.append({
                    "type": "own_birthday",
                    "record_id": p["id"],
                    "profile_name": p["name"],
                    "profile_id": p["id"],
                    "profile_type": p["profile_type"],
                    "detail": p["name"],
                    "days_until": days,
                    "due_date": None,
                    "turning": turning,
                })

    events.sort(key=lambda e: e["days_until"])
    return events


# ---------- Email digest notifications ----------

def get_already_notified_keys():
    """Set of (event_type, record_id, state_key, milestone) already included in a
    previously-sent digest. state_key/milestone computation lives in notifications.py, not
    here — this is plain storage, no domain logic about what counts as "the same" due item
    or which countdown checkpoint it's at."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT event_type, record_id, state_key, milestone FROM notified_events"
        ).fetchall()
        return {(r["event_type"], r["record_id"], r["state_key"], r["milestone"]) for r in rows}


def mark_events_notified(keys):
    """keys: iterable of (event_type, record_id, state_key, milestone) tuples just included
    in a digest that sent successfully (or, since the dashboard's "mute" button reuses this
    same function, all included at once to pre-empt every remaining checkpoint). Safe to call
    with a combo that's already marked -- ON CONFLICT DO NOTHING makes this idempotent rather
    than an error. (Postgres aborts the whole transaction on an uncaught constraint violation,
    unlike sqlite3, so this can't rely on a per-row try/except the way the old version did.)"""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        for event_type, record_id, state_key, milestone in keys:
            conn.execute(
                """INSERT INTO notified_events (event_type, record_id, state_key, milestone, notified_at)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (event_type, record_id, state_key, milestone) DO NOTHING""",
                (event_type, record_id, state_key, milestone, now)
            )


def was_digest_sent_today():
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM notification_log WHERE sent_at LIKE %s", (f"{today}%",)
        ).fetchone()
        return row["c"] > 0


def record_digest_sent():
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notification_log (sent_at) VALUES (%s)", (datetime.now().isoformat(),)
        )
