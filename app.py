import streamlit as st
from db import init_db
from styles import inject_theme

st.set_page_config(page_title="Pawfolio", page_icon="🐾", layout="wide")
init_db()

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
