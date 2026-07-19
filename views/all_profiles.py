import streamlit as st
from db import get_all_profiles, calc_age_str
from ui_helpers import show_photo, render_queued_toast

# "My Pups" -- renamed from "All the Pups" 2026-07-19, purely a label change.
# Still exactly as private as before: every query below is owner_id-scoped,
# covering only this user's own "my_dog" and "community_dog" profiles, nothing
# from any other account. This is NOT the future public "All Pups" feature
# (Phase 5 -- every user's dog names + general location only, no private
# records, with a "friend" option) -- that's a deliberately separate page with
# very different data-scoping, not built yet, not this page renamed further.
owner_id = st.session_state["auth_user"]["user_id"]

# Surfaces the "profile deleted" confirmation queued by profile_detail.py just before
# it redirected here (see ui_helpers.queue_toast for why it can't fire inline there).
render_queued_toast()

title_cols = st.columns([4, 1.4])
with title_cols[0]:
    st.title("My Pups", anchor=False)
with title_cols[1]:
    st.write("")
    if st.button("➕ New Profile", key="all_profiles_add_profile", use_container_width=True):
        st.switch_page("views/add_profile.py")

filter_cols = st.columns([1.3, 1])
with filter_cols[0]:
    filter_choice = st.radio("Show", ["All", "My Dogs", "Community Dogs"], horizontal=True)
with filter_cols[1]:
    sort_choice = st.selectbox("Sort", ["Name (A–Z)", "Recently added", "Upcoming soonest"])

search = st.text_input("Search by name", placeholder="Search by name…")

if filter_choice == "My Dogs":
    profiles = get_all_profiles(owner_id, profile_type="my_dog")
elif filter_choice == "Community Dogs":
    profiles = get_all_profiles(owner_id, profile_type="community_dog")
else:
    profiles = get_all_profiles(owner_id)

if search:
    needle = search.strip().lower()
    profiles = [p for p in profiles if needle in p["name"].lower()]

if sort_choice == "Recently added":
    profiles = sorted(profiles, key=lambda p: p["date_added"], reverse=True)
elif sort_choice == "Upcoming soonest":
    from db import get_upcoming_events
    soonest = {}
    for e in get_upcoming_events(owner_id, horizon_days=365):
        soonest.setdefault(e["profile_id"], e["days_until"])
    profiles = sorted(profiles, key=lambda p: soonest.get(p["id"], float("inf")))
# "Name (A–Z)" is already the query's default order — nothing to do.

st.caption(f"{len(profiles)} profile(s)")
st.divider()

if not profiles:
    if search:
        st.info(f"No dogs match \"{search}\". Try a different name, or clear the search.")
    else:
        st.info("No profiles yet. Head to **New Profile** at the top to add your first dog.")
else:
    # Fewer columns than a full row of 4 keeps cards from stranding in a sea of
    # empty grid space when there are only one or two profiles.
    cols_per_row = min(4, len(profiles))
    rows = [profiles[i:i + cols_per_row] for i in range(0, len(profiles), cols_per_row)]
    for row in rows:
        cols = st.columns(cols_per_row)
        for col, profile in zip(cols, row):
            with col:
                with st.container(border=True, key=f"profile_card_{profile['id']}"):
                    # max_width caps how big the circle can grow when a row has very few
                    # cards (e.g. one search result, or a single stacked mobile column) --
                    # responsive=True alone would let it fill the entire column width.
                    show_photo(profile["photo_path"], responsive=True, shape="circle", max_width=180)
                    st.markdown(f"**{profile['name']}**")
                    type_label = "🏠 My Dog" if profile["profile_type"] == "my_dog" else "🌳 Community Dog"
                    st.caption(type_label)
                    st.caption(calc_age_str(profile["dob"], bool(profile["dob_estimated"])))
                    if st.button("View →", key=f"view_{profile['id']}"):
                        st.session_state["selected_profile_id"] = profile["id"]
                        st.switch_page("views/profile_detail.py")
