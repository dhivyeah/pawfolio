from datetime import date
import streamlit as st
from db import (
    get_profile, update_profile, delete_profile, get_all_profiles,
    calc_age_str,
    add_vaccination, get_vaccinations, update_vaccination, delete_vaccination,
    add_medication, get_medications, update_medication, delete_medication,
    add_friend, get_friends, update_friend, delete_friend,
    add_surgery, get_surgeries, update_surgery, delete_surgery,
    add_vet_visit, get_vet_visits, update_vet_visit, delete_vet_visit,
    add_bath, get_baths, update_bath, delete_bath,
    add_food_refill, get_food_refills, update_food_refill, delete_food_refill,
    add_boarding_stay, get_boarding_stays, update_boarding_stay, delete_boarding_stay,
)
from ui_helpers import show_photo, save_uploaded_photo, show_tag_pills, render_vet_picker

profile_id = st.session_state.get("selected_profile_id")

if not profile_id:
    all_profiles = get_all_profiles()
    if not all_profiles:
        st.info("No profiles yet. Add one from **New Profile** at the top first.")
        st.stop()
    names = {f"{p['name']} ({'My Dog' if p['profile_type']=='my_dog' else 'Community Dog'})": p["id"] for p in all_profiles}
    choice = st.selectbox("Pick a profile", list(names.keys()))
    profile_id = names[choice]
    st.session_state["selected_profile_id"] = profile_id

profile = get_profile(profile_id)
if not profile:
    st.error("This profile no longer exists.")
    st.session_state["selected_profile_id"] = None
    st.stop()

# ---------- Header ----------
header_cols = st.columns([1, 4])
with header_cols[0]:
    show_photo(profile["photo_path"], responsive=True, max_width=260)
with header_cols[1]:
    st.header(profile["name"])
    type_label = "🏠 My Dog" if profile["profile_type"] == "my_dog" else "🌳 Community Dog"
    st.subheader(type_label)
    st.write(calc_age_str(profile["dob"], bool(profile["dob_estimated"])))
    if profile["breed"]:
        st.write(f"Breed: {profile['breed']}")
    if profile["profile_type"] == "community_dog" and profile["hangout_location"]:
        st.write(f"📍 Usually hangs out at: {profile['hangout_location']}")
    st.caption(f"Added to Pawfolio on {profile['date_added']}")

st.divider()

tab_identity, tab_health, tab_personality, tab_social, tab_care = st.tabs(
    ["🪪 Identity", "🩺 Health", "🎾 Personality", "🐕 Social", "🧺 Care & Logistics"]
)

# ================= IDENTITY =================
with tab_identity:
    with st.expander("✏️ Edit Identity"):
        with st.form("edit_identity_form"):
            name = st.text_input("Name", value=profile["name"])
            new_photo = st.file_uploader("Replace photo", type=["png", "jpg", "jpeg", "webp"])
            dob_val = date.fromisoformat(profile["dob"]) if profile["dob"] else None
            dob = st.date_input("Date of birth", value=dob_val, min_value=date(1990, 1, 1), max_value=date.today())
            dob_estimated = st.checkbox("Date of birth is estimated", value=bool(profile["dob_estimated"]))
            breed = st.text_input("Breed / mix description", value=profile["breed"] or "")
            profile_type = st.selectbox(
                "Profile type", ["my_dog", "community_dog"],
                index=0 if profile["profile_type"] == "my_dog" else 1,
                format_func=lambda x: "My Dog" if x == "my_dog" else "Community Dog",
            )
            hangout_location = st.text_input(
                "Usual hangout location (community dogs)", value=profile["hangout_location"] or ""
            )
            submitted = st.form_submit_button("Save Identity")
            if submitted:
                photo_path = profile["photo_path"]
                if new_photo is not None:
                    photo_path = save_uploaded_photo(new_photo)
                data = dict(profile)
                data.update({
                    "name": name,
                    "photo_path": photo_path,
                    "dob": dob.isoformat() if dob else None,
                    "dob_estimated": dob_estimated,
                    "breed": breed,
                    "profile_type": profile_type,
                    "hangout_location": hangout_location,
                })
                update_profile(profile_id, data)
                st.success("Identity updated.")
                st.rerun()

    st.markdown("---")
    st.subheader("Danger zone")
    confirm = st.checkbox("I understand this permanently deletes this profile and all its records.")
    if st.button("🗑️ Delete this profile", disabled=not confirm, key="delete_profile"):
        delete_profile(profile_id)
        st.session_state["selected_profile_id"] = None
        st.success("Profile deleted.")
        st.switch_page("views/all_profiles.py")

# ================= HEALTH =================
with tab_health:
    st.subheader("Vaccinations")
    vaccinations = get_vaccinations(profile_id)
    if not vaccinations:
        st.caption("No vaccination records yet.")
    for v in vaccinations:
        with st.expander(f"💉 {v['vaccine_name']} — next due {v['next_due_date'] or 'unset'}"):
            with st.form(f"edit_vacc_{v['id']}"):
                vname = st.text_input("Vaccine name", value=v["vaccine_name"], key=f"vname_{v['id']}")
                given = st.date_input(
                    "Date given", value=date.fromisoformat(v["date_given"]) if v["date_given"] else None,
                    key=f"vgiven_{v['id']}"
                )
                due = st.date_input(
                    "Next due date", value=date.fromisoformat(v["next_due_date"]) if v["next_due_date"] else None,
                    key=f"vdue_{v['id']}"
                )
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_vaccination(v["id"], vname, given.isoformat() if given else None, due.isoformat() if due else None)
                    st.rerun()
                if remove:
                    delete_vaccination(v["id"])
                    st.rerun()

    with st.expander("➕ Add vaccination"):
        with st.form("add_vacc_form", clear_on_submit=True):
            vname = st.text_input("Vaccine name")
            given = st.date_input("Date given", value=date.today())
            due = st.date_input("Next due date", value=None)
            if st.form_submit_button("Add vaccination"):
                if vname:
                    add_vaccination(profile_id, vname, given.isoformat(), due.isoformat() if due else None)
                    st.success("Vaccination added.")
                    st.rerun()
                else:
                    st.warning("Vaccine name is required.")

    st.divider()
    st.subheader("Chennai Corporation Registration")
    with st.form("edit_registration_form"):
        reg_id = st.text_input("Registration ID", value=profile["reg_id"] or "")
        reg_last_renewed_val = date.fromisoformat(profile["reg_last_renewed"]) if profile["reg_last_renewed"] else None
        reg_last_renewed = st.date_input("Last renewed date", value=reg_last_renewed_val)
        reg_next_due_val = date.fromisoformat(profile["reg_next_due"]) if profile["reg_next_due"] else None
        reg_next_due = st.date_input("Next renewal due date", value=reg_next_due_val)
        if st.form_submit_button("Save registration"):
            data = dict(profile)
            data.update({
                "reg_id": reg_id or None,
                "reg_last_renewed": reg_last_renewed.isoformat() if reg_last_renewed else None,
                "reg_next_due": reg_next_due.isoformat() if reg_next_due else None,
            })
            update_profile(profile_id, data)
            st.success("Registration updated.")
            st.rerun()

    st.divider()
    st.subheader("Current Medications")
    medications = get_medications(profile_id)
    if not medications:
        st.caption("No medications on record.")
    for m in medications:
        status = "ongoing" if m["ongoing"] else f"ends {m['end_date'] or 'unset'}"
        with st.expander(f"💊 {m['med_name']} — {status}"):
            with st.form(f"edit_med_{m['id']}"):
                mname = st.text_input("Medication name", value=m["med_name"], key=f"mname_{m['id']}")
                dosage = st.text_input("Dosage", value=m["dosage"] or "", key=f"mdose_{m['id']}")
                frequency = st.text_input("Frequency", value=m["frequency"] or "", key=f"mfreq_{m['id']}")
                start = st.date_input(
                    "Start date", value=date.fromisoformat(m["start_date"]) if m["start_date"] else None,
                    key=f"mstart_{m['id']}"
                )
                ongoing = st.checkbox("Ongoing (no end date)", value=bool(m["ongoing"]), key=f"mongoing_{m['id']}")
                end = st.date_input(
                    "End date", value=date.fromisoformat(m["end_date"]) if m["end_date"] else None,
                    disabled=ongoing, key=f"mend_{m['id']}"
                )
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_medication(
                        m["id"], mname, dosage, frequency,
                        start.isoformat() if start else None,
                        None if ongoing else (end.isoformat() if end else None),
                        ongoing,
                    )
                    st.rerun()
                if remove:
                    delete_medication(m["id"])
                    st.rerun()

    with st.expander("➕ Add medication"):
        with st.form("add_med_form", clear_on_submit=True):
            mname = st.text_input("Medication name")
            dosage = st.text_input("Dosage")
            frequency = st.text_input("Frequency (e.g. twice daily)")
            start = st.date_input("Start date", value=date.today())
            ongoing = st.checkbox("Ongoing (no end date)", value=True)
            end = st.date_input("End date", value=None, disabled=ongoing)
            if st.form_submit_button("Add medication"):
                if mname:
                    add_medication(
                        profile_id, mname, dosage, frequency, start.isoformat(),
                        None if ongoing else (end.isoformat() if end else None), ongoing
                    )
                    st.success("Medication added.")
                    st.rerun()
                else:
                    st.warning("Medication name is required.")

    st.divider()
    st.subheader("Spay / Neuter Status")
    with st.form("edit_spay_neuter_form"):
        status_options = ["unknown", "yes", "no"]
        current_status = profile["spay_neuter_status"] or "unknown"
        spay_status = st.selectbox(
            "Status", status_options,
            index=status_options.index(current_status) if current_status in status_options else 0,
            format_func=lambda x: {"unknown": "Unknown", "yes": "Yes", "no": "No"}[x],
        )
        spay_date_val = date.fromisoformat(profile["spay_neuter_date"]) if profile["spay_neuter_date"] else None
        spay_date = st.date_input("Date (if known)", value=spay_date_val)
        if st.form_submit_button("Save Spay/Neuter Status"):
            data = dict(profile)
            data.update({
                "spay_neuter_status": spay_status,
                "spay_neuter_date": spay_date.isoformat() if spay_date else None,
            })
            update_profile(profile_id, data)
            st.success("Spay/neuter status updated.")
            st.rerun()

    st.divider()
    st.subheader("Surgeries")
    surgeries = get_surgeries(profile_id)
    if not surgeries:
        st.caption("No surgeries on record.")
    for s in surgeries:
        with st.expander(f"🩹 {s['surgery_name']} — {s['surgery_date'] or 'date unknown'}"):
            with st.form(f"edit_surgery_{s['id']}"):
                sname = st.text_input("Surgery name/description", value=s["surgery_name"], key=f"sname_{s['id']}")
                sdate = st.date_input(
                    "Date", value=date.fromisoformat(s["surgery_date"]) if s["surgery_date"] else None,
                    key=f"sdate_{s['id']}"
                )
                snotes = st.text_area("Notes", value=s["notes"] or "", key=f"snotes_{s['id']}")
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_surgery(s["id"], sname, sdate.isoformat() if sdate else None, snotes)
                    st.rerun()
                if remove:
                    delete_surgery(s["id"])
                    st.rerun()

    with st.expander("➕ Add surgery"):
        with st.form("add_surgery_form", clear_on_submit=True):
            sname = st.text_input("Surgery name/description")
            sdate = st.date_input("Date", value=date.today())
            snotes = st.text_area("Notes")
            if st.form_submit_button("Add surgery"):
                if sname:
                    add_surgery(profile_id, sname, sdate.isoformat(), snotes)
                    st.success("Surgery added.")
                    st.rerun()
                else:
                    st.warning("Surgery name/description is required.")

    st.divider()
    st.subheader("Vet Visit History")
    visits = get_vet_visits(profile_id)
    if not visits:
        st.caption("No vet visits on record.")
    for vv in visits:
        with st.expander(f"🩺 {vv['visit_date'] or 'date unknown'} — {vv['reason'] or 'visit'}"):
            with st.form(f"edit_visit_{vv['id']}"):
                vdate = st.date_input(
                    "Visit date", value=date.fromisoformat(vv["visit_date"]) if vv["visit_date"] else None,
                    key=f"vvdate_{vv['id']}"
                )
                vreason = st.text_input("Reason", value=vv["reason"] or "", key=f"vvreason_{vv['id']}")
                vnotes = st.text_area("Notes", value=vv["notes"] or "", key=f"vvnotes_{vv['id']}")
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_vet_visit(vv["id"], vdate.isoformat() if vdate else None, vreason, vnotes)
                    st.rerun()
                if remove:
                    delete_vet_visit(vv["id"])
                    st.rerun()

    with st.expander("➕ Add vet visit"):
        with st.form("add_visit_form", clear_on_submit=True):
            vdate = st.date_input("Visit date", value=date.today())
            vreason = st.text_input("Reason")
            vnotes = st.text_area("Notes")
            if st.form_submit_button("Add vet visit"):
                add_vet_visit(profile_id, vdate.isoformat(), vreason, vnotes)
                st.success("Vet visit added.")
                st.rerun()

    st.divider()
    st.subheader("Vets")
    render_vet_picker(profile_id, key_prefix=f"vetpicker_{profile_id}")

# ================= PERSONALITY =================
with tab_personality:
    with st.expander("✏️ Edit Personality", expanded=True):
        with st.form("edit_personality_form"):
            likes = st.text_input("Likes (comma-separated)", value=profile["likes"] or "")
            dislikes = st.text_input("Dislikes (comma-separated)", value=profile["dislikes"] or "")
            favorite_toys = st.text_input("Favorite toys (comma-separated)", value=profile["favorite_toys"] or "")
            favorite_foods = st.text_input("Favorite foods (comma-separated)", value=profile["favorite_foods"] or "")
            foods_to_avoid = st.text_input("Foods to avoid / allergies (comma-separated)", value=profile["foods_to_avoid"] or "")
            favorite_games = st.text_input("Favorite games/activities (comma-separated)", value=profile["favorite_games"] or "")
            if st.form_submit_button("Save Personality"):
                data = dict(profile)
                data.update({
                    "likes": likes, "dislikes": dislikes, "favorite_toys": favorite_toys,
                    "favorite_foods": favorite_foods, "foods_to_avoid": foods_to_avoid,
                    "favorite_games": favorite_games,
                })
                update_profile(profile_id, data)
                st.success("Personality updated.")
                st.rerun()

    st.markdown("**❤️ Likes**")
    show_tag_pills(profile["likes"])
    st.markdown("**🚫 Dislikes**")
    show_tag_pills(profile["dislikes"])
    st.markdown("**🧸 Favorite toys**")
    show_tag_pills(profile["favorite_toys"])
    st.markdown("**🍖 Favorite foods**")
    show_tag_pills(profile["favorite_foods"])
    st.markdown("**⚠️ Foods to avoid / allergies**")
    show_tag_pills(profile["foods_to_avoid"])
    st.markdown("**🎾 Favorite games/activities**")
    show_tag_pills(profile["favorite_games"])

# ================= SOCIAL =================
with tab_social:
    st.subheader("Friends")
    friends = get_friends(profile_id)
    if not friends:
        st.caption("No friends on record yet.")
    for f in friends:
        with st.expander(f"🐕 {f['friend_name']}"):
            with st.form(f"edit_friend_{f['id']}"):
                fname = st.text_input("Friend's name", value=f["friend_name"], key=f"fname_{f['id']}")
                fbday_val = date.fromisoformat(f["friend_birthday"]) if f["friend_birthday"] else None
                fbday = st.date_input("Friend's birthday (optional)", value=fbday_val, key=f"fbday_{f['id']}")
                fnotes = st.text_area("Notes", value=f["notes"] or "", key=f"fnotes_{f['id']}")
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_friend(f["id"], fname, fbday.isoformat() if fbday else None, fnotes)
                    st.rerun()
                if remove:
                    delete_friend(f["id"])
                    st.rerun()

    with st.expander("➕ Add friend"):
        with st.form("add_friend_form", clear_on_submit=True):
            fname = st.text_input("Friend's name")
            fbday = st.date_input("Friend's birthday (optional)", value=None)
            fnotes = st.text_area("Notes")
            if st.form_submit_button("Add friend"):
                if fname:
                    add_friend(profile_id, fname, fbday.isoformat() if fbday else None, fnotes)
                    st.success("Friend added.")
                    st.rerun()
                else:
                    st.warning("Friend's name is required.")

# ================= CARE & LOGISTICS =================
with tab_care:
    st.subheader("🛁 Bath Tracking")
    baths = get_baths(profile_id)
    if not baths:
        st.caption("No bath records yet.")
    for b in baths:
        with st.expander(f"🛁 Last bath {b['bath_date'] or 'unknown'} — next due {b['next_due_date'] or 'unset'}"):
            with st.form(f"edit_bath_{b['id']}"):
                bdate = st.date_input(
                    "Last bath date", value=date.fromisoformat(b["bath_date"]) if b["bath_date"] else None,
                    key=f"bdate_{b['id']}"
                )
                bdue = st.date_input(
                    "Next due date", value=date.fromisoformat(b["next_due_date"]) if b["next_due_date"] else None,
                    key=f"bdue_{b['id']}"
                )
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_bath(b["id"], bdate.isoformat() if bdate else None, bdue.isoformat() if bdue else None)
                    st.rerun()
                if remove:
                    delete_bath(b["id"])
                    st.rerun()

    with st.expander("➕ Add bath record"):
        with st.form("add_bath_form", clear_on_submit=True):
            bdate = st.date_input("Last bath date", value=date.today())
            bdue = st.date_input("Next due date", value=None)
            if st.form_submit_button("Add bath record"):
                add_bath(profile_id, bdate.isoformat(), bdue.isoformat() if bdue else None)
                st.success("Bath record added.")
                st.rerun()

    st.divider()
    st.subheader("🥣 Food Refill Tracking")
    refills = get_food_refills(profile_id)
    if not refills:
        st.caption("No food refill records yet.")
    for fr in refills:
        with st.expander(f"🥣 {fr['food_type'] or 'food'} — next refill {fr['next_refill_date'] or 'unset'}"):
            with st.form(f"edit_refill_{fr['id']}"):
                ftype = st.text_input("Food brand/type", value=fr["food_type"] or "", key=f"ftype_{fr['id']}")
                flast = st.date_input(
                    "Last refill date", value=date.fromisoformat(fr["last_refill_date"]) if fr["last_refill_date"] else None,
                    key=f"flast_{fr['id']}"
                )
                fnext = st.date_input(
                    "Next refill due date", value=date.fromisoformat(fr["next_refill_date"]) if fr["next_refill_date"] else None,
                    key=f"fnext_{fr['id']}"
                )
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_food_refill(
                        fr["id"], ftype,
                        flast.isoformat() if flast else None,
                        fnext.isoformat() if fnext else None,
                    )
                    st.rerun()
                if remove:
                    delete_food_refill(fr["id"])
                    st.rerun()

    with st.expander("➕ Add food refill record"):
        with st.form("add_refill_form", clear_on_submit=True):
            ftype = st.text_input("Food brand/type")
            flast = st.date_input("Last refill date", value=date.today())
            fnext = st.date_input("Next refill due date", value=None)
            if st.form_submit_button("Add food refill record"):
                add_food_refill(profile_id, ftype, flast.isoformat(), fnext.isoformat() if fnext else None)
                st.success("Food refill record added.")
                st.rerun()

    st.divider()
    st.subheader("🧳 Boarding History")
    stays = get_boarding_stays(profile_id)
    if not stays:
        st.caption("No boarding history yet.")
    for bs in stays:
        with st.expander(f"🧳 {bs['facility_name'] or 'boarding'} — {bs['check_in_date'] or '?'} to {bs['check_out_date'] or '?'}"):
            with st.form(f"edit_stay_{bs['id']}"):
                facility = st.text_input("Boarding facility name", value=bs["facility_name"] or "", key=f"facility_{bs['id']}")
                check_in = st.date_input(
                    "Check-in date", value=date.fromisoformat(bs["check_in_date"]) if bs["check_in_date"] else None,
                    key=f"checkin_{bs['id']}"
                )
                check_out = st.date_input(
                    "Check-out date", value=date.fromisoformat(bs["check_out_date"]) if bs["check_out_date"] else None,
                    key=f"checkout_{bs['id']}"
                )
                bnotes = st.text_area("Notes", value=bs["notes"] or "", key=f"bnotes_{bs['id']}")
                col1, col2 = st.columns(2)
                save = col1.form_submit_button("Save")
                remove = col2.form_submit_button("Delete")
                if save:
                    update_boarding_stay(
                        bs["id"], facility,
                        check_in.isoformat() if check_in else None,
                        check_out.isoformat() if check_out else None,
                        bnotes,
                    )
                    st.rerun()
                if remove:
                    delete_boarding_stay(bs["id"])
                    st.rerun()

    with st.expander("➕ Add boarding stay"):
        with st.form("add_stay_form", clear_on_submit=True):
            facility = st.text_input("Boarding facility name")
            check_in = st.date_input("Check-in date", value=date.today())
            check_out = st.date_input("Check-out date", value=None)
            bnotes = st.text_area("Notes")
            if st.form_submit_button("Add boarding stay"):
                if facility:
                    add_boarding_stay(
                        profile_id, facility, check_in.isoformat(),
                        check_out.isoformat() if check_out else None, bnotes
                    )
                    st.success("Boarding stay added.")
                    st.rerun()
                else:
                    st.warning("Boarding facility name is required.")
