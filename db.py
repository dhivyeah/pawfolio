"""Postgres data access layer for Pawfolio (hosted on Supabase), via psycopg2. No ORM.

Was SQLite; migrated to hosted Postgres so the app can run on Streamlit Community Cloud
without a local file for storage. See migrate_to_postgres.py for the one-time data move
from an existing local pawfolio.db, and README/KNOWN_ISSUES for the deployment notes.

Phase 4: every profile/vet is owned by a Supabase Auth user (owner_id, a UUID from
auth.users). Every function that touches profile- or vet-scoped data takes owner_id and
filters by it -- either directly (profiles, vets, notification_log all have their own
owner_id column) or via a JOIN back through profiles/vets for the child tables
(vaccinations, medications, friends, etc.), which deliberately do NOT get their own
owner_id column -- ownership lives in exactly one place per record type, so a child row
can never drift out of sync with who actually owns its parent.
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

        # ---- Phase 4: per-user ownership. Nullable at the DB level -- existing rows have
        # no owner until the one-time migration backfills them (see migrate_add_owner.py) --
        # but every function below always requires and filters by owner_id regardless, so
        # enforcement lives at the application layer rather than a NOT NULL constraint that
        # would make the additive migration a two-step dance for no real benefit at this scale.
        # Deliberately not a foreign key into auth.users(id): that table is Supabase's own
        # (lives in the `auth` schema, not this app's), and a hard FK into it would mean
        # every test run needs a real Supabase Auth user to exist first just to satisfy the
        # constraint -- a plain UUID column keeps ownership correctness an application-layer
        # guarantee (every write path already requires a real owner_id from a logged-in
        # session) rather than tying schema setup to Supabase's own internal table.
        _ensure_column_sql("profiles", "owner_id", "UUID"),

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

        # ---- Vet directory. Was shared across all profiles; Phase 4 makes it per-owner
        # instead (own_id column) since "no shared/public visibility yet" applies to vets
        # too -- one user's vet list (names, phone numbers) shouldn't be visible to another.
        """CREATE TABLE IF NOT EXISTS vets (
            id SERIAL PRIMARY KEY,
            vet_name TEXT NOT NULL,
            clinic_name TEXT,
            phone TEXT,
            address TEXT,
            notes TEXT
        );""",
        _ensure_column_sql("vets", "owner_id", "UUID"),
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
        # the whole countdown starts fresh. No owner_id column needed here -- record_id is a
        # globally unique SERIAL id from its own table, so two different users' events can
        # never collide on the same dedup key even without an explicit owner filter.
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
        # Phase 4: gained an owner_id column so the once-a-day cap applies per user, not
        # globally -- otherwise one user's digest would suppress every other user's for the
        # rest of that day.
        """CREATE TABLE IF NOT EXISTS notification_log (
            id SERIAL PRIMARY KEY,
            sent_at TEXT NOT NULL
        );""",
        _ensure_column_sql("notification_log", "owner_id", "UUID"),

        # ---- Photo storage (Supabase Storage, "photos" bucket, private) ----
        # RLS policies scoping storage.objects so a signed-in user can only
        # read/write/delete objects under their own {auth.uid()}/... folder -- see
        # photo_storage.py, which uploads to exactly that path and authenticates each
        # call as the current user (not the shared anon key alone) so these policies
        # actually apply. storage.foldername() is a Supabase-provided helper that splits
        # an object path on "/" into an array; [1] is the first segment, i.e. the
        # owner-id folder a photo lives under. Global to the bucket, not per-schema, so
        # re-asserting them on every init_db() call (including test runs against a
        # throwaway schema) is harmless -- DROP+CREATE makes each one idempotent.
        """DROP POLICY IF EXISTS "Users manage own photos - select" ON storage.objects;""",
        """CREATE POLICY "Users manage own photos - select" ON storage.objects
           FOR SELECT TO authenticated
           USING (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);""",
        """DROP POLICY IF EXISTS "Users manage own photos - insert" ON storage.objects;""",
        """CREATE POLICY "Users manage own photos - insert" ON storage.objects
           FOR INSERT TO authenticated
           WITH CHECK (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);""",
        """DROP POLICY IF EXISTS "Users manage own photos - update" ON storage.objects;""",
        """CREATE POLICY "Users manage own photos - update" ON storage.objects
           FOR UPDATE TO authenticated
           USING (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);""",
        """DROP POLICY IF EXISTS "Users manage own photos - delete" ON storage.objects;""",
        """CREATE POLICY "Users manage own photos - delete" ON storage.objects
           FOR DELETE TO authenticated
           USING (bucket_id = 'photos' AND (storage.foldername(name))[1] = auth.uid()::text);""",
    ]
    with get_conn() as conn:
        conn.execute("\n".join(statements))


# ---------- Profiles ----------

def create_profile(data: dict, owner_id: str) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO profiles (
                name, nickname, photo_path, dob, dob_estimated, breed, profile_type, date_added,
                hangout_location, reg_id, reg_last_renewed, reg_next_due,
                likes, dislikes, favorite_toys, favorite_foods, foods_to_avoid, favorite_games,
                spay_neuter_status, spay_neuter_date, other_notes, owner_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            data.get("name"), data.get("nickname"), data.get("photo_path"), data.get("dob"),
            int(data.get("dob_estimated", 0)), data.get("breed"), data.get("profile_type"),
            data.get("date_added", date.today().isoformat()), data.get("hangout_location"),
            data.get("reg_id"), data.get("reg_last_renewed"), data.get("reg_next_due"),
            data.get("likes"), data.get("dislikes"), data.get("favorite_toys"),
            data.get("favorite_foods"), data.get("foods_to_avoid"), data.get("favorite_games"),
            data.get("spay_neuter_status", "unknown"), data.get("spay_neuter_date"),
            data.get("other_notes"), owner_id,
        ))
        return cur.fetchone()["id"]


def update_profile(profile_id: int, data: dict, owner_id: str):
    fields = [
        "name", "nickname", "photo_path", "dob", "dob_estimated", "breed", "profile_type",
        "hangout_location", "reg_id", "reg_last_renewed", "reg_next_due",
        "likes", "dislikes", "favorite_toys", "favorite_foods", "foods_to_avoid", "favorite_games",
        "spay_neuter_status", "spay_neuter_date", "other_notes"
    ]
    set_clause = ", ".join(f"{f} = %s" for f in fields)
    values = [data.get(f) for f in fields]
    values[fields.index("dob_estimated")] = int(data.get("dob_estimated", 0))
    values.extend([profile_id, owner_id])
    with get_conn() as conn:
        conn.execute(f"UPDATE profiles SET {set_clause} WHERE id = %s AND owner_id = %s", values)


def delete_profile(profile_id: int, owner_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM profiles WHERE id = %s AND owner_id = %s", (profile_id, owner_id))


def get_profile(profile_id: int, owner_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE id = %s AND owner_id = %s", (profile_id, owner_id)
        ).fetchone()
        return dict(row) if row else None


def get_all_profiles(owner_id: str, profile_type: str = None):
    with get_conn() as conn:
        if profile_type:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE owner_id = %s AND profile_type = %s ORDER BY LOWER(name)",
                (owner_id, profile_type)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE owner_id = %s ORDER BY LOWER(name)", (owner_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_recently_added_profiles(owner_id: str, days: int = 7):
    """Profiles added within the last `days` days, most recent first."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM profiles WHERE owner_id = %s AND date_added >= %s ORDER BY date_added DESC, id DESC",
            (owner_id, cutoff)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Vaccinations ----------

def add_vaccination(profile_id, vaccine_name, date_given, next_due_date, owner_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO vaccinations (profile_id, vaccine_name, date_given, next_due_date)
               SELECT %s, %s, %s, %s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, vaccine_name, date_given, next_due_date, profile_id, owner_id)
        )


def get_vaccinations(profile_id, owner_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.* FROM vaccinations v JOIN profiles p ON p.id = v.profile_id
            WHERE v.profile_id = %s AND p.owner_id = %s
            ORDER BY v.next_due_date IS NULL, v.next_due_date
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_vaccination(vacc_id, vaccine_name, date_given, next_due_date, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE vaccinations SET vaccine_name=%s, date_given=%s, next_due_date=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (vaccine_name, date_given, next_due_date, vacc_id, owner_id))


def delete_vaccination(vacc_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM vaccinations WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (vacc_id, owner_id))


# ---------- Medications ----------

def add_medication(profile_id, med_name, dosage, frequency, start_date, end_date, ongoing, owner_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO medications (profile_id, med_name, dosage, frequency, start_date, end_date, ongoing)
               SELECT %s,%s,%s,%s,%s,%s,%s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, med_name, dosage, frequency, start_date, end_date, int(ongoing), profile_id, owner_id)
        )


def get_medications(profile_id, owner_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT m.* FROM medications m JOIN profiles p ON p.id = m.profile_id
            WHERE m.profile_id = %s AND p.owner_id = %s
            ORDER BY m.ongoing DESC, m.end_date
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_medication(med_id, med_name, dosage, frequency, start_date, end_date, ongoing, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE medications SET med_name=%s, dosage=%s, frequency=%s, start_date=%s, end_date=%s, ongoing=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (med_name, dosage, frequency, start_date, end_date, int(ongoing), med_id, owner_id))


def delete_medication(med_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM medications WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (med_id, owner_id))


# ---------- Friends ----------

def add_friend(profile_id, friend_name, friend_birthday, notes, owner_id, friend_profile_id=None):
    with get_conn() as conn:
        # A linked friend (friend_profile_id set) must belong to the same owner as
        # profile_id -- checked explicitly rather than trusted, same as add_sibling's
        # owned_count check and link_vet_to_profile's owns_profile/owns_vet checks. The UI
        # only ever offers same-owner candidates for this picker, but this function's own
        # contract shouldn't depend on that staying true forever.
        if friend_profile_id is not None:
            owns_friend_profile = conn.execute(
                "SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s",
                (friend_profile_id, owner_id)
            ).fetchone()
            if not owns_friend_profile:
                raise PawfolioDBError("Couldn't link that profile as a friend.")
        conn.execute(
            """INSERT INTO friends (profile_id, friend_name, friend_birthday, notes, friend_profile_id)
               SELECT %s,%s,%s,%s,%s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, friend_name, friend_birthday, notes, friend_profile_id, profile_id, owner_id)
        )


def get_friends(profile_id, owner_id):
    """Friends for a profile. A friend may be freeform (friend_name/friend_birthday typed in
    directly) or a link to another real profile (friend_profile_id set) — for linked friends,
    linked_name/linked_photo_path/linked_dob come live from that profile so they can't go
    stale if the other profile's own name or photo changes later."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT f.*, lp.name AS linked_name, lp.photo_path AS linked_photo_path, lp.dob AS linked_dob
            FROM friends f
            JOIN profiles p ON p.id = f.profile_id
            LEFT JOIN profiles lp ON lp.id = f.friend_profile_id AND lp.owner_id = p.owner_id
            WHERE f.profile_id = %s AND p.owner_id = %s
            ORDER BY LOWER(COALESCE(lp.name, f.friend_name))
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_friend(friend_id, friend_name, friend_birthday, notes, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE friends SET friend_name=%s, friend_birthday=%s, notes=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (friend_name, friend_birthday, notes, friend_id, owner_id))


def delete_friend(friend_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM friends WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (friend_id, owner_id))


# ---------- Siblings ----------
# Symmetric relationship between two profiles, stored once per pair with the lower id
# always in profile_id_a so (A, B) and (B, A) can't both be inserted as separate rows.

def add_sibling(profile_id, other_profile_id, owner_id):
    a, b = sorted((profile_id, other_profile_id))
    with get_conn() as conn:
        # Both sides must belong to the same owner -- a sibling link is only ever offered
        # between two of the *same* user's own dogs (see views/profile_detail.py's picker,
        # which only lists candidates from that user's own get_all_profiles()), but this is
        # verified again here rather than trusted, same as every other write in this file.
        owned_count = conn.execute(
            "SELECT COUNT(*) AS c FROM profiles WHERE id IN (%s, %s) AND owner_id = %s",
            (a, b, owner_id)
        ).fetchone()["c"]
        if owned_count != 2:
            raise PawfolioDBError("Couldn't link those two profiles.")
        existing = conn.execute(
            "SELECT id FROM siblings WHERE profile_id_a = %s AND profile_id_b = %s", (a, b)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO siblings (profile_id_a, profile_id_b) VALUES (%s, %s) RETURNING id", (a, b)
        )
        return cur.fetchone()["id"]


def get_siblings(profile_id, owner_id):
    """Sibling profiles linked to this one, joined with their current name/photo."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.id AS link_id, p.id AS sibling_id, p.name AS sibling_name,
                   p.photo_path AS sibling_photo_path
            FROM siblings s
            JOIN profiles anchor ON anchor.id = %s AND anchor.owner_id = %s
            JOIN profiles p ON p.id = CASE WHEN s.profile_id_a = %s THEN s.profile_id_b ELSE s.profile_id_a END
            WHERE s.profile_id_a = %s OR s.profile_id_b = %s
            ORDER BY LOWER(p.name)
        """, (profile_id, owner_id, profile_id, profile_id, profile_id)).fetchall()
        return [dict(r) for r in rows]


def remove_sibling(link_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM siblings WHERE id = %s AND (
                profile_id_a IN (SELECT id FROM profiles WHERE owner_id=%s)
                OR profile_id_b IN (SELECT id FROM profiles WHERE owner_id=%s)
            )
        """, (link_id, owner_id, owner_id))


def count_incoming_links(profile_id, owner_id):
    """How many *other* profiles reference this one as a linked friend, plus how many
    sibling links it has. Both cascade-delete silently (ON DELETE CASCADE) if this
    profile is deleted — used to warn about that before it happens, since it's not
    obvious from this profile's own page that deleting it also edits other profiles."""
    with get_conn() as conn:
        friend_refs = conn.execute("""
            SELECT COUNT(*) AS c FROM friends f JOIN profiles p ON p.id = f.profile_id
            WHERE f.friend_profile_id = %s AND p.owner_id = %s
        """, (profile_id, owner_id)).fetchone()["c"]
    sibling_refs = len(get_siblings(profile_id, owner_id))
    return friend_refs, sibling_refs


# ---------- Surgeries ----------

def add_surgery(profile_id, surgery_name, surgery_date, notes, owner_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO surgeries (profile_id, surgery_name, surgery_date, notes)
               SELECT %s,%s,%s,%s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, surgery_name, surgery_date, notes, profile_id, owner_id)
        )


def get_surgeries(profile_id, owner_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.* FROM surgeries s JOIN profiles p ON p.id = s.profile_id
            WHERE s.profile_id = %s AND p.owner_id = %s
            ORDER BY s.surgery_date IS NULL, s.surgery_date DESC
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_surgery(surgery_id, surgery_name, surgery_date, notes, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE surgeries SET surgery_name=%s, surgery_date=%s, notes=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (surgery_name, surgery_date, notes, surgery_id, owner_id))


def delete_surgery(surgery_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM surgeries WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (surgery_id, owner_id))


# ---------- Vet visits (history) ----------

def add_vet_visit(profile_id, visit_date, reason, notes, owner_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO vet_visits (profile_id, visit_date, reason, notes)
               SELECT %s,%s,%s,%s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, visit_date, reason, notes, profile_id, owner_id)
        )


def get_vet_visits(profile_id, owner_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT vv.* FROM vet_visits vv JOIN profiles p ON p.id = vv.profile_id
            WHERE vv.profile_id = %s AND p.owner_id = %s
            ORDER BY vv.visit_date IS NULL, vv.visit_date DESC
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_vet_visit(visit_id, visit_date, reason, notes, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE vet_visits SET visit_date=%s, reason=%s, notes=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (visit_date, reason, notes, visit_id, owner_id))


def delete_vet_visit(visit_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM vet_visits WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (visit_id, owner_id))


# ---------- Vets (per-owner directory) ----------

def create_vet(vet_name, clinic_name, phone, address, notes, owner_id):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO vets (vet_name, clinic_name, phone, address, notes, owner_id) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (vet_name, clinic_name, phone, address, notes, owner_id)
        )
        return cur.fetchone()["id"]


def get_all_vets(owner_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM vets WHERE owner_id = %s ORDER BY LOWER(vet_name)", (owner_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_vet(vet_id, owner_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vets WHERE id = %s AND owner_id = %s", (vet_id, owner_id)
        ).fetchone()
        return dict(row) if row else None


def update_vet(vet_id, vet_name, clinic_name, phone, address, notes, owner_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vets SET vet_name=%s, clinic_name=%s, phone=%s, address=%s, notes=%s "
            "WHERE id=%s AND owner_id=%s",
            (vet_name, clinic_name, phone, address, notes, vet_id, owner_id)
        )


def delete_vet(vet_id, owner_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM vets WHERE id = %s AND owner_id = %s", (vet_id, owner_id))


def link_vet_to_profile(profile_id, vet_id, owner_id, is_primary=False):
    """Links a vet to a profile. If this vet is already linked to this profile, promotes
    it to primary if requested instead of creating a duplicate link. Both the profile and
    the vet must belong to the calling owner -- checked explicitly rather than trusted,
    even though the UI only ever offers same-owner candidates for both."""
    with get_conn() as conn:
        owns_profile = conn.execute(
            "SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s", (profile_id, owner_id)
        ).fetchone()
        owns_vet = conn.execute(
            "SELECT 1 FROM vets WHERE id = %s AND owner_id = %s", (vet_id, owner_id)
        ).fetchone()
        if not owns_profile or not owns_vet:
            raise PawfolioDBError("Couldn't link that vet.")
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


def unlink_vet_from_profile(profile_vet_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM profile_vets WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (profile_vet_id, owner_id))


def set_primary_vet(profile_id, profile_vet_id, owner_id):
    with get_conn() as conn:
        owns_profile = conn.execute(
            "SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s", (profile_id, owner_id)
        ).fetchone()
        if not owns_profile:
            raise PawfolioDBError("Couldn't update that vet link.")
        conn.execute("UPDATE profile_vets SET is_primary = 0 WHERE profile_id = %s", (profile_id,))
        conn.execute(
            "UPDATE profile_vets SET is_primary = 1 WHERE id = %s AND profile_id = %s",
            (profile_vet_id, profile_id)
        )


def get_vets_for_profile(profile_id, owner_id):
    """Vets linked to this profile, joined with vet details. Primary vet first."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT profile_vets.id AS link_id, profile_vets.is_primary AS is_primary,
                   vets.id AS vet_id, vets.vet_name, vets.clinic_name, vets.phone,
                   vets.address, vets.notes
            FROM profile_vets
            JOIN profiles p ON p.id = profile_vets.profile_id
            JOIN vets ON vets.id = profile_vets.vet_id
            WHERE profile_vets.profile_id = %s AND p.owner_id = %s
            ORDER BY profile_vets.is_primary DESC, LOWER(vets.vet_name)
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


# ---------- Baths ----------

def add_bath(profile_id, bath_date, next_due_date, owner_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO baths (profile_id, bath_date, next_due_date)
               SELECT %s,%s,%s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, bath_date, next_due_date, profile_id, owner_id)
        )


def get_baths(profile_id, owner_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT b.* FROM baths b JOIN profiles p ON p.id = b.profile_id
            WHERE b.profile_id = %s AND p.owner_id = %s
            ORDER BY b.next_due_date IS NULL, b.next_due_date DESC
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_bath(bath_id, bath_date, next_due_date, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE baths SET bath_date=%s, next_due_date=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (bath_date, next_due_date, bath_id, owner_id))


def delete_bath(bath_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM baths WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (bath_id, owner_id))


# ---------- Food refills ----------

def add_food_refill(profile_id, food_type, last_refill_date, next_refill_date, owner_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO food_refills (profile_id, food_type, last_refill_date, next_refill_date)
               SELECT %s,%s,%s,%s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, food_type, last_refill_date, next_refill_date, profile_id, owner_id)
        )


def get_food_refills(profile_id, owner_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT fr.* FROM food_refills fr JOIN profiles p ON p.id = fr.profile_id
            WHERE fr.profile_id = %s AND p.owner_id = %s
            ORDER BY fr.next_refill_date IS NULL, fr.next_refill_date DESC
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_food_refill(refill_id, food_type, last_refill_date, next_refill_date, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE food_refills SET food_type=%s, last_refill_date=%s, next_refill_date=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (food_type, last_refill_date, next_refill_date, refill_id, owner_id))


def delete_food_refill(refill_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM food_refills WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (refill_id, owner_id))


# ---------- Boarding stays (history) ----------

def add_boarding_stay(profile_id, facility_name, check_in_date, check_out_date, notes, owner_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO boarding_stays (profile_id, facility_name, check_in_date, check_out_date, notes)
               SELECT %s,%s,%s,%s,%s WHERE EXISTS (
                   SELECT 1 FROM profiles WHERE id = %s AND owner_id = %s
               )""",
            (profile_id, facility_name, check_in_date, check_out_date, notes, profile_id, owner_id)
        )


def get_boarding_stays(profile_id, owner_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT bs.* FROM boarding_stays bs JOIN profiles p ON p.id = bs.profile_id
            WHERE bs.profile_id = %s AND p.owner_id = %s
            ORDER BY bs.check_in_date IS NULL, bs.check_in_date DESC
        """, (profile_id, owner_id)).fetchall()
        return [dict(r) for r in rows]


def update_boarding_stay(stay_id, facility_name, check_in_date, check_out_date, notes, owner_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE boarding_stays SET facility_name=%s, check_in_date=%s, check_out_date=%s, notes=%s
            WHERE id=%s AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (facility_name, check_in_date, check_out_date, notes, stay_id, owner_id))


def delete_boarding_stay(stay_id, owner_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM boarding_stays WHERE id = %s
            AND profile_id IN (SELECT id FROM profiles WHERE owner_id=%s)
        """, (stay_id, owner_id))


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


def get_upcoming_events(owner_id: str, horizon_days: int = 30):
    """Gather all upcoming/overdue events across every one of this owner's profiles,
    sorted soonest/most overdue first.

    Fetches each record type once across all of this owner's profiles (6 queries total)
    rather than once per profile per type (6 x N queries) -- against local SQLite that
    distinction was free, but against hosted Postgres each query is a real network
    round-trip, so the old per-profile-per-type loop turned a 3-profile dashboard into ~19
    round-trips and a 20-profile one into ~120. Grouping happens in Python afterward via
    profiles_by_id instead of in the query, so every event's shape and the
    horizon/ongoing/linked-friend filtering rules below are unchanged from the per-profile
    version this replaced. The owner filter is applied at the SQL level (JOIN through
    profiles) on all six bulk queries, not just relied on implicitly via profiles_by_id
    only containing this owner's profiles -- keeps other owners' rows out of process
    memory entirely rather than fetching-then-discarding them."""
    events = []
    today = date.today()
    profiles = get_all_profiles(owner_id)
    profiles_by_id = {p["id"]: p for p in profiles}

    with get_conn() as conn:
        all_vaccinations = conn.execute("""
            SELECT v.* FROM vaccinations v JOIN profiles p ON p.id = v.profile_id
            WHERE v.next_due_date IS NOT NULL AND p.owner_id = %s
        """, (owner_id,)).fetchall()
        all_medications = conn.execute("""
            SELECT m.* FROM medications m JOIN profiles p ON p.id = m.profile_id
            WHERE m.ongoing = 0 AND m.end_date IS NOT NULL AND p.owner_id = %s
        """, (owner_id,)).fetchall()
        all_friends = conn.execute("""
            SELECT f.* FROM friends f JOIN profiles p ON p.id = f.profile_id
            WHERE f.friend_profile_id IS NULL AND f.friend_birthday IS NOT NULL AND p.owner_id = %s
        """, (owner_id,)).fetchall()
        all_baths = conn.execute("""
            SELECT b.* FROM baths b JOIN profiles p ON p.id = b.profile_id
            WHERE b.next_due_date IS NOT NULL AND p.owner_id = %s
        """, (owner_id,)).fetchall()
        all_food_refills = conn.execute("""
            SELECT fr.* FROM food_refills fr JOIN profiles p ON p.id = fr.profile_id
            WHERE fr.next_refill_date IS NOT NULL AND p.owner_id = %s
        """, (owner_id,)).fetchall()
        all_boarding_stays = conn.execute("""
            SELECT bs.* FROM boarding_stays bs JOIN profiles p ON p.id = bs.profile_id
            WHERE bs.check_in_date IS NOT NULL AND p.owner_id = %s
        """, (owner_id,)).fetchall()

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
    or which countdown checkpoint it's at. No owner_id needed: record_id is a globally
    unique id from its own source table, so two different owners' events can never
    collide on the same dedup key."""
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


def was_digest_sent_today(owner_id: str):
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM notification_log WHERE owner_id = %s AND sent_at LIKE %s",
            (owner_id, f"{today}%")
        ).fetchone()
        return row["c"] > 0


def record_digest_sent(owner_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notification_log (owner_id, sent_at) VALUES (%s, %s)",
            (owner_id, datetime.now().isoformat())
        )


# ---------- Users (for admin/migration use, e.g. one-time owner backfill) ----------

def list_auth_users():
    """Every Supabase Auth user's id/email, straight from the auth schema our direct
    Postgres connection already has access to. Not used by the app itself at runtime --
    only by one-time migration scripts (see migrate_add_owner.py) that need to find a
    user's id to backfill existing ownerless rows, without asking for a UUID to be
    copy-pasted by hand."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id, email, created_at FROM auth.users ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]
