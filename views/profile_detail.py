from datetime import date
import streamlit as st
from db import (
    get_profile, update_profile, delete_profile, get_all_profiles,
    calc_age_str, get_vets_for_profile,
    add_vaccination, get_vaccinations, update_vaccination, delete_vaccination,
    add_medication, get_medications, update_medication, delete_medication,
    add_friend, get_friends, update_friend, delete_friend,
    add_sibling, get_siblings, remove_sibling, count_incoming_links,
    add_surgery, get_surgeries, update_surgery, delete_surgery,
    add_vet_visit, get_vet_visits, update_vet_visit, delete_vet_visit,
    add_bath, get_baths, update_bath, delete_bath,
    add_food_refill, get_food_refills, update_food_refill, delete_food_refill,
    add_boarding_stay, get_boarding_stays, update_boarding_stay, delete_boarding_stay,
)
from ui_helpers import (
    show_photo, save_uploaded_photo, show_tag_pills, render_vet_picker,
    request_delete, render_pending_delete_dialog, queue_toast, render_queued_toast,
)

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


def _record_row(summary: str, key: str, on_click):
    """A single existing record as a compact read-only line + an Edit button that
    opens a dialog. Used for every record list on this page instead of an expander,
    since a dialog always closes cleanly on Save/Delete/Cancel — an expander's
    open/closed state is "sticky" in the browser and can't be forced shut from Python
    once a user has touched it, which is what made an old expander-per-record layout
    feel like it never collapsed after an action."""
    with st.container(border=True):
        cols = st.columns([5, 1.3])
        cols[0].markdown(summary)
        if cols[1].button("Edit", key=key, use_container_width=True):
            on_click()


# ============================================================
# Identity
# ============================================================

@st.dialog("Edit Identity")
def _edit_identity_dialog(profile_id, profile):
    # Profile type lives outside the form so switching to "Community Dog" can reveal
    # the hangout-location field immediately, rather than always showing a field
    # that's only relevant to the other case.
    profile_type = st.selectbox(
        "Profile type", ["my_dog", "community_dog"],
        index=0 if profile["profile_type"] == "my_dog" else 1,
        format_func=lambda x: "My Dog" if x == "my_dog" else "Community Dog",
    )
    with st.form("edit_identity_form"):
        name = st.text_input("Name", value=profile["name"])
        nickname = st.text_input("Nickname (optional)", value=profile["nickname"] or "")
        new_photo = st.file_uploader("Replace photo", type=["png", "jpg", "jpeg", "webp"])
        dob_val = date.fromisoformat(profile["dob"]) if profile["dob"] else None
        dob = st.date_input("Date of birth", value=dob_val, min_value=date(1990, 1, 1), max_value=date.today())
        dob_estimated = st.checkbox("Date of birth is estimated", value=bool(profile["dob_estimated"]))
        breed = st.text_input("Breed / mix description", value=profile["breed"] or "")
        hangout_location = profile["hangout_location"] or ""
        if profile_type == "community_dog":
            hangout_location = st.text_input("Usual hangout location", value=hangout_location)
        other_notes = st.text_area("Other notes (optional)", value=profile["other_notes"] or "")
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Save Identity", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_edit_identity", use_container_width=True)
    if submitted:
        photo_path = profile["photo_path"]
        if new_photo is not None:
            photo_path = save_uploaded_photo(new_photo)
        data = dict(profile)
        data.update({
            "name": name,
            "nickname": nickname or None,
            "photo_path": photo_path,
            "dob": dob.isoformat() if dob else None,
            "dob_estimated": dob_estimated,
            "breed": breed,
            "profile_type": profile_type,
            "hangout_location": hangout_location or None,
            "other_notes": other_notes or None,
        })
        update_profile(profile_id, data)
        queue_toast("Identity updated.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


@st.dialog("Delete profile?")
def _delete_profile_dialog(profile_id, profile_name):
    st.warning(
        f"Permanently delete **{profile_name}**'s profile? This also deletes every "
        "vaccination, medication, surgery, vet visit, friend, bath, food refill, and "
        "boarding record on file for them. This can't be undone."
    )
    friend_refs, sibling_refs = count_incoming_links(profile_id)
    if friend_refs or sibling_refs:
        mentions = []
        if friend_refs:
            mentions.append(f"{friend_refs} other profile{'s' if friend_refs != 1 else ''} that lists {profile_name} as a friend")
        if sibling_refs:
            mentions.append(f"{sibling_refs} sibling link{'s' if sibling_refs != 1 else ''}")
        st.warning(f"Also removes {profile_name} from " + " and ".join(mentions) + " — those profiles aren't deleted, just the connection to this one.")
    c1, c2 = st.columns(2)
    if c1.button("Yes, delete permanently", key="delete_confirm_yes", use_container_width=True):
        delete_profile(profile_id)
        st.session_state["selected_profile_id"] = None
        queue_toast(f"{profile_name}'s profile was deleted.", icon="🗑️")
        st.switch_page("views/all_profiles.py")
    if c2.button("Cancel", key="cancel_delete_profile", use_container_width=True):
        st.rerun()


# ============================================================
# Vaccinations
# ============================================================

@st.dialog("Add vaccination")
def _add_vaccination_dialog(profile_id):
    with st.form("add_vacc_form_dialog", clear_on_submit=True):
        vname = st.text_input("Vaccine name")
        given = st.date_input("Date given", value=date.today())
        due = st.date_input("Next due date", value=None)
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add vaccination", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_vacc", use_container_width=True)
    if submitted:
        if vname:
            add_vaccination(profile_id, vname, given.isoformat(), due.isoformat() if due else None)
            queue_toast("Vaccination added.", icon="✅")
            st.rerun()
        else:
            st.warning("Vaccine name is required.")
    if cancelled:
        st.rerun()


@st.dialog("Edit vaccination")
def _edit_vaccination_dialog(v):
    with st.form(f"edit_vacc_dialog_{v['id']}"):
        vname = st.text_input("Vaccine name", value=v["vaccine_name"])
        given = st.date_input("Date given", value=date.fromisoformat(v["date_given"]) if v["date_given"] else None)
        due = st.date_input("Next due date", value=date.fromisoformat(v["next_due_date"]) if v["next_due_date"] else None)
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", use_container_width=True)
        remove = c2.form_submit_button("Delete", key=f"delete_vacc_{v['id']}", use_container_width=True)
        cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_vacc_{v['id']}", use_container_width=True)
    if save:
        update_vaccination(v["id"], vname, given.isoformat() if given else None, due.isoformat() if due else None)
        queue_toast("Vaccination updated.", icon="✅")
        st.rerun()
    if remove:
        request_delete(f"the vaccination **{v['vaccine_name']}**", lambda vid=v["id"]: delete_vaccination(vid), "Vaccination deleted.")
    if cancel:
        st.rerun()


# ============================================================
# Chennai Corporation Registration
# ============================================================

@st.dialog("Edit Registration")
def _edit_registration_dialog(profile_id, profile):
    with st.form("edit_registration_form"):
        reg_id = st.text_input("Registration ID", value=profile["reg_id"] or "")
        reg_last_renewed_val = date.fromisoformat(profile["reg_last_renewed"]) if profile["reg_last_renewed"] else None
        reg_last_renewed = st.date_input("Last renewed date", value=reg_last_renewed_val)
        reg_next_due_val = date.fromisoformat(profile["reg_next_due"]) if profile["reg_next_due"] else None
        reg_next_due = st.date_input("Next renewal due date", value=reg_next_due_val)
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Save registration", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_edit_reg", use_container_width=True)
    if submitted:
        data = dict(profile)
        data.update({
            "reg_id": reg_id or None,
            "reg_last_renewed": reg_last_renewed.isoformat() if reg_last_renewed else None,
            "reg_next_due": reg_next_due.isoformat() if reg_next_due else None,
        })
        update_profile(profile_id, data)
        queue_toast("Registration updated.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


# ============================================================
# Medications
# ============================================================

@st.dialog("Add medication")
def _add_medication_dialog(profile_id):
    with st.form("add_med_form_dialog", clear_on_submit=True):
        mname = st.text_input("Medication name")
        dosage = st.text_input("Dosage")
        frequency = st.text_input("Frequency (e.g. twice daily)")
        start = st.date_input("Start date", value=date.today())
        ongoing = st.checkbox("Ongoing (no end date)", value=True)
        end = st.date_input("End date", value=None, disabled=ongoing)
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add medication", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_med", use_container_width=True)
    if submitted:
        if mname:
            add_medication(
                profile_id, mname, dosage, frequency, start.isoformat(),
                None if ongoing else (end.isoformat() if end else None), ongoing
            )
            queue_toast("Medication added.", icon="✅")
            st.rerun()
        else:
            st.warning("Medication name is required.")
    if cancelled:
        st.rerun()


@st.dialog("Edit medication")
def _edit_medication_dialog(m):
    with st.form(f"edit_med_dialog_{m['id']}"):
        mname = st.text_input("Medication name", value=m["med_name"])
        dosage = st.text_input("Dosage", value=m["dosage"] or "")
        frequency = st.text_input("Frequency", value=m["frequency"] or "")
        start = st.date_input("Start date", value=date.fromisoformat(m["start_date"]) if m["start_date"] else None)
        ongoing = st.checkbox("Ongoing (no end date)", value=bool(m["ongoing"]))
        end = st.date_input("End date", value=date.fromisoformat(m["end_date"]) if m["end_date"] else None, disabled=ongoing)
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", use_container_width=True)
        remove = c2.form_submit_button("Delete", key=f"delete_med_{m['id']}", use_container_width=True)
        cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_med_{m['id']}", use_container_width=True)
    if save:
        update_medication(
            m["id"], mname, dosage, frequency,
            start.isoformat() if start else None,
            None if ongoing else (end.isoformat() if end else None),
            ongoing,
        )
        queue_toast("Medication updated.", icon="✅")
        st.rerun()
    if remove:
        request_delete(f"the medication **{m['med_name']}**", lambda mid=m["id"]: delete_medication(mid), "Medication deleted.")
    if cancel:
        st.rerun()


# ============================================================
# Spay / Neuter
# ============================================================

@st.dialog("Edit Spay/Neuter Status")
def _edit_spay_neuter_dialog(profile_id, profile):
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
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Save Spay/Neuter Status", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_edit_spay", use_container_width=True)
    if submitted:
        data = dict(profile)
        data.update({
            "spay_neuter_status": spay_status,
            "spay_neuter_date": spay_date.isoformat() if spay_date else None,
        })
        update_profile(profile_id, data)
        queue_toast("Spay/neuter status updated.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


# ============================================================
# Surgeries
# ============================================================

@st.dialog("Add surgery")
def _add_surgery_dialog(profile_id):
    with st.form("add_surgery_form_dialog", clear_on_submit=True):
        sname = st.text_input("Surgery name/description")
        sdate = st.date_input("Date", value=date.today())
        snotes = st.text_area("Notes")
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add surgery", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_surgery", use_container_width=True)
    if submitted:
        if sname:
            add_surgery(profile_id, sname, sdate.isoformat(), snotes)
            queue_toast("Surgery added.", icon="✅")
            st.rerun()
        else:
            st.warning("Surgery name/description is required.")
    if cancelled:
        st.rerun()


@st.dialog("Edit surgery")
def _edit_surgery_dialog(s):
    with st.form(f"edit_surgery_dialog_{s['id']}"):
        sname = st.text_input("Surgery name/description", value=s["surgery_name"])
        sdate = st.date_input("Date", value=date.fromisoformat(s["surgery_date"]) if s["surgery_date"] else None)
        snotes = st.text_area("Notes", value=s["notes"] or "")
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", use_container_width=True)
        remove = c2.form_submit_button("Delete", key=f"delete_surgery_{s['id']}", use_container_width=True)
        cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_surgery_{s['id']}", use_container_width=True)
    if save:
        update_surgery(s["id"], sname, sdate.isoformat() if sdate else None, snotes)
        queue_toast("Surgery updated.", icon="✅")
        st.rerun()
    if remove:
        request_delete(f"the surgery record **{s['surgery_name']}**", lambda sid=s["id"]: delete_surgery(sid), "Surgery record deleted.")
    if cancel:
        st.rerun()


# ============================================================
# Vet visits
# ============================================================

@st.dialog("Add vet visit")
def _add_vet_visit_dialog(profile_id):
    with st.form("add_visit_form_dialog", clear_on_submit=True):
        vdate = st.date_input("Visit date", value=date.today())
        vreason = st.text_input("Reason")
        vnotes = st.text_area("Notes")
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add vet visit", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_visit", use_container_width=True)
    if submitted:
        add_vet_visit(profile_id, vdate.isoformat(), vreason, vnotes)
        queue_toast("Vet visit added.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


@st.dialog("Edit vet visit")
def _edit_vet_visit_dialog(vv):
    with st.form(f"edit_visit_dialog_{vv['id']}"):
        vdate = st.date_input("Visit date", value=date.fromisoformat(vv["visit_date"]) if vv["visit_date"] else None)
        vreason = st.text_input("Reason", value=vv["reason"] or "")
        vnotes = st.text_area("Notes", value=vv["notes"] or "")
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", use_container_width=True)
        remove = c2.form_submit_button("Delete", key=f"delete_visit_{vv['id']}", use_container_width=True)
        cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_visit_{vv['id']}", use_container_width=True)
    if save:
        update_vet_visit(vv["id"], vdate.isoformat() if vdate else None, vreason, vnotes)
        queue_toast("Vet visit updated.", icon="✅")
        st.rerun()
    if remove:
        request_delete(f"this vet visit record ({vv['visit_date'] or 'date unknown'})", lambda vvid=vv["id"]: delete_vet_visit(vvid), "Vet visit deleted.")
    if cancel:
        st.rerun()


# ============================================================
# Personality
# ============================================================

@st.dialog("Edit Personality")
def _edit_personality_dialog(profile_id, profile):
    with st.form("edit_personality_form"):
        likes = st.text_input("Likes (comma-separated)", value=profile["likes"] or "")
        dislikes = st.text_input("Dislikes (comma-separated)", value=profile["dislikes"] or "")
        favorite_toys = st.text_input("Favorite toys (comma-separated)", value=profile["favorite_toys"] or "")
        favorite_foods = st.text_input("Favorite foods (comma-separated)", value=profile["favorite_foods"] or "")
        foods_to_avoid = st.text_input("Foods to avoid / allergies (comma-separated)", value=profile["foods_to_avoid"] or "")
        favorite_games = st.text_input("Favorite games/activities (comma-separated)", value=profile["favorite_games"] or "")
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Save Personality", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_edit_personality", use_container_width=True)
    if submitted:
        data = dict(profile)
        data.update({
            "likes": likes, "dislikes": dislikes, "favorite_toys": favorite_toys,
            "favorite_foods": favorite_foods, "foods_to_avoid": foods_to_avoid,
            "favorite_games": favorite_games,
        })
        update_profile(profile_id, data)
        queue_toast("Personality updated.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


# ============================================================
# Friends
# ============================================================

_ADD_NEW_FRIEND_OPTION = "✏️ Someone new (not in Pawfolio)"


@st.dialog("Add friend")
def _add_friend_dialog(profile_id):
    # Which-kind-of-friend lives outside the form so picking an existing pup can swap
    # the name/birthday fields for a simple confirmation line, the same reactive
    # pattern used for Profile type on the Identity dialog.
    already_linked = {f["friend_profile_id"] for f in get_friends(profile_id) if f["friend_profile_id"]}
    candidates = [p for p in get_all_profiles() if p["id"] != profile_id and p["id"] not in already_linked]
    choice_labels = [_ADD_NEW_FRIEND_OPTION] + [p["name"] for p in candidates]
    choice_index = st.selectbox(
        "Who's this friend?", options=range(len(choice_labels)), format_func=lambda i: choice_labels[i]
    )

    with st.form("add_friend_form_dialog", clear_on_submit=True):
        if choice_index == 0:
            fname = st.text_input("Friend's name")
            fbday = st.date_input("Friend's birthday (optional)", value=None)
        else:
            st.caption(f"This links to **{candidates[choice_index - 1]['name']}**'s existing Pawfolio profile.")
            fname, fbday = None, None
        fnotes = st.text_area("Notes")
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add friend", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_friend", use_container_width=True)
    if submitted:
        if choice_index == 0:
            if fname:
                add_friend(profile_id, fname, fbday.isoformat() if fbday else None, fnotes)
                queue_toast("Friend added.", icon="✅")
                st.rerun()
            else:
                st.warning("Friend's name is required.")
        else:
            chosen = candidates[choice_index - 1]
            add_friend(profile_id, chosen["name"], None, fnotes, friend_profile_id=chosen["id"])
            queue_toast(f"{chosen['name']} added as a friend.", icon="✅")
            st.rerun()
    if cancelled:
        st.rerun()


@st.dialog("Edit friend")
def _edit_friend_dialog(f, profile_name):
    is_linked = bool(f["friend_profile_id"])
    display_name = f["linked_name"] if is_linked else f["friend_name"]

    if is_linked:
        st.caption(f"🔗 Linked to **{display_name}**'s Pawfolio profile — name and birthday follow that profile.")
        if st.button("View their profile →", key=f"goto_friend_{f['id']}", use_container_width=True):
            st.session_state["selected_profile_id"] = f["friend_profile_id"]
            st.switch_page("views/profile_detail.py")
        with st.form(f"edit_friend_dialog_{f['id']}"):
            fnotes = st.text_area("Notes", value=f["notes"] or "")
            c1, c2, c3 = st.columns(3)
            save = c1.form_submit_button("Save", use_container_width=True)
            remove = c2.form_submit_button("Remove", key=f"delete_friend_{f['id']}", use_container_width=True)
            cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_friend_{f['id']}", use_container_width=True)
        if save:
            update_friend(f["id"], f["friend_name"], f["friend_birthday"], fnotes)
            queue_toast("Friend updated.", icon="✅")
            st.rerun()
        if remove:
            request_delete(f"**{display_name}** from {profile_name}'s friends", lambda fid=f["id"]: delete_friend(fid), "Friend removed.")
        if cancel:
            st.rerun()
    else:
        with st.form(f"edit_friend_dialog_{f['id']}"):
            fname = st.text_input("Friend's name", value=f["friend_name"])
            fbday_val = date.fromisoformat(f["friend_birthday"]) if f["friend_birthday"] else None
            fbday = st.date_input("Friend's birthday (optional)", value=fbday_val)
            fnotes = st.text_area("Notes", value=f["notes"] or "")
            c1, c2, c3 = st.columns(3)
            save = c1.form_submit_button("Save", use_container_width=True)
            remove = c2.form_submit_button("Delete", key=f"delete_friend_{f['id']}", use_container_width=True)
            cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_friend_{f['id']}", use_container_width=True)
        if save:
            update_friend(f["id"], fname, fbday.isoformat() if fbday else None, fnotes)
            queue_toast("Friend updated.", icon="✅")
            st.rerun()
        if remove:
            request_delete(f"**{f['friend_name']}** from {profile_name}'s friends", lambda fid=f["id"]: delete_friend(fid), "Friend deleted.")
        if cancel:
            st.rerun()


# ============================================================
# Siblings
# ============================================================

@st.dialog("Add sibling")
def _add_sibling_dialog(profile_id):
    existing_ids = {s["sibling_id"] for s in get_siblings(profile_id)}
    other_profiles = [p for p in get_all_profiles() if p["id"] != profile_id]
    candidates = [p for p in other_profiles if p["id"] not in existing_ids]
    if not candidates:
        if other_profiles:
            st.caption("Every other pup in Pawfolio is already linked as a sibling.")
        else:
            st.caption("Add another pup to Pawfolio first — siblings both need their own profile here.")
        if st.button("Close", key="cancel_add_sibling", use_container_width=True):
            st.rerun()
        return
    choice_index = st.selectbox(
        "Which pup is a sibling?", options=range(len(candidates)), format_func=lambda i: candidates[i]["name"]
    )
    c1, c2 = st.columns(2)
    submitted = c1.button("Add sibling", key="confirm_add_sibling", use_container_width=True)
    cancelled = c2.button("Cancel", key="cancel_add_sibling", use_container_width=True)
    if submitted:
        chosen = candidates[choice_index]
        add_sibling(profile_id, chosen["id"])
        queue_toast(f"{chosen['name']} added as a sibling.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


# ============================================================
# Baths
# ============================================================

@st.dialog("Add bath record")
def _add_bath_dialog(profile_id):
    with st.form("add_bath_form_dialog", clear_on_submit=True):
        bdate = st.date_input("Last bath date", value=date.today())
        bdue = st.date_input("Next due date", value=None)
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add bath record", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_bath", use_container_width=True)
    if submitted:
        add_bath(profile_id, bdate.isoformat(), bdue.isoformat() if bdue else None)
        queue_toast("Bath record added.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


@st.dialog("Edit bath record")
def _edit_bath_dialog(b):
    with st.form(f"edit_bath_dialog_{b['id']}"):
        bdate = st.date_input("Last bath date", value=date.fromisoformat(b["bath_date"]) if b["bath_date"] else None)
        bdue = st.date_input("Next due date", value=date.fromisoformat(b["next_due_date"]) if b["next_due_date"] else None)
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", use_container_width=True)
        remove = c2.form_submit_button("Delete", key=f"delete_bath_{b['id']}", use_container_width=True)
        cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_bath_{b['id']}", use_container_width=True)
    if save:
        update_bath(b["id"], bdate.isoformat() if bdate else None, bdue.isoformat() if bdue else None)
        queue_toast("Bath record updated.", icon="✅")
        st.rerun()
    if remove:
        request_delete(f"this bath record ({b['bath_date'] or 'unknown date'})", lambda bid=b["id"]: delete_bath(bid), "Bath record deleted.")
    if cancel:
        st.rerun()


# ============================================================
# Food refills
# ============================================================

@st.dialog("Add food refill record")
def _add_food_refill_dialog(profile_id):
    with st.form("add_refill_form_dialog", clear_on_submit=True):
        ftype = st.text_input("Food brand/type")
        flast = st.date_input("Last refill date", value=date.today())
        fnext = st.date_input("Next refill due date", value=None)
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add food refill record", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_refill", use_container_width=True)
    if submitted:
        add_food_refill(profile_id, ftype, flast.isoformat(), fnext.isoformat() if fnext else None)
        queue_toast("Food refill record added.", icon="✅")
        st.rerun()
    if cancelled:
        st.rerun()


@st.dialog("Edit food refill record")
def _edit_food_refill_dialog(fr):
    with st.form(f"edit_refill_dialog_{fr['id']}"):
        ftype = st.text_input("Food brand/type", value=fr["food_type"] or "")
        flast = st.date_input("Last refill date", value=date.fromisoformat(fr["last_refill_date"]) if fr["last_refill_date"] else None)
        fnext = st.date_input("Next refill due date", value=date.fromisoformat(fr["next_refill_date"]) if fr["next_refill_date"] else None)
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", use_container_width=True)
        remove = c2.form_submit_button("Delete", key=f"delete_refill_{fr['id']}", use_container_width=True)
        cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_refill_{fr['id']}", use_container_width=True)
    if save:
        update_food_refill(
            fr["id"], ftype,
            flast.isoformat() if flast else None,
            fnext.isoformat() if fnext else None,
        )
        queue_toast("Food refill record updated.", icon="✅")
        st.rerun()
    if remove:
        request_delete(f"this food refill record ({fr['food_type'] or 'food'})", lambda frid=fr["id"]: delete_food_refill(frid), "Food refill record deleted.")
    if cancel:
        st.rerun()


# ============================================================
# Boarding stays
# ============================================================

@st.dialog("Add boarding stay")
def _add_boarding_stay_dialog(profile_id):
    with st.form("add_stay_form_dialog", clear_on_submit=True):
        facility = st.text_input("Boarding facility name")
        check_in = st.date_input("Check-in date", value=date.today())
        check_out = st.date_input("Check-out date", value=None)
        bnotes = st.text_area("Notes")
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Add boarding stay", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key="cancel_add_stay", use_container_width=True)
    if submitted:
        if facility:
            add_boarding_stay(
                profile_id, facility, check_in.isoformat(),
                check_out.isoformat() if check_out else None, bnotes
            )
            queue_toast("Boarding stay added.", icon="✅")
            st.rerun()
        else:
            st.warning("Boarding facility name is required.")
    if cancelled:
        st.rerun()


@st.dialog("Edit boarding stay")
def _edit_boarding_stay_dialog(bs):
    with st.form(f"edit_stay_dialog_{bs['id']}"):
        facility = st.text_input("Boarding facility name", value=bs["facility_name"] or "")
        check_in = st.date_input("Check-in date", value=date.fromisoformat(bs["check_in_date"]) if bs["check_in_date"] else None)
        check_out = st.date_input("Check-out date", value=date.fromisoformat(bs["check_out_date"]) if bs["check_out_date"] else None)
        bnotes = st.text_area("Notes", value=bs["notes"] or "")
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("Save", use_container_width=True)
        remove = c2.form_submit_button("Delete", key=f"delete_stay_{bs['id']}", use_container_width=True)
        cancel = c3.form_submit_button("Cancel", key=f"cancel_edit_stay_{bs['id']}", use_container_width=True)
    if save:
        update_boarding_stay(
            bs["id"], facility,
            check_in.isoformat() if check_in else None,
            check_out.isoformat() if check_out else None,
            bnotes,
        )
        queue_toast("Boarding stay updated.", icon="✅")
        st.rerun()
    if remove:
        request_delete(f"this boarding stay at **{bs['facility_name'] or 'boarding'}**", lambda bsid=bs["id"]: delete_boarding_stay(bsid), "Boarding stay deleted.")
    if cancel:
        st.rerun()


# Surface any delete confirmation queued by a record's Edit dialog. Must run outside
# every other dialog on the page (Streamlit forbids nesting dialogs), so this sits at
# top level rather than being called from inside the dialog functions above.
render_pending_delete_dialog()

# Fire any save/add/delete confirmation queued just before the rerun that closed the
# dialog which triggered it (see queue_toast's docstring for why it can't fire inline).
render_queued_toast()


# ---------- Header ----------
# Identity fields (name/photo/dob/breed/type) and the profile-level delete both used
# to be their own tabs. Identity's tab ended up nearly empty once its fields moved
# into this header, and Delete Profile sitting in the tab strip gave an irreversible,
# rarely-used action the same visual weight as Health/Personality/Social/Care. Both
# now live as small icon controls right here instead — one tap from anywhere on the
# page, no tab spent on either.
header_cols = st.columns([1, 5, 0.6, 0.6])
with header_cols[0]:
    show_photo(profile["photo_path"], responsive=True, max_width=260)
with header_cols[1]:
    st.header(profile["name"])
    if profile["nickname"]:
        st.caption(f'aka "{profile["nickname"]}"')
    type_label = "🏠 My Dog" if profile["profile_type"] == "my_dog" else "🌳 Community Dog"
    st.subheader(type_label)
    st.write(calc_age_str(profile["dob"], bool(profile["dob_estimated"])))
    if profile["breed"]:
        st.write(f"Breed: {profile['breed']}")
    if profile["profile_type"] == "community_dog" and profile["hangout_location"]:
        st.write(f"📍 Usually hangs out at: {profile['hangout_location']}")
    st.caption(f"Added to Pawfolio on {profile['date_added']}")
    if profile["other_notes"]:
        with st.expander("📝 Other notes"):
            st.write(profile["other_notes"])
with header_cols[2]:
    if st.button("✏️", key="header_edit", help="Edit identity"):
        _edit_identity_dialog(profile_id, profile)
with header_cols[3]:
    # A popover here left itself visibly open behind the confirm dialog it triggered
    # (its own open/closed state doesn't auto-close just because a dialog opened on
    # top of it) — and with a single item in it, the menu wasn't earning its keep
    # anyway. A plain icon button opens the same confirm dialog with none of that.
    if st.button("🗑️", key="header_delete", help=f"Delete {profile['name']}'s profile"):
        _delete_profile_dialog(profile_id, profile["name"])

st.divider()

tab_health, tab_personality, tab_social, tab_care = st.tabs(
    ["🩺 Health", "🎾 Personality", "🐕 Social", "🧺 Care"]
)

# ================= HEALTH =================
with tab_health:
    vet_count = len(get_vets_for_profile(profile_id))
    with st.expander(f"🐾 Vets · {vet_count}", key="exp_health_vets"):
        render_vet_picker(profile_id, key_prefix=f"vetpicker_{profile_id}")

    vaccinations = get_vaccinations(profile_id)
    with st.expander(f"💉 Vaccinations · {len(vaccinations)}", key="exp_health_vacc"):
        if not vaccinations:
            st.caption("No vaccination records yet.")
        for v in vaccinations:
            _record_row(
                f"💉 **{v['vaccine_name']}** — next due {v['next_due_date'] or 'unset'}",
                f"editbtn_vacc_{v['id']}",
                lambda v=v: _edit_vaccination_dialog(v),
            )
        if st.button("➕ Add vaccination", key="btn_add_vacc", use_container_width=True):
            _add_vaccination_dialog(profile_id)

    with st.expander("📇 Chennai Corporation Registration", key="exp_health_reg"):
        st.caption(
            "Only relevant if this dog is registered with the Chennai Corporation's "
            "pet program — safe to leave blank otherwise."
        )
        st.write(
            f"Registration ID: **{profile['reg_id'] or '—'}** · "
            f"Last renewed: {profile['reg_last_renewed'] or '—'} · "
            f"Next due: {profile['reg_next_due'] or '—'}"
        )
        if st.button("✏️ Edit Registration", key="btn_edit_reg", use_container_width=True):
            _edit_registration_dialog(profile_id, profile)

    medications = get_medications(profile_id)
    with st.expander(f"💊 Medications · {len(medications)}", key="exp_health_med"):
        if not medications:
            st.caption("No medications on record.")
        for m in medications:
            status = "ongoing" if m["ongoing"] else f"ends {m['end_date'] or 'unset'}"
            _record_row(
                f"💊 **{m['med_name']}** — {status}",
                f"editbtn_med_{m['id']}",
                lambda m=m: _edit_medication_dialog(m),
            )
        if st.button("➕ Add medication", key="btn_add_med", use_container_width=True):
            _add_medication_dialog(profile_id)

    with st.expander("♻️ Spay / Neuter Status", key="exp_health_spay"):
        status_label = {"unknown": "Unknown", "yes": "Yes", "no": "No"}.get(profile["spay_neuter_status"] or "unknown", "Unknown")
        date_suffix = f" · Date: {profile['spay_neuter_date']}" if profile["spay_neuter_date"] else ""
        st.write(f"Status: **{status_label}**{date_suffix}")
        if st.button("✏️ Edit Spay/Neuter Status", key="btn_edit_spay", use_container_width=True):
            _edit_spay_neuter_dialog(profile_id, profile)

    surgeries = get_surgeries(profile_id)
    with st.expander(f"🩹 Surgeries · {len(surgeries)}", key="exp_health_surgery"):
        if not surgeries:
            st.caption("No surgeries on record.")
        for s in surgeries:
            _record_row(
                f"🩹 **{s['surgery_name']}** — {s['surgery_date'] or 'date unknown'}",
                f"editbtn_surgery_{s['id']}",
                lambda s=s: _edit_surgery_dialog(s),
            )
        if st.button("➕ Add surgery", key="btn_add_surgery", use_container_width=True):
            _add_surgery_dialog(profile_id)

    visits = get_vet_visits(profile_id)
    with st.expander(f"🩺 Vet Visit History · {len(visits)}", key="exp_health_visits"):
        if not visits:
            st.caption("No vet visits on record.")
        for vv in visits:
            _record_row(
                f"🩺 {vv['visit_date'] or 'date unknown'} — {vv['reason'] or 'visit'}",
                f"editbtn_visit_{vv['id']}",
                lambda vv=vv: _edit_vet_visit_dialog(vv),
            )
        if st.button("➕ Add vet visit", key="btn_add_visit", use_container_width=True):
            _add_vet_visit_dialog(profile_id)

# ================= PERSONALITY =================
with tab_personality:
    if st.button("✏️ Edit Personality", key="btn_edit_personality", use_container_width=True):
        _edit_personality_dialog(profile_id, profile)

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
        display_name = f["linked_name"] or f["friend_name"]
        bday = f["linked_dob"] if f["friend_profile_id"] else f["friend_birthday"]
        bday_suffix = f" — 🎂 {bday}" if bday else ""
        link_suffix = " 🔗" if f["friend_profile_id"] else ""
        _record_row(
            f"🐕 **{display_name}**{link_suffix}{bday_suffix}",
            f"editbtn_friend_{f['id']}",
            lambda f=f: _edit_friend_dialog(f, profile["name"]),
        )
    if st.button("➕ Add friend", key="btn_add_friend", use_container_width=True):
        _add_friend_dialog(profile_id)

    st.divider()
    st.subheader("Siblings")
    siblings = get_siblings(profile_id)
    if not siblings:
        st.caption("No siblings linked yet.")
    for s in siblings:
        with st.container(border=True):
            cols = st.columns([5, 1.3])
            cols[0].markdown(f"🦴 **{s['sibling_name']}**")
            # Removing a sibling link is low-stakes and fully reversible (neither profile
            # is touched, just the association) — same reasoning as "Unlink vet": no
            # confirm dialog, no danger styling.
            if cols[1].button("Remove", key=f"remove_sibling_{s['link_id']}", use_container_width=True):
                remove_sibling(s["link_id"])
                queue_toast(f"{s['sibling_name']} removed as a sibling.", icon="↩️")
                st.rerun()
    if st.button("➕ Add sibling", key="btn_add_sibling", use_container_width=True):
        _add_sibling_dialog(profile_id)

# ================= CARE & LOGISTICS =================
with tab_care:
    baths = get_baths(profile_id)
    with st.expander(f"🛁 Bath Tracking · {len(baths)}", key="exp_care_bath"):
        if not baths:
            st.caption("No bath records yet.")
        for b in baths:
            _record_row(
                f"🛁 Last bath {b['bath_date'] or 'unknown'} — next due {b['next_due_date'] or 'unset'}",
                f"editbtn_bath_{b['id']}",
                lambda b=b: _edit_bath_dialog(b),
            )
        if st.button("➕ Add bath record", key="btn_add_bath", use_container_width=True):
            _add_bath_dialog(profile_id)

    refills = get_food_refills(profile_id)
    with st.expander(f"🥣 Food Refill Tracking · {len(refills)}", key="exp_care_refill"):
        if not refills:
            st.caption("No food refill records yet.")
        for fr in refills:
            _record_row(
                f"🥣 {fr['food_type'] or 'food'} — next refill {fr['next_refill_date'] or 'unset'}",
                f"editbtn_refill_{fr['id']}",
                lambda fr=fr: _edit_food_refill_dialog(fr),
            )
        if st.button("➕ Add food refill record", key="btn_add_refill", use_container_width=True):
            _add_food_refill_dialog(profile_id)

    stays = get_boarding_stays(profile_id)
    with st.expander(f"🧳 Boarding History · {len(stays)}", key="exp_care_stay"):
        if not stays:
            st.caption("No boarding history yet.")
        for bs in stays:
            _record_row(
                f"🧳 {bs['facility_name'] or 'boarding'} — {bs['check_in_date'] or '?'} to {bs['check_out_date'] or '?'}",
                f"editbtn_stay_{bs['id']}",
                lambda bs=bs: _edit_boarding_stay_dialog(bs),
            )
        if st.button("➕ Add boarding stay", key="btn_add_stay", use_container_width=True):
            _add_boarding_stay_dialog(profile_id)
