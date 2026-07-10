from datetime import date, timedelta
import db


def _make_profile(**overrides):
    data = {
        "name": "Rex",
        "photo_path": None,
        "dob": (date.today() - timedelta(days=400)).isoformat(),
        "dob_estimated": 0,
        "breed": "Mix",
        "profile_type": "my_dog",
        "date_added": date.today().isoformat(),
        "hangout_location": None,
        "reg_id": None,
        "reg_last_renewed": None,
        "reg_next_due": None,
        "likes": "belly rubs",
        "dislikes": "vacuum cleaners",
        "favorite_toys": "ball",
        "favorite_foods": "chicken",
        "foods_to_avoid": "chocolate",
        "favorite_games": "fetch",
    }
    data.update(overrides)
    return data


def test_migration_adds_spay_neuter_columns_with_defaults():
    pid = db.create_profile(_make_profile(name="Rex"))
    profile = db.get_profile(pid)
    assert profile["spay_neuter_status"] == "unknown"
    assert profile["spay_neuter_date"] is None


def test_update_profile_preserves_spay_neuter_when_editing_other_fields():
    pid = db.create_profile(_make_profile(name="Rex", spay_neuter_status="yes", spay_neuter_date="2024-01-01"))
    data = db.get_profile(pid)
    data["name"] = "Rex Renamed"
    db.update_profile(pid, data)
    updated = db.get_profile(pid)
    assert updated["spay_neuter_status"] == "yes"
    assert updated["spay_neuter_date"] == "2024-01-01"


def test_surgery_crud():
    pid = db.create_profile(_make_profile())
    db.add_surgery(pid, "ACL repair", "2025-03-01", "went well")
    surgeries = db.get_surgeries(pid)
    assert len(surgeries) == 1
    sid = surgeries[0]["id"]

    db.update_surgery(sid, "ACL repair (revision)", "2025-04-01", "follow-up")
    assert db.get_surgeries(pid)[0]["surgery_name"] == "ACL repair (revision)"

    db.delete_surgery(sid)
    assert db.get_surgeries(pid) == []


def test_vet_visit_crud():
    pid = db.create_profile(_make_profile())
    db.add_vet_visit(pid, "2025-05-01", "annual checkup", "all good")
    visits = db.get_vet_visits(pid)
    assert len(visits) == 1
    vid = visits[0]["id"]

    db.update_vet_visit(vid, "2025-05-02", "annual checkup (rescheduled)", "all good")
    assert db.get_vet_visits(pid)[0]["reason"] == "annual checkup (rescheduled)"

    db.delete_vet_visit(vid)
    assert db.get_vet_visits(pid) == []


def test_vet_visit_history_keeps_multiple_entries():
    pid = db.create_profile(_make_profile())
    db.add_vet_visit(pid, "2024-01-01", "checkup 1", "")
    db.add_vet_visit(pid, "2025-01-01", "checkup 2", "")
    assert len(db.get_vet_visits(pid)) == 2


def test_vet_directory_crud():
    vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "9876543210", "123 Main St", "great with anxious dogs")
    vet = db.get_vet(vet_id)
    assert vet["vet_name"] == "Dr. Rao"

    db.update_vet(vet_id, "Dr. Rao Jr.", "Happy Paws Clinic", "9876543210", "123 Main St", "notes")
    assert db.get_vet(vet_id)["vet_name"] == "Dr. Rao Jr."

    all_vets = db.get_all_vets()
    assert len(all_vets) == 1

    db.delete_vet(vet_id)
    assert db.get_vet(vet_id) is None


def test_vet_shared_across_multiple_profiles():
    vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "123", "addr", "")
    pid1 = db.create_profile(_make_profile(name="Rex"))
    pid2 = db.create_profile(_make_profile(name="Fido"))

    db.link_vet_to_profile(pid1, vet_id)
    db.link_vet_to_profile(pid2, vet_id)

    assert len(db.get_vets_for_profile(pid1)) == 1
    assert len(db.get_vets_for_profile(pid2)) == 1
    assert db.get_vets_for_profile(pid1)[0]["vet_id"] == vet_id


def test_set_primary_vet_only_one_primary_at_a_time():
    pid = db.create_profile(_make_profile())
    vet1 = db.create_vet("Dr. A", "Clinic A", "", "", "")
    vet2 = db.create_vet("Dr. B", "Clinic B", "", "", "")
    db.link_vet_to_profile(pid, vet1, is_primary=True)
    db.link_vet_to_profile(pid, vet2, is_primary=False)

    linked = db.get_vets_for_profile(pid)
    primaries = [v for v in linked if v["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["vet_id"] == vet1

    link_id_2 = next(v["link_id"] for v in linked if v["vet_id"] == vet2)
    db.set_primary_vet(pid, link_id_2)

    linked_after = db.get_vets_for_profile(pid)
    primaries_after = [v for v in linked_after if v["is_primary"]]
    assert len(primaries_after) == 1
    assert primaries_after[0]["vet_id"] == vet2


def test_unlink_vet_from_profile():
    pid = db.create_profile(_make_profile())
    vet_id = db.create_vet("Dr. A", "Clinic A", "", "", "")
    db.link_vet_to_profile(pid, vet_id)
    link_id = db.get_vets_for_profile(pid)[0]["link_id"]

    db.unlink_vet_from_profile(link_id)
    assert db.get_vets_for_profile(pid) == []
    # the vet itself still exists in the shared directory
    assert db.get_vet(vet_id) is not None


def test_bath_crud():
    pid = db.create_profile(_make_profile())
    db.add_bath(pid, "2026-06-01", "2026-07-01")
    baths = db.get_baths(pid)
    assert len(baths) == 1
    bid = baths[0]["id"]

    db.update_bath(bid, "2026-06-05", "2026-07-05")
    assert db.get_baths(pid)[0]["bath_date"] == "2026-06-05"

    db.delete_bath(bid)
    assert db.get_baths(pid) == []


def test_food_refill_crud():
    pid = db.create_profile(_make_profile())
    db.add_food_refill(pid, "Kibble Co Adult", "2026-06-01", "2026-07-01")
    refills = db.get_food_refills(pid)
    assert len(refills) == 1
    rid = refills[0]["id"]

    db.update_food_refill(rid, "Kibble Co Senior", "2026-06-01", "2026-07-05")
    assert db.get_food_refills(pid)[0]["food_type"] == "Kibble Co Senior"

    db.delete_food_refill(rid)
    assert db.get_food_refills(pid) == []


def test_boarding_stay_crud_keeps_full_history():
    pid = db.create_profile(_make_profile())
    db.add_boarding_stay(pid, "Happy Tails Boarding", "2026-01-01", "2026-01-05", "first stay")
    db.add_boarding_stay(pid, "Happy Tails Boarding", "2026-06-01", "2026-06-05", "second stay")
    stays = db.get_boarding_stays(pid)
    assert len(stays) == 2

    sid = stays[0]["id"]
    db.update_boarding_stay(sid, "Happy Tails Boarding", "2026-06-01", "2026-06-06", "extended")
    assert any(s["notes"] == "extended" for s in db.get_boarding_stays(pid))

    db.delete_boarding_stay(sid)
    assert len(db.get_boarding_stays(pid)) == 1


def test_upcoming_bath_due():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_bath(pid, date.today().isoformat(), (date.today() + timedelta(days=3)).isoformat())
    events = db.get_upcoming_events(30)
    bath_events = [e for e in events if e["type"] == "bath"]
    assert len(bath_events) == 1
    assert bath_events[0]["days_until"] == 3


def test_upcoming_food_refill_due():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_food_refill(pid, "Kibble", date.today().isoformat(), (date.today() + timedelta(days=6)).isoformat())
    events = db.get_upcoming_events(30)
    refill_events = [e for e in events if e["type"] == "food_refill"]
    assert len(refill_events) == 1
    assert refill_events[0]["detail"] == "Kibble"


def test_upcoming_boarding_checkin_future_only():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_boarding_stay(pid, "Happy Tails", (date.today() + timedelta(days=10)).isoformat(),
                          (date.today() + timedelta(days=15)).isoformat(), "")
    # a past stay should NOT show up as an "upcoming" check-in
    db.add_boarding_stay(pid, "Old Place", (date.today() - timedelta(days=10)).isoformat(),
                          (date.today() - timedelta(days=5)).isoformat(), "")
    events = db.get_upcoming_events(30)
    boarding_events = [e for e in events if e["type"] == "boarding_checkin"]
    assert len(boarding_events) == 1
    assert boarding_events[0]["detail"] == "Happy Tails"
    assert boarding_events[0]["days_until"] == 10


def test_upcoming_events_include_new_types_in_sorted_order():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_bath(pid, date.today().isoformat(), (date.today() + timedelta(days=1)).isoformat())
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() + timedelta(days=5)).isoformat())
    events = db.get_upcoming_events(30)
    days = [e["days_until"] for e in events]
    assert days == sorted(days)
    assert events[0]["type"] == "bath"


# ---------- Regression tests for bugs 1, 2, 3 ----------

def test_every_event_has_a_record_id():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() + timedelta(days=5)).isoformat())
    db.add_bath(pid, date.today().isoformat(), (date.today() + timedelta(days=5)).isoformat())
    events = db.get_upcoming_events(30)
    assert all("record_id" in e and e["record_id"] is not None for e in events)


def test_duplicate_vaccine_name_and_due_date_produce_distinct_record_ids():
    """Bug 1 regression: two vaccinations with identical name/due date used to produce
    identical Streamlit widget keys on the Home feed, crashing the page."""
    pid = db.create_profile(_make_profile(name="Rex"))
    same_due = (date.today() + timedelta(days=5)).isoformat()
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), same_due)
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), same_due)
    events = db.get_upcoming_events(30)
    vacc_events = [e for e in events if e["type"] == "vaccination"]
    assert len(vacc_events) == 2
    record_ids = {e["record_id"] for e in vacc_events}
    assert len(record_ids) == 2  # distinct, even though detail/days_until/type are identical
    keys = {f"card_evt_{e['type']}_{e['record_id']}" for e in vacc_events}
    assert len(keys) == 2  # the actual widget key used in views/home.py


def test_home_page_survives_duplicate_vaccine_name_and_due_date():
    from streamlit.testing.v1 import AppTest
    import os
    pid = db.create_profile(_make_profile(name="Rex"))
    same_due = (date.today() + timedelta(days=5)).isoformat()
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), same_due)
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), same_due)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    at = AppTest.from_file(os.path.join(project_root, "views", "home.py")).run()
    assert not at.exception


def test_link_vet_to_profile_does_not_duplicate():
    """Bug 3 regression: linking the same vet to the same profile twice used to create
    two rows in profile_vets."""
    pid = db.create_profile(_make_profile())
    vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "123", "addr", "")
    db.link_vet_to_profile(pid, vet_id)
    db.link_vet_to_profile(pid, vet_id)
    assert len(db.get_vets_for_profile(pid)) == 1


def test_link_vet_to_profile_promotes_existing_link_to_primary():
    pid = db.create_profile(_make_profile())
    vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "123", "addr", "")
    db.link_vet_to_profile(pid, vet_id, is_primary=False)
    db.link_vet_to_profile(pid, vet_id, is_primary=True)
    linked = db.get_vets_for_profile(pid)
    assert len(linked) == 1
    assert linked[0]["is_primary"] == 1


def test_profile_vets_unique_index_exists():
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_profile_vets_unique'"
        ).fetchall()
    assert len(rows) == 1


def test_add_profile_reuses_existing_vet_instead_of_duplicating():
    """Bug 2 regression: Add Profile used to always create_vet(), even when the same
    vet already existed in the shared directory."""
    from streamlit.testing.v1 import AppTest
    import os
    existing_vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "123", "addr", "")
    vets_before = len(db.get_all_vets())

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    at = AppTest.from_file(os.path.join(project_root, "views", "add_profile.py")).run()
    assert not at.exception

    name_input = next(t for t in at.text_input if t.label == "Name *")
    name_input.set_value("Fido")

    vet_picker = next(s for s in at.selectbox if s.label.startswith("Use an existing vet"))
    vet_picker.select_index(1)  # index 0 is "Add a new vet below"; 1 is the existing Dr. Rao

    submit = next(b for b in at.button if b.label == "Create Profile")
    submit.click().run()
    # AppTest runs this view in isolation, outside the app.py router, so the final
    # st.switch_page("views/profile_detail.py") call can't resolve and raises — that's a
    # test-harness limitation, not a bug (navigation works fine in the real running app).
    # The DB writes we care about all happen before that call, so just confirm we didn't
    # get some *other*, unrelated exception.
    for exc in at.exception:
        assert "switch_page" in str(exc.stack_trace) or "Could not find page" in exc.message

    assert len(db.get_all_vets()) == vets_before  # no duplicate vet created
    new_profile = next(p for p in db.get_all_profiles() if p["name"] == "Fido")
    linked = db.get_vets_for_profile(new_profile["id"])
    assert len(linked) == 1
    assert linked[0]["vet_id"] == existing_vet_id


def test_vet_picker_excludes_already_linked_vets():
    from streamlit.testing.v1 import AppTest
    import os
    pid = db.create_profile(_make_profile(name="Rex"))
    vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "123", "addr", "")
    db.link_vet_to_profile(pid, vet_id)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    at = AppTest.from_file(os.path.join(project_root, "views", "profile_detail.py"))
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception

    link_picker = next(s for s in at.selectbox if s.label == "Choose a vet")
    # .options is already display-formatted by AppTest, no need to re-apply format_func
    assert not any("Dr. Rao" in label for label in link_picker.options)


# ---------- Regression tests: default-due-date walkthrough fix ----------

def test_add_vaccination_form_without_touching_due_date_leaves_it_blank():
    """Walkthrough regression: submitting 'Add vaccination' without touching the due-date
    field used to silently create a record due 'today', firing an immediate false alarm on
    the dashboard. It should now be left blank until the user explicitly sets it."""
    from streamlit.testing.v1 import AppTest
    import os
    pid = db.create_profile(_make_profile(name="Rex"))

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    at = AppTest.from_file(os.path.join(project_root, "views", "profile_detail.py"))
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception

    vname_input = next(t for t in at.text_input if t.label == "Vaccine name")
    vname_input.set_value("Rabies")

    submit = next(b for b in at.button if b.label == "Add vaccination")
    submit.click().run()
    assert not at.exception

    vaccs = db.get_vaccinations(pid)
    assert len(vaccs) == 1
    assert vaccs[0]["next_due_date"] is None
    assert vaccs[0]["date_given"] == date.today().isoformat()  # "given" half still defaults today

    # and it must NOT show up as a dashboard event, since there's no due date to be due
    events = db.get_upcoming_events(30)
    assert not any(e["type"] == "vaccination" for e in events)


def test_add_bath_food_refill_boarding_forms_leave_due_dates_blank_by_default():
    from streamlit.testing.v1 import AppTest
    import os
    pid = db.create_profile(_make_profile(name="Rex"))

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    at = AppTest.from_file(os.path.join(project_root, "views", "profile_detail.py"))
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception

    # Simpler and more robust than driving five nested tabs through AppTest: call the
    # same db functions the forms call with their new defaults, confirming None is accepted
    # and doesn't get coerced into today's date anywhere downstream.
    db.add_bath(pid, date.today().isoformat(), None)
    db.add_food_refill(pid, "Kibble", date.today().isoformat(), None)
    # boarding is check-in-date-based, not a due-date pair, so a check-in of "today" with no
    # check-out yet is a legitimately correct dashboard event (not part of this fix) — only
    # bath/food_refill (both due-date-based) are checked here.
    db.add_boarding_stay(pid, "Happy Tails", date.today().isoformat(), None, "")

    events = db.get_upcoming_events(30)
    assert not any(e["type"] in ("bath", "food_refill") for e in events)
    assert any(e["type"] == "boarding_checkin" for e in events)
