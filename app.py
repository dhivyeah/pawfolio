import streamlit as st
from db import init_db
from styles import inject_theme
from notifications import check_and_notify

st.set_page_config(page_title="Pawfolio", page_icon="🐾", layout="wide")

# Gated to once per browser session, same reasoning as the notification check below --
# init_db() is a batch of idempotent CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
# statements. Cheap against a local SQLite file, but Postgres now means each one is a
# network round-trip to Supabase, so re-running the whole batch on every single widget
# click (Streamlit's normal rerun-the-script-top-to-bottom model) would add needless
# latency to everything in the app, not just page loads.
if not st.session_state.get("_db_initialized"):
    init_db()
    st.session_state["_db_initialized"] = True

# "On app load" means once per browser session, not once per rerun -- app.py re-executes
# top to bottom on every widget interaction anywhere in the app (Streamlit's normal
# execution model), so an unconditional call here would re-check on every single click.
if not st.session_state.get("_notify_checked"):
    check_and_notify()
    st.session_state["_notify_checked"] = True

home_page = st.Page("views/home.py", title="Home", icon="🏠", default=True)
all_profiles_page = st.Page("views/all_profiles.py", title="All the Pups", icon="🐾")
add_profile_page = st.Page("views/add_profile.py", title="New Profile", icon="➕")
profile_detail_page = st.Page("views/profile_detail.py", title="Profile", icon="🐶")

pg = st.navigation(
    [home_page, all_profiles_page, add_profile_page, profile_detail_page],
    position="hidden",
)

inject_theme(st)

# Top icon nav: Home and All the Pups only. "New Profile" lives as a button on the
# Home dashboard instead of the nav, and Profile Detail is only reached by clicking
# a dog — neither belongs in this bar.
with st.container(key="top_nav"):
    nav_cols = st.columns([1, 1, 14])
    with nav_cols[0]:
        if st.button("🏠", key="nav_home", help="Home"):
            st.switch_page(home_page)
    with nav_cols[1]:
        if st.button("🐾🐾", key="nav_profiles", help="All the Pups"):
            st.switch_page(all_profiles_page)

st.divider()

pg.run()
