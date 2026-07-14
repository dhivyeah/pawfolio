"""SQLite data access layer for Pawfolio. No ORM, just sqlite3."""
import sqlite3
import os
from datetime import date, datetime, timedelta
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pawfolio.db")
PHOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")

os.makedirs(PHOTOS_DIR, exist_ok=True)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_column(conn, table: str, column: str, column_def: str):
    """Additive migration helper: add a column to an existing table if it isn't there yet."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vaccinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                vaccine_name TEXT NOT NULL,
                date_given TEXT,
                next_due_date TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                med_name TEXT NOT NULL,
                dosage TEXT,
                frequency TEXT,
                start_date TEXT,
                end_date TEXT,
                ongoing INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS friends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                friend_name TEXT NOT NULL,
                friend_birthday TEXT,
                notes TEXT
            )
        """)
        # A friend can either be freeform (friend_name/friend_birthday typed in directly) or
        # a link to another real profile already in Pawfolio — friend_profile_id set, name/
        # birthday looked up live from that profile instead so it can't go stale.
        _ensure_column(conn, "friends", "friend_profile_id", "INTEGER REFERENCES profiles(id) ON DELETE CASCADE")

        # ---- Additive migration: expand Health group on the existing profiles table ----
        _ensure_column(conn, "profiles", "spay_neuter_status", "TEXT DEFAULT 'unknown'")
        _ensure_column(conn, "profiles", "spay_neuter_date", "TEXT")
        _ensure_column(conn, "profiles", "nickname", "TEXT")
        _ensure_column(conn, "profiles", "other_notes", "TEXT")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS surgeries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                surgery_name TEXT NOT NULL,
                surgery_date TEXT,
                notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vet_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                visit_date TEXT,
                reason TEXT,
                notes TEXT
            )
        """)

        # ---- New: shared vet directory, reusable across profiles ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vet_name TEXT NOT NULL,
                clinic_name TEXT,
                phone TEXT,
                address TEXT,
                notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile_vets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                vet_id INTEGER NOT NULL REFERENCES vets(id) ON DELETE CASCADE,
                is_primary INTEGER DEFAULT 0
            )
        """)
        # Belt-and-suspenders against the same vet being linked to the same profile twice
        # (the application-level guard is in link_vet_to_profile). Wrapped defensively in
        # case a pre-existing database somehow already has duplicate rows.
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_profile_vets_unique ON profile_vets(profile_id, vet_id)"
            )
        except sqlite3.Error:
            pass

        # ---- New: sibling links between two profiles (symmetric, stored once per pair) ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS siblings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id_a INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                profile_id_b INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                UNIQUE(profile_id_a, profile_id_b)
            )
        """)

        # ---- New: Care & Logistics group ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS baths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                bath_date TEXT,
                next_due_date TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS food_refills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                food_type TEXT,
                last_refill_date TEXT,
                next_refill_date TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS boarding_stays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                facility_name TEXT,
                check_in_date TEXT,
                check_out_date TEXT,
                notes TEXT
            )
        """)


# ---------- Profiles ----------

def create_profile(data: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO profiles (
                name, nickname, photo_path, dob, dob_estimated, breed, profile_type, date_added,
                hangout_location, reg_id, reg_last_renewed, reg_next_due,
                likes, dislikes, favorite_toys, favorite_foods, foods_to_avoid, favorite_games,
                spay_neuter_status, spay_neuter_date, other_notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
        return cur.lastrowid


def update_profile(profile_id: int, data: dict):
    fields = [
        "name", "nickname", "photo_path", "dob", "dob_estimated", "breed", "profile_type",
        "hangout_location", "reg_id", "reg_last_renewed", "reg_next_due",
        "likes", "dislikes", "favorite_toys", "favorite_foods", "foods_to_avoid", "favorite_games",
        "spay_neuter_status", "spay_neuter_date", "other_notes"
    ]
    set_clause = ", ".join(f"{f} = ?" for f in fields)
    values = [data.get(f) for f in fields]
    values.append(profile_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE profiles SET {set_clause} WHERE id = ?", values)


def delete_profile(profile_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))


def get_profile(profile_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return dict(row) if row else None


def get_all_profiles(profile_type: str = None):
    with get_conn() as conn:
        if profile_type:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE profile_type = ? ORDER BY name COLLATE NOCASE",
                (profile_type,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM profiles ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]


def get_recently_added_profiles(days: int = 7):
    """Profiles added within the last `days` days, most recent first."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM profiles WHERE date_added >= ? ORDER BY date_added DESC, id DESC",
            (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Vaccinations ----------

def add_vaccination(profile_id, vaccine_name, date_given, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO vaccinations (profile_id, vaccine_name, date_given, next_due_date) VALUES (?,?,?,?)",
            (profile_id, vaccine_name, date_given, next_due_date)
        )


def get_vaccinations(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM vaccinations WHERE profile_id = ? ORDER BY next_due_date IS NULL, next_due_date",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_vaccination(vacc_id, vaccine_name, date_given, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vaccinations SET vaccine_name=?, date_given=?, next_due_date=? WHERE id=?",
            (vaccine_name, date_given, next_due_date, vacc_id)
        )


def delete_vaccination(vacc_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM vaccinations WHERE id = ?", (vacc_id,))


# ---------- Medications ----------

def add_medication(profile_id, med_name, dosage, frequency, start_date, end_date, ongoing):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO medications (profile_id, med_name, dosage, frequency, start_date, end_date, ongoing)
               VALUES (?,?,?,?,?,?,?)""",
            (profile_id, med_name, dosage, frequency, start_date, end_date, int(ongoing))
        )


def get_medications(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM medications WHERE profile_id = ? ORDER BY ongoing DESC, end_date",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_medication(med_id, med_name, dosage, frequency, start_date, end_date, ongoing):
    with get_conn() as conn:
        conn.execute(
            """UPDATE medications SET med_name=?, dosage=?, frequency=?, start_date=?, end_date=?, ongoing=?
               WHERE id=?""",
            (med_name, dosage, frequency, start_date, end_date, int(ongoing), med_id)
        )


def delete_medication(med_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM medications WHERE id = ?", (med_id,))


# ---------- Friends ----------

def add_friend(profile_id, friend_name, friend_birthday, notes, friend_profile_id=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO friends (profile_id, friend_name, friend_birthday, notes, friend_profile_id)
               VALUES (?,?,?,?,?)""",
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
            WHERE f.profile_id = ?
            ORDER BY COALESCE(p.name, f.friend_name) COLLATE NOCASE
        """, (profile_id,)).fetchall()
        return [dict(r) for r in rows]


def update_friend(friend_id, friend_name, friend_birthday, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE friends SET friend_name=?, friend_birthday=?, notes=? WHERE id=?",
            (friend_name, friend_birthday, notes, friend_id)
        )


def delete_friend(friend_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM friends WHERE id = ?", (friend_id,))


# ---------- Siblings ----------
# Symmetric relationship between two profiles, stored once per pair with the lower id
# always in profile_id_a so (A, B) and (B, A) can't both be inserted as separate rows.

def add_sibling(profile_id, other_profile_id):
    a, b = sorted((profile_id, other_profile_id))
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM siblings WHERE profile_id_a = ? AND profile_id_b = ?", (a, b)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO siblings (profile_id_a, profile_id_b) VALUES (?, ?)", (a, b)
        )
        return cur.lastrowid


def get_siblings(profile_id):
    """Sibling profiles linked to this one, joined with their current name/photo."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.id AS link_id, p.id AS sibling_id, p.name AS sibling_name,
                   p.photo_path AS sibling_photo_path
            FROM siblings s
            JOIN profiles p ON p.id = CASE WHEN s.profile_id_a = ? THEN s.profile_id_b ELSE s.profile_id_a END
            WHERE s.profile_id_a = ? OR s.profile_id_b = ?
            ORDER BY p.name COLLATE NOCASE
        """, (profile_id, profile_id, profile_id)).fetchall()
        return [dict(r) for r in rows]


def remove_sibling(link_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM siblings WHERE id = ?", (link_id,))


def count_incoming_links(profile_id):
    """How many *other* profiles reference this one as a linked friend, plus how many
    sibling links it has. Both cascade-delete silently (ON DELETE CASCADE) if this
    profile is deleted — used to warn about that before it happens, since it's not
    obvious from this profile's own page that deleting it also edits other profiles."""
    with get_conn() as conn:
        friend_refs = conn.execute(
            "SELECT COUNT(*) AS c FROM friends WHERE friend_profile_id = ?", (profile_id,)
        ).fetchone()["c"]
    sibling_refs = len(get_siblings(profile_id))
    return friend_refs, sibling_refs


# ---------- Surgeries ----------

def add_surgery(profile_id, surgery_name, surgery_date, notes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO surgeries (profile_id, surgery_name, surgery_date, notes) VALUES (?,?,?,?)",
            (profile_id, surgery_name, surgery_date, notes)
        )


def get_surgeries(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM surgeries WHERE profile_id = ? ORDER BY surgery_date IS NULL, surgery_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_surgery(surgery_id, surgery_name, surgery_date, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE surgeries SET surgery_name=?, surgery_date=?, notes=? WHERE id=?",
            (surgery_name, surgery_date, notes, surgery_id)
        )


def delete_surgery(surgery_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM surgeries WHERE id = ?", (surgery_id,))


# ---------- Vet visits (history) ----------

def add_vet_visit(profile_id, visit_date, reason, notes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO vet_visits (profile_id, visit_date, reason, notes) VALUES (?,?,?,?)",
            (profile_id, visit_date, reason, notes)
        )


def get_vet_visits(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM vet_visits WHERE profile_id = ? ORDER BY visit_date IS NULL, visit_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_vet_visit(visit_id, visit_date, reason, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vet_visits SET visit_date=?, reason=?, notes=? WHERE id=?",
            (visit_date, reason, notes, visit_id)
        )


def delete_vet_visit(visit_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM vet_visits WHERE id = ?", (visit_id,))


# ---------- Vets (shared directory) ----------

def create_vet(vet_name, clinic_name, phone, address, notes):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO vets (vet_name, clinic_name, phone, address, notes) VALUES (?,?,?,?,?)",
            (vet_name, clinic_name, phone, address, notes)
        )
        return cur.lastrowid


def get_all_vets():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM vets ORDER BY vet_name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]


def get_vet(vet_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM vets WHERE id = ?", (vet_id,)).fetchone()
        return dict(row) if row else None


def update_vet(vet_id, vet_name, clinic_name, phone, address, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE vets SET vet_name=?, clinic_name=?, phone=?, address=?, notes=? WHERE id=?",
            (vet_name, clinic_name, phone, address, notes, vet_id)
        )


def delete_vet(vet_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM vets WHERE id = ?", (vet_id,))


def link_vet_to_profile(profile_id, vet_id, is_primary=False):
    """Links a vet to a profile. If this vet is already linked to this profile, promotes
    it to primary if requested instead of creating a duplicate link."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM profile_vets WHERE profile_id = ? AND vet_id = ?",
            (profile_id, vet_id)
        ).fetchone()
        if is_primary:
            conn.execute("UPDATE profile_vets SET is_primary = 0 WHERE profile_id = ?", (profile_id,))
        if existing:
            if is_primary:
                conn.execute("UPDATE profile_vets SET is_primary = 1 WHERE id = ?", (existing["id"],))
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO profile_vets (profile_id, vet_id, is_primary) VALUES (?,?,?)",
            (profile_id, vet_id, int(is_primary))
        )
        return cur.lastrowid


def unlink_vet_from_profile(profile_vet_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM profile_vets WHERE id = ?", (profile_vet_id,))


def set_primary_vet(profile_id, profile_vet_id):
    with get_conn() as conn:
        conn.execute("UPDATE profile_vets SET is_primary = 0 WHERE profile_id = ?", (profile_id,))
        conn.execute("UPDATE profile_vets SET is_primary = 1 WHERE id = ?", (profile_vet_id,))


def get_vets_for_profile(profile_id):
    """Vets linked to this profile, joined with vet details. Primary vet first."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT profile_vets.id AS link_id, profile_vets.is_primary AS is_primary,
                   vets.id AS vet_id, vets.vet_name, vets.clinic_name, vets.phone,
                   vets.address, vets.notes
            FROM profile_vets
            JOIN vets ON vets.id = profile_vets.vet_id
            WHERE profile_vets.profile_id = ?
            ORDER BY profile_vets.is_primary DESC, vets.vet_name COLLATE NOCASE
        """, (profile_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------- Baths ----------

def add_bath(profile_id, bath_date, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO baths (profile_id, bath_date, next_due_date) VALUES (?,?,?)",
            (profile_id, bath_date, next_due_date)
        )


def get_baths(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM baths WHERE profile_id = ? ORDER BY next_due_date IS NULL, next_due_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_bath(bath_id, bath_date, next_due_date):
    with get_conn() as conn:
        conn.execute(
            "UPDATE baths SET bath_date=?, next_due_date=? WHERE id=?",
            (bath_date, next_due_date, bath_id)
        )


def delete_bath(bath_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM baths WHERE id = ?", (bath_id,))


# ---------- Food refills ----------

def add_food_refill(profile_id, food_type, last_refill_date, next_refill_date):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO food_refills (profile_id, food_type, last_refill_date, next_refill_date) VALUES (?,?,?,?)",
            (profile_id, food_type, last_refill_date, next_refill_date)
        )


def get_food_refills(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM food_refills WHERE profile_id = ? ORDER BY next_refill_date IS NULL, next_refill_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_food_refill(refill_id, food_type, last_refill_date, next_refill_date):
    with get_conn() as conn:
        conn.execute(
            "UPDATE food_refills SET food_type=?, last_refill_date=?, next_refill_date=? WHERE id=?",
            (food_type, last_refill_date, next_refill_date, refill_id)
        )


def delete_food_refill(refill_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM food_refills WHERE id = ?", (refill_id,))


# ---------- Boarding stays (history) ----------

def add_boarding_stay(profile_id, facility_name, check_in_date, check_out_date, notes):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO boarding_stays (profile_id, facility_name, check_in_date, check_out_date, notes)
               VALUES (?,?,?,?,?)""",
            (profile_id, facility_name, check_in_date, check_out_date, notes)
        )


def get_boarding_stays(profile_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM boarding_stays WHERE profile_id = ? ORDER BY check_in_date IS NULL, check_in_date DESC",
            (profile_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_boarding_stay(stay_id, facility_name, check_in_date, check_out_date, notes):
    with get_conn() as conn:
        conn.execute(
            """UPDATE boarding_stays SET facility_name=?, check_in_date=?, check_out_date=?, notes=?
               WHERE id=?""",
            (facility_name, check_in_date, check_out_date, notes, stay_id)
        )


def delete_boarding_stay(stay_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM boarding_stays WHERE id = ?", (stay_id,))


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
    """Gather all upcoming/overdue events across every profile, sorted soonest/most overdue first."""
    events = []
    today = date.today()
    profiles = get_all_profiles()

    for p in profiles:
        pid = p["id"]
        pname = p["name"]

        for v in get_vaccinations(pid):
            if not v["next_due_date"]:
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
                    "profile_name": pname,
                    "profile_id": pid,
                    "profile_type": p["profile_type"],
                    "detail": v["vaccine_name"],
                    "days_until": days,
                    "due_date": v["next_due_date"],
                })

        for m in get_medications(pid):
            if m["ongoing"] or not m["end_date"]:
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
                    "profile_name": pname,
                    "profile_id": pid,
                    "profile_type": p["profile_type"],
                    "detail": m["med_name"],
                    "days_until": days,
                    "due_date": m["end_date"],
                })

        if p["reg_next_due"]:
            try:
                due = datetime.strptime(p["reg_next_due"], "%Y-%m-%d").date()
                days = (due - today).days
                if days <= horizon_days:
                    events.append({
                        "type": "registration",
                        "record_id": pid,
                        "profile_name": pname,
                        "profile_id": pid,
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
                    "record_id": pid,
                    "profile_name": pname,
                    "profile_id": pid,
                    "profile_type": p["profile_type"],
                    "detail": pname,
                    "days_until": days,
                    "due_date": None,
                    "turning": turning,
                })

        for f in get_friends(pid):
            if f["friend_profile_id"]:
                continue  # they already get their own "own_birthday" event on their own profile
            if not f["friend_birthday"]:
                continue
            days, _turning = _next_annual_occurrence(f["friend_birthday"], today)
            if days is not None and days <= horizon_days:
                events.append({
                    "type": "friend_birthday",
                    "record_id": f["id"],
                    "profile_name": pname,
                    "profile_id": pid,
                    "profile_type": p["profile_type"],
                    "detail": f["friend_name"],
                    "days_until": days,
                    "due_date": None,
                })

        for b in get_baths(pid):
            if not b["next_due_date"]:
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
                    "profile_name": pname,
                    "profile_id": pid,
                    "profile_type": p["profile_type"],
                    "detail": "bath",
                    "days_until": days,
                    "due_date": b["next_due_date"],
                })

        for fr in get_food_refills(pid):
            if not fr["next_refill_date"]:
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
                    "profile_name": pname,
                    "profile_id": pid,
                    "profile_type": p["profile_type"],
                    "detail": fr["food_type"] or "food",
                    "days_until": days,
                    "due_date": fr["next_refill_date"],
                })

        for bs in get_boarding_stays(pid):
            if not bs["check_in_date"]:
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
                    "profile_name": pname,
                    "profile_id": pid,
                    "profile_type": p["profile_type"],
                    "detail": bs["facility_name"] or "boarding",
                    "days_until": days,
                    "due_date": bs["check_in_date"],
                })

    events.sort(key=lambda e: e["days_until"])
    return events
