import streamlit as st
from db import get_all_profiles, calc_age_str
from ui_helpers import show_photo

title_cols = st.columns([4, 1.4])
with title_cols[0]:
    st.title("All the Pups")
with title_cols[1]:
    st.write("")
    if st.button("➕ New Profile", key="all_profiles_add_profile", use_container_width=True):
        st.switch_page("views/add_profile.py")

filter_choice = st.radio(
    "Show",
    ["All", "My Dogs", "Community Dogs"],
    horizontal=True,
)

if filter_choice == "My Dogs":
    profiles = get_all_profiles(profile_type="my_dog")
elif filter_choice == "Community Dogs":
    profiles = get_all_profiles(profile_type="community_dog")
else:
    profiles = get_all_profiles()

st.caption(f"{len(profiles)} profile(s)")
st.divider()

if not profiles:
    st.info("No profiles yet. Head to **New Profile** at the top to add your first dog.")
else:
    cols_per_row = 4
    rows = [profiles[i:i + cols_per_row] for i in range(0, len(profiles), cols_per_row)]
    for row in rows:
        cols = st.columns(cols_per_row)
        for col, profile in zip(cols, row):
            with col:
                with st.container(border=True, key=f"profile_card_{profile['id']}"):
                    show_photo(profile["photo_path"], responsive=True, shape="circle")
                    st.markdown(f"**{profile['name']}**")
                    type_label = "🏠 My Dog" if profile["profile_type"] == "my_dog" else "🌳 Community Dog"
                    st.caption(type_label)
                    st.caption(calc_age_str(profile["dob"], bool(profile["dob_estimated"])))
                    if st.button("View", key=f"view_{profile['id']}", use_container_width=True):
                        st.session_state["selected_profile_id"] = profile["id"]
                        st.switch_page("views/profile_detail.py")
