# Pawfolio

A personal tracker for your dogs' lives — health, personality, and social info. Phase 1: single-user, local, no login.

## Setup

```
pip install -r requirements.txt
```

## Run

```
python -m streamlit run app.py
```

(If `streamlit` is on your PATH, the shorter `streamlit run app.py` works too. On Windows, pip sometimes installs the `streamlit` script somewhere not on PATH — `python -m streamlit` always works regardless.)

This opens the app in your browser (usually `http://localhost:8501`).

## Data storage

- **Database**: `pawfolio.db`, a SQLite file created automatically in the project root the first time you run the app.
- **Photos**: uploaded photos are saved to the `photos/` folder in the project root; the database stores the relative path to each file.

Both are local to this folder — nothing leaves your machine, and there's no login or multi-user separation in this phase.

## Pages

Navigation is two icon buttons at the top of the app, no sidebar, no text labels: **🏠 Home** and **🐾🐾 All the Pups**. Both are icon-only by design so labels never truncate on narrow screens.

- **Home** (`views/home.py`) — the dashboard. A puppy mascot and title up top with a **➕ New Profile** button (this is the only place "add a profile" lives — it's deliberately not in the persistent nav). Below that: a "🎉 New Pack Members" section for any dog added in the last 7 days, then the upcoming-events feed (vaccinations due, medications ending, Chennai Corporation registration renewals, birthdays), sorted soonest first. Empty state shows a bigger mascot instead of a blank page.
- **All the Pups** (`views/all_profiles.py`) — browse every dog (yours and community dogs) in a grid with uniform, center-cropped square thumbnails that fill their card at any screen size; click into any profile for details.
- **Profile Detail** (`views/profile_detail.py`) — full view of one dog's Identity, Health, Personality, Social, and **Care & Logistics** info, with inline edit and delete for every record. Not a nav item — only reached by clicking a dog from Home or All the Pups.
- **Add Profile form** (`views/add_profile.py`) — same form used by the Home page's New Profile button, extended with optional first entries for all the new fields below.

`app.py` is the router: it sets up `st.navigation` (sidebar hidden via `position="hidden"`), renders the top icon bar, injects the central theme from `styles.py`, and runs whichever page is active.

The app is responsive: Streamlit's columns stack vertically on narrow screens, and photos/thumbnails resize to fill their container rather than using fixed pixel dimensions.

## Health & Care & Logistics (added in this update)

The **Health** tab now also tracks: spay/neuter status (yes/no/unknown + date), a surgeries list, full vet visit history, and links to a shared **vet directory** (`vets` table) — the same vet/clinic can be linked from multiple dog profiles, with an inline "add a new vet" option right where you pick one, and a primary-vet flag.

A new **🧺 Care & Logistics** tab tracks bath history (with next-due dates, same pattern as vaccinations), food refill tracking, and full boarding stay history. Upcoming bath/refill due dates and future boarding check-ins feed into the same Home dashboard sorting-by-urgency logic as vaccinations/meds/registration/birthdays, in the same warm card style and tone.

All of this was added via an additive SQLite migration (`db.py: init_db()` / `_ensure_column`) — existing tables gain new columns via `ALTER TABLE`, new tables are created with `CREATE TABLE IF NOT EXISTS`, and no existing data is touched or reset.

## Visual theme

`styles.py` is the single place all custom CSS lives, injected once at startup. Warm & playful direction: cream background, soft pastel cards (peach/terracotta/sage/buttery yellow/dusty pink), rounded corners everywhere, circular photos in list/feed views and larger rounded-rect photos on the detail page. It's layered on top of Streamlit's existing layout via CSS only — no layout primitives were rebuilt.

## Notes

- Tag-style fields (likes, dislikes, favorite toys/foods, foods to avoid, favorite games) are stored as simple comma-separated text — no tag picker yet, that's a later phase.
- The dashboard is computed live from the database on every page load — no background jobs, no notifications.

## Tests

```
pip install -r requirements-dev.txt
python -m pytest tests/
```

Tests run against a throwaway temp SQLite file (via a `monkeypatch`-based fixture in `tests/conftest.py`) — they never touch your real `pawfolio.db` or `photos/` folder. Covers the `db.py` CRUD and due-date logic, the `voice.py` copy templates, and that every page (including the nav itself) loads without exceptions via Streamlit's `AppTest` framework.
