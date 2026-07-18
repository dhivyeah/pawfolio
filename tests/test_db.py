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


def test_create_and_get_profile(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    profile = db.get_profile(pid, owner_id)
    assert profile["name"] == "Rex"
    assert profile["profile_type"] == "my_dog"


def test_get_all_profiles_filters_by_type(owner_id):
    db.create_profile(_make_profile(name="Rex", profile_type="my_dog"), owner_id)
    db.create_profile(_make_profile(name="Fido", profile_type="community_dog"), owner_id)
    assert len(db.get_all_profiles(owner_id)) == 2
    assert [p["name"] for p in db.get_all_profiles(owner_id, profile_type="my_dog")] == ["Rex"]
    assert [p["name"] for p in db.get_all_profiles(owner_id, profile_type="community_dog")] == ["Fido"]


def test_get_all_profiles_excludes_other_owners(owner_id):
    """Phase 4: the core promise of owner scoping -- a different owner's profiles never
    show up, no matter how they're queried."""
    other_owner = "11111111-1111-1111-1111-111111111111"
    db.create_profile(_make_profile(name="Mine"), owner_id)
    db.create_profile(_make_profile(name="TheirsNotMine"), other_owner)
    assert [p["name"] for p in db.get_all_profiles(owner_id)] == ["Mine"]
    assert [p["name"] for p in db.get_all_profiles(other_owner)] == ["TheirsNotMine"]


def test_update_profile(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    data = db.get_profile(pid, owner_id)
    data["name"] = "Rex Updated"
    data["breed"] = "Beagle"
    db.update_profile(pid, data, owner_id)
    assert db.get_profile(pid, owner_id)["name"] == "Rex Updated"
    assert db.get_profile(pid, owner_id)["breed"] == "Beagle"


def test_update_profile_ignores_other_owners_id(owner_id):
    other_owner = "22222222-2222-2222-2222-222222222222"
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    data = db.get_profile(pid, owner_id)
    data["name"] = "Hijacked"
    db.update_profile(pid, data, other_owner)
    assert db.get_profile(pid, owner_id)["name"] == "Rex"


def test_delete_profile_cascades_children(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), date.today().isoformat(), owner_id)
    db.add_medication(pid, "Antibiotic", "1 tab", "daily", date.today().isoformat(), None, True, owner_id)
    db.add_friend(pid, "Buddy", None, "met at the park", owner_id)

    db.delete_profile(pid, owner_id)

    assert db.get_profile(pid, owner_id) is None
    assert db.get_vaccinations(pid, owner_id) == []
    assert db.get_medications(pid, owner_id) == []
    assert db.get_friends(pid, owner_id) == []


def test_delete_profile_ignores_other_owners(owner_id):
    other_owner = "33333333-3333-3333-3333-333333333333"
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    db.delete_profile(pid, other_owner)
    assert db.get_profile(pid, owner_id) is not None


def test_vaccination_crud(owner_id):
    pid = db.create_profile(_make_profile(), owner_id)
    db.add_vaccination(pid, "Rabies", "2026-01-01", "2027-01-01", owner_id)
    vaccs = db.get_vaccinations(pid, owner_id)
    assert len(vaccs) == 1
    vid = vaccs[0]["id"]

    db.update_vaccination(vid, "Rabies Booster", "2026-02-01", "2027-02-01", owner_id)
    updated = db.get_vaccinations(pid, owner_id)[0]
    assert updated["vaccine_name"] == "Rabies Booster"

    db.delete_vaccination(vid, owner_id)
    assert db.get_vaccinations(pid, owner_id) == []


def test_medication_crud(owner_id):
    pid = db.create_profile(_make_profile(), owner_id)
    db.add_medication(pid, "Antibiotic", "1 tab", "daily", "2026-01-01", "2026-01-10", False, owner_id)
    meds = db.get_medications(pid, owner_id)
    assert len(meds) == 1
    mid = meds[0]["id"]

    db.update_medication(mid, "Antibiotic", "2 tabs", "daily", "2026-01-01", None, True, owner_id)
    updated = db.get_medications(pid, owner_id)[0]
    assert updated["dosage"] == "2 tabs"
    assert updated["ongoing"] == 1

    db.delete_medication(mid, owner_id)
    assert db.get_medications(pid, owner_id) == []


def test_friend_crud(owner_id):
    pid = db.create_profile(_make_profile(), owner_id)
    db.add_friend(pid, "Buddy", "2020-05-01", "met at the park", owner_id)
    friends = db.get_friends(pid, owner_id)
    assert len(friends) == 1
    fid = friends[0]["id"]

    db.update_friend(fid, "Buddy Jr.", "2021-05-01", "still friends", owner_id)
    updated = db.get_friends(pid, owner_id)[0]
    assert updated["friend_name"] == "Buddy Jr."

    db.delete_friend(fid, owner_id)
    assert db.get_friends(pid, owner_id) == []


def test_calc_age_str_known_dob():
    dob = (date.today() - timedelta(days=400)).isoformat()
    result = db.calc_age_str(dob, False)
    assert "y" in result and "old" in result
    assert not result.startswith("~")


def test_calc_age_str_estimated():
    dob = (date.today() - timedelta(days=400)).isoformat()
    result = db.calc_age_str(dob, True)
    assert result.startswith("~")


def test_calc_age_str_unknown():
    assert db.calc_age_str(None, False) == "Unknown age"


def test_upcoming_vaccination_due_soon(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() + timedelta(days=5)).isoformat(), owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    assert any(e["type"] == "vaccination" and e["days_until"] == 5 for e in events)


def test_upcoming_events_excludes_other_owners(owner_id):
    other_owner = "44444444-4444-4444-4444-444444444444"
    db.create_profile(_make_profile(name="TheirsNotMine"), other_owner)
    other_pid = db.get_all_profiles(other_owner)[0]["id"]
    db.add_vaccination(other_pid, "Rabies", date.today().isoformat(), (date.today() + timedelta(days=5)).isoformat(), other_owner)
    events = db.get_upcoming_events(owner_id, 30)
    assert events == []


def test_upcoming_vaccination_overdue(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() - timedelta(days=3)).isoformat(), owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    match = next(e for e in events if e["type"] == "vaccination")
    assert match["days_until"] == -3


def test_upcoming_medication_ending_excludes_ongoing(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    db.add_medication(pid, "Antibiotic", "1 tab", "daily", date.today().isoformat(),
                       (date.today() + timedelta(days=2)).isoformat(), False, owner_id)
    db.add_medication(pid, "Forever Med", "1 tab", "daily", date.today().isoformat(), None, True, owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    med_events = [e for e in events if e["type"] == "medication"]
    assert len(med_events) == 1
    assert med_events[0]["detail"] == "Antibiotic"


def test_upcoming_registration_renewal(owner_id):
    pid = db.create_profile(_make_profile(name="Rex", reg_id="CHN123",
                                           reg_next_due=(date.today() + timedelta(days=10)).isoformat()), owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    assert any(e["type"] == "registration" and e["days_until"] == 10 for e in events)


def test_upcoming_own_birthday(owner_id):
    upcoming_bday = date.today() + timedelta(days=7)
    dob = upcoming_bday.replace(year=upcoming_bday.year - 3).isoformat()
    pid = db.create_profile(_make_profile(name="Rex", dob=dob), owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    bday_events = [e for e in events if e["type"] == "own_birthday"]
    assert len(bday_events) == 1
    assert bday_events[0]["turning"] == 3


def test_upcoming_friend_birthday(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    upcoming_bday = date.today() + timedelta(days=4)
    db.add_friend(pid, "Buddy", upcoming_bday.replace(year=2019).isoformat(), "notes", owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    friend_events = [e for e in events if e["type"] == "friend_birthday"]
    assert len(friend_events) == 1
    assert friend_events[0]["detail"] == "Buddy"


def test_upcoming_events_respects_horizon(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() + timedelta(days=90)).isoformat(), owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    assert events == []


def test_upcoming_events_sorted_soonest_first(owner_id):
    pid = db.create_profile(_make_profile(name="Rex"), owner_id)
    db.add_vaccination(pid, "Later Shot", date.today().isoformat(), (date.today() + timedelta(days=20)).isoformat(), owner_id)
    db.add_vaccination(pid, "Sooner Shot", date.today().isoformat(), (date.today() + timedelta(days=2)).isoformat(), owner_id)
    events = db.get_upcoming_events(owner_id, 30)
    days = [e["days_until"] for e in events]
    assert days == sorted(days)


def test_get_recently_added_profiles(owner_id):
    db.create_profile(_make_profile(name="Recent", date_added=date.today().isoformat()), owner_id)
    db.create_profile(_make_profile(name="Old", date_added=(date.today() - timedelta(days=30)).isoformat()), owner_id)
    recent = db.get_recently_added_profiles(owner_id, days=7)
    assert [p["name"] for p in recent] == ["Recent"]


def test_get_recently_added_profiles_empty_when_none_recent(owner_id):
    db.create_profile(_make_profile(name="Old", date_added=(date.today() - timedelta(days=30)).isoformat()), owner_id)
    assert db.get_recently_added_profiles(owner_id, days=7) == []
