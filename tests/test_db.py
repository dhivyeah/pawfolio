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


def test_create_and_get_profile():
    pid = db.create_profile(_make_profile(name="Rex"))
    profile = db.get_profile(pid)
    assert profile["name"] == "Rex"
    assert profile["profile_type"] == "my_dog"


def test_get_all_profiles_filters_by_type():
    db.create_profile(_make_profile(name="Rex", profile_type="my_dog"))
    db.create_profile(_make_profile(name="Fido", profile_type="community_dog"))
    assert len(db.get_all_profiles()) == 2
    assert [p["name"] for p in db.get_all_profiles(profile_type="my_dog")] == ["Rex"]
    assert [p["name"] for p in db.get_all_profiles(profile_type="community_dog")] == ["Fido"]


def test_update_profile():
    pid = db.create_profile(_make_profile(name="Rex"))
    data = db.get_profile(pid)
    data["name"] = "Rex Updated"
    data["breed"] = "Beagle"
    db.update_profile(pid, data)
    assert db.get_profile(pid)["name"] == "Rex Updated"
    assert db.get_profile(pid)["breed"] == "Beagle"


def test_delete_profile_cascades_children():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), date.today().isoformat())
    db.add_medication(pid, "Antibiotic", "1 tab", "daily", date.today().isoformat(), None, True)
    db.add_friend(pid, "Buddy", None, "met at the park")

    db.delete_profile(pid)

    assert db.get_profile(pid) is None
    assert db.get_vaccinations(pid) == []
    assert db.get_medications(pid) == []
    assert db.get_friends(pid) == []


def test_vaccination_crud():
    pid = db.create_profile(_make_profile())
    db.add_vaccination(pid, "Rabies", "2026-01-01", "2027-01-01")
    vaccs = db.get_vaccinations(pid)
    assert len(vaccs) == 1
    vid = vaccs[0]["id"]

    db.update_vaccination(vid, "Rabies Booster", "2026-02-01", "2027-02-01")
    updated = db.get_vaccinations(pid)[0]
    assert updated["vaccine_name"] == "Rabies Booster"

    db.delete_vaccination(vid)
    assert db.get_vaccinations(pid) == []


def test_medication_crud():
    pid = db.create_profile(_make_profile())
    db.add_medication(pid, "Antibiotic", "1 tab", "daily", "2026-01-01", "2026-01-10", False)
    meds = db.get_medications(pid)
    assert len(meds) == 1
    mid = meds[0]["id"]

    db.update_medication(mid, "Antibiotic", "2 tabs", "daily", "2026-01-01", None, True)
    updated = db.get_medications(pid)[0]
    assert updated["dosage"] == "2 tabs"
    assert updated["ongoing"] == 1

    db.delete_medication(mid)
    assert db.get_medications(pid) == []


def test_friend_crud():
    pid = db.create_profile(_make_profile())
    db.add_friend(pid, "Buddy", "2020-05-01", "met at the park")
    friends = db.get_friends(pid)
    assert len(friends) == 1
    fid = friends[0]["id"]

    db.update_friend(fid, "Buddy Jr.", "2021-05-01", "still friends")
    updated = db.get_friends(pid)[0]
    assert updated["friend_name"] == "Buddy Jr."

    db.delete_friend(fid)
    assert db.get_friends(pid) == []


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


def test_upcoming_vaccination_due_soon():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() + timedelta(days=5)).isoformat())
    events = db.get_upcoming_events(30)
    assert any(e["type"] == "vaccination" and e["days_until"] == 5 for e in events)


def test_upcoming_vaccination_overdue():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() - timedelta(days=3)).isoformat())
    events = db.get_upcoming_events(30)
    match = next(e for e in events if e["type"] == "vaccination")
    assert match["days_until"] == -3


def test_upcoming_medication_ending_excludes_ongoing():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_medication(pid, "Antibiotic", "1 tab", "daily", date.today().isoformat(),
                       (date.today() + timedelta(days=2)).isoformat(), False)
    db.add_medication(pid, "Forever Med", "1 tab", "daily", date.today().isoformat(), None, True)
    events = db.get_upcoming_events(30)
    med_events = [e for e in events if e["type"] == "medication"]
    assert len(med_events) == 1
    assert med_events[0]["detail"] == "Antibiotic"


def test_upcoming_registration_renewal():
    pid = db.create_profile(_make_profile(name="Rex", reg_id="CHN123",
                                           reg_next_due=(date.today() + timedelta(days=10)).isoformat()))
    events = db.get_upcoming_events(30)
    assert any(e["type"] == "registration" and e["days_until"] == 10 for e in events)


def test_upcoming_own_birthday():
    upcoming_bday = date.today() + timedelta(days=7)
    dob = upcoming_bday.replace(year=upcoming_bday.year - 3).isoformat()
    pid = db.create_profile(_make_profile(name="Rex", dob=dob))
    events = db.get_upcoming_events(30)
    bday_events = [e for e in events if e["type"] == "own_birthday"]
    assert len(bday_events) == 1
    assert bday_events[0]["turning"] == 3


def test_upcoming_friend_birthday():
    pid = db.create_profile(_make_profile(name="Rex"))
    upcoming_bday = date.today() + timedelta(days=4)
    db.add_friend(pid, "Buddy", upcoming_bday.replace(year=2019).isoformat(), "notes")
    events = db.get_upcoming_events(30)
    friend_events = [e for e in events if e["type"] == "friend_birthday"]
    assert len(friend_events) == 1
    assert friend_events[0]["detail"] == "Buddy"


def test_upcoming_events_respects_horizon():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_vaccination(pid, "Rabies", date.today().isoformat(), (date.today() + timedelta(days=90)).isoformat())
    events = db.get_upcoming_events(30)
    assert events == []


def test_upcoming_events_sorted_soonest_first():
    pid = db.create_profile(_make_profile(name="Rex"))
    db.add_vaccination(pid, "Later Shot", date.today().isoformat(), (date.today() + timedelta(days=20)).isoformat())
    db.add_vaccination(pid, "Sooner Shot", date.today().isoformat(), (date.today() + timedelta(days=2)).isoformat())
    events = db.get_upcoming_events(30)
    days = [e["days_until"] for e in events]
    assert days == sorted(days)


def test_get_recently_added_profiles():
    db.create_profile(_make_profile(name="Recent", date_added=date.today().isoformat()))
    db.create_profile(_make_profile(name="Old", date_added=(date.today() - timedelta(days=30)).isoformat()))
    recent = db.get_recently_added_profiles(days=7)
    assert [p["name"] for p in recent] == ["Recent"]


def test_get_recently_added_profiles_empty_when_none_recent():
    db.create_profile(_make_profile(name="Old", date_added=(date.today() - timedelta(days=30)).isoformat()))
    assert db.get_recently_added_profiles(days=7) == []
