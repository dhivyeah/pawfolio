from datetime import date
import streamlit as st
from db import create_profile
from ui_helpers import save_uploaded_photo, queue_toast

owner_id = st.session_state["auth_user"]["user_id"]

st.title("New Profile", anchor=False)
st.caption(
    "Create a profile for one of your own dogs, or a friendly dog from the neighborhood. "
    "Vaccinations, friends, and everything else can be added afterward from the profile page."
)

# Profile type lives outside the form so choosing "Community Dog" can reveal the
# hangout-location field immediately, instead of showing it (irrelevantly) for the
# "My Dog" default every time.
profile_type = st.selectbox(
    "Profile type", ["my_dog", "community_dog"],
    format_func=lambda x: "My Dog" if x == "my_dog" else "Community Dog",
)

with st.form("add_profile_form"):
    name = st.text_input("Name *")
    nickname = st.text_input("Nickname (optional)")
    photo = st.file_uploader("Photo", type=["png", "jpg", "jpeg", "webp"])
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("Date of birth", value=None, min_value=date(1990, 1, 1), max_value=date.today())
    with col2:
        dob_estimated = st.checkbox("Date of birth is estimated")
    breed = st.text_input("Breed / mix description")
    hangout_location = None
    if profile_type == "community_dog":
        hangout_location = st.text_input("Usual hangout location/area")
    other_notes = st.text_area("Other notes (optional)")

    submitted = st.form_submit_button("Create Profile", use_container_width=True)

    if submitted:
        if not name:
            st.error("Name is required.")
        else:
            photo_path = save_uploaded_photo(photo)
            profile_id = create_profile({
                "name": name,
                "nickname": nickname or None,
                "photo_path": photo_path,
                "dob": dob.isoformat() if dob else None,
                "dob_estimated": dob_estimated,
                "breed": breed,
                "profile_type": profile_type,
                "date_added": date.today().isoformat(),
                "hangout_location": hangout_location or None,
                "other_notes": other_notes or None,
            }, owner_id)
            st.session_state["selected_profile_id"] = profile_id
            queue_toast(f"{name}'s profile has been created! 🎉", icon="🐾")
            st.switch_page("views/profile_detail.py")
