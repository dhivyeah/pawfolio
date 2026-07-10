from datetime import date
import streamlit as st
from db import (
    create_profile, add_vaccination, add_medication, add_friend,
    add_surgery, add_vet_visit, create_vet, link_vet_to_profile, get_all_vets,
    add_bath, add_food_refill, add_boarding_stay,
)
from ui_helpers import save_uploaded_photo

_ADD_NEW_VET_OPTION = "➕ Add a new vet below"

st.title("New Profile")
st.caption("Create a profile for one of your own dogs, or a friendly dog from the neighborhood.")

with st.form("add_profile_form"):
    st.subheader("🪪 Identity")
    name = st.text_input("Name *")
    photo = st.file_uploader("Photo", type=["png", "jpg", "jpeg", "webp"])
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("Date of birth", value=None, min_value=date(1990, 1, 1), max_value=date.today())
    with col2:
        dob_estimated = st.checkbox("Date of birth is estimated")
    breed = st.text_input("Breed / mix description")
    profile_type = st.selectbox(
        "Profile type", ["my_dog", "community_dog"],
        format_func=lambda x: "My Dog" if x == "my_dog" else "Community Dog",
    )
    hangout_location = st.text_input("Usual hangout location/area (community dogs only)")

    st.divider()
    st.subheader("🩺 Health")
    st.caption("You can add vaccination and medication history here, or come back later from the profile page.")

    st.markdown("**Vaccination record (optional, first entry)**")
    vcol1, vcol2, vcol3 = st.columns(3)
    with vcol1:
        vacc_name = st.text_input("Vaccine name")
    with vcol2:
        vacc_given = st.date_input("Date given", value=None, key="vacc_given")
    with vcol3:
        vacc_due = st.date_input("Next due date", value=None, key="vacc_due")

    st.markdown("**Chennai Corporation registration**")
    rcol1, rcol2, rcol3 = st.columns(3)
    with rcol1:
        reg_id = st.text_input("Registration ID")
    with rcol2:
        reg_last_renewed = st.date_input("Last renewed date", value=None, key="reg_last")
    with rcol3:
        reg_next_due = st.date_input("Next renewal due date", value=None, key="reg_next")

    st.markdown("**Current medication (optional, first entry)**")
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        med_name = st.text_input("Medication name")
        dosage = st.text_input("Dosage")
    with mcol2:
        frequency = st.text_input("Frequency")
        med_start = st.date_input("Start date", value=None, key="med_start")
    with mcol3:
        ongoing = st.checkbox("Ongoing", value=True)
        med_end = st.date_input("End date", value=None, key="med_end", disabled=ongoing)

    st.markdown("**Spay / neuter status**")
    spcol1, spcol2 = st.columns(2)
    with spcol1:
        spay_neuter_status = st.selectbox(
            "Status", ["unknown", "yes", "no"],
            format_func=lambda x: {"unknown": "Unknown", "yes": "Yes", "no": "No"}[x],
        )
    with spcol2:
        spay_neuter_date = st.date_input("Date (if known)", value=None, key="spay_neuter_date")

    st.markdown("**First surgery on record (optional)**")
    surgcol1, surgcol2 = st.columns(2)
    with surgcol1:
        surgery_name = st.text_input("Surgery name/description")
    with surgcol2:
        surgery_date = st.date_input("Date", value=None, key="surgery_date")
    surgery_notes = st.text_area("Surgery notes", key="surgery_notes")

    st.markdown("**First vet visit on record (optional)**")
    vvcol1, vvcol2 = st.columns(2)
    with vvcol1:
        visit_date = st.date_input("Visit date", value=None, key="visit_date")
    with vvcol2:
        visit_reason = st.text_input("Reason")
    visit_notes = st.text_area("Visit notes", key="visit_notes")

    st.markdown("**Primary vet (optional)**")
    existing_vets = get_all_vets()
    vet_choice_labels = [_ADD_NEW_VET_OPTION] + [
        f"{v['vet_name']} — {v['clinic_name'] or 'no clinic listed'}" for v in existing_vets
    ]
    vet_choice_index = st.selectbox(
        "Use an existing vet from your directory, or add a new one below",
        options=range(len(vet_choice_labels)), format_func=lambda i: vet_choice_labels[i],
    )
    st.caption("Only needed if adding a new vet — ignored if you picked an existing one above.")
    vetcol1, vetcol2 = st.columns(2)
    with vetcol1:
        vet_name = st.text_input("Vet name")
        vet_phone = st.text_input("Phone number")
    with vetcol2:
        vet_clinic = st.text_input("Clinic name")
        vet_address = st.text_input("Address")
    vet_notes = st.text_area("Vet notes", key="vet_notes")

    st.divider()
    st.subheader("🧺 Care & Logistics")
    st.caption("Optional first entries — you can add more anytime from the profile page.")

    st.markdown("**First bath record (optional)**")
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        bath_date = st.date_input("Last bath date", value=None, key="bath_date")
    with bcol2:
        bath_next_due = st.date_input("Next due date", value=None, key="bath_next_due")

    st.markdown("**First food refill record (optional)**")
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        food_type = st.text_input("Food brand/type")
    with fcol2:
        food_last_refill = st.date_input("Last refill date", value=None, key="food_last_refill")
    with fcol3:
        food_next_refill = st.date_input("Next refill due date", value=None, key="food_next_refill")

    st.markdown("**First boarding stay (optional)**")
    bscol1, bscol2, bscol3 = st.columns(3)
    with bscol1:
        boarding_facility = st.text_input("Boarding facility name")
    with bscol2:
        boarding_checkin = st.date_input("Check-in date", value=None, key="boarding_checkin")
    with bscol3:
        boarding_checkout = st.date_input("Check-out date", value=None, key="boarding_checkout")
    boarding_notes = st.text_area("Boarding notes", key="boarding_notes")

    st.divider()
    st.subheader("🎾 Personality")
    st.caption("Comma-separated tags, e.g. \"belly rubs, car rides\"")
    likes = st.text_input("Likes")
    dislikes = st.text_input("Dislikes")
    favorite_toys = st.text_input("Favorite toys")
    favorite_foods = st.text_input("Favorite foods")
    foods_to_avoid = st.text_input("Foods to avoid / allergies")
    favorite_games = st.text_input("Favorite games/activities")

    st.divider()
    st.subheader("🐕 Social")
    st.markdown("**First friend (optional)**")
    scol1, scol2 = st.columns(2)
    with scol1:
        friend_name = st.text_input("Friend's name")
    with scol2:
        friend_bday = st.date_input("Friend's birthday (optional)", value=None, key="friend_bday")
    friend_notes = st.text_area("Notes about this friend")

    submitted = st.form_submit_button("Create Profile", use_container_width=True)

    if submitted:
        if not name:
            st.error("Name is required.")
        else:
            photo_path = save_uploaded_photo(photo)
            profile_id = create_profile({
                "name": name,
                "photo_path": photo_path,
                "dob": dob.isoformat() if dob else None,
                "dob_estimated": dob_estimated,
                "breed": breed,
                "profile_type": profile_type,
                "date_added": date.today().isoformat(),
                "hangout_location": hangout_location or None,
                "reg_id": reg_id or None,
                "reg_last_renewed": reg_last_renewed.isoformat() if reg_last_renewed else None,
                "reg_next_due": reg_next_due.isoformat() if reg_next_due else None,
                "likes": likes, "dislikes": dislikes, "favorite_toys": favorite_toys,
                "favorite_foods": favorite_foods, "foods_to_avoid": foods_to_avoid,
                "favorite_games": favorite_games,
                "spay_neuter_status": spay_neuter_status,
                "spay_neuter_date": spay_neuter_date.isoformat() if spay_neuter_date else None,
            })

            if vacc_name:
                add_vaccination(
                    profile_id, vacc_name,
                    vacc_given.isoformat() if vacc_given else None,
                    vacc_due.isoformat() if vacc_due else None,
                )
            if surgery_name:
                add_surgery(profile_id, surgery_name, surgery_date.isoformat() if surgery_date else None, surgery_notes)
            if visit_date or visit_reason:
                add_vet_visit(profile_id, visit_date.isoformat() if visit_date else None, visit_reason, visit_notes)
            if vet_choice_index > 0:
                vet_id = existing_vets[vet_choice_index - 1]["id"]
                link_vet_to_profile(profile_id, vet_id, is_primary=True)
            elif vet_name:
                vet_id = create_vet(vet_name, vet_clinic, vet_phone, vet_address, vet_notes)
                link_vet_to_profile(profile_id, vet_id, is_primary=True)
            if bath_date or bath_next_due:
                add_bath(profile_id, bath_date.isoformat() if bath_date else None,
                          bath_next_due.isoformat() if bath_next_due else None)
            if food_type:
                add_food_refill(profile_id, food_type,
                                 food_last_refill.isoformat() if food_last_refill else None,
                                 food_next_refill.isoformat() if food_next_refill else None)
            if boarding_facility:
                add_boarding_stay(profile_id, boarding_facility,
                                   boarding_checkin.isoformat() if boarding_checkin else None,
                                   boarding_checkout.isoformat() if boarding_checkout else None,
                                   boarding_notes)
            if med_name:
                add_medication(
                    profile_id, med_name, dosage, frequency,
                    med_start.isoformat() if med_start else None,
                    None if ongoing else (med_end.isoformat() if med_end else None),
                    ongoing,
                )
            if friend_name:
                add_friend(profile_id, friend_name, friend_bday.isoformat() if friend_bday else None, friend_notes)

            st.session_state["selected_profile_id"] = profile_id
            st.success(f"{name}'s profile has been created! 🎉")
            st.switch_page("views/profile_detail.py")
