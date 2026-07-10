import os
from datetime import date, timedelta
from streamlit.testing.v1 import AppTest
import db

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _path(relative):
    return os.path.join(PROJECT_ROOT, relative)


def test_app_home_loads_without_exception():
    at = AppTest.from_file(_path("app.py")).run()
    assert not at.exception
    assert at.title[0].value == "🐾 Pawfolio"


def test_top_nav_has_only_home_and_profiles_no_add_profile_button():
    at = AppTest.from_file(_path("app.py")).run()
    button_keys = [b.key for b in at.button]
    assert "nav_home" in button_keys
    assert "nav_profiles" in button_keys
    # "New Profile" must not be a persistent nav item — only a button on the Home page itself
    assert "nav_add_profile" not in button_keys
    page_link_labels = [pl.label for pl in at.get("page_link")]
    assert "New Profile" not in page_link_labels
    assert "Profile" not in page_link_labels  # profile detail must not be a nav destination either


def test_home_page_has_new_profile_button():
    at = AppTest.from_file(_path("app.py")).run()
    button_keys = [b.key for b in at.button]
    assert "home_add_profile" in button_keys


def test_all_profiles_view_loads_without_exception():
    at = AppTest.from_file(_path("views/all_profiles.py")).run()
    assert not at.exception


def test_add_profile_view_loads_without_exception():
    at = AppTest.from_file(_path("views/add_profile.py")).run()
    assert not at.exception


def test_profile_detail_without_selection_shows_picker():
    pid = db.create_profile({
        "name": "Rex", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    })
    at = AppTest.from_file(_path("views/profile_detail.py")).run()
    assert not at.exception


def test_profile_detail_with_selection_shows_profile():
    pid = db.create_profile({
        "name": "Rex", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    })
    at = AppTest.from_file(_path("views/profile_detail.py"))
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception
    headers = [h.value for h in at.header]
    assert "Rex" in headers


def test_home_shows_new_pack_member_card_for_recent_profile():
    db.create_profile({
        "name": "Newbie", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    })
    at = AppTest.from_file(_path("views/home.py")).run()
    assert not at.exception
    markdown_text = " ".join(m.value for m in at.markdown)
    assert "Newbie" in markdown_text


def test_home_empty_state_when_nothing_upcoming():
    at = AppTest.from_file(_path("views/home.py")).run()
    assert not at.exception
    infos = [i.value for i in at.info]
    assert len(infos) == 1


def test_all_profiles_has_new_profile_button():
    at = AppTest.from_file(_path("views/all_profiles.py")).run()
    assert not at.exception
    button_keys = [b.key for b in at.button]
    assert "all_profiles_add_profile" in button_keys


def _new_profile(name="Rex"):
    return db.create_profile({
        "name": name, "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    })


def test_profile_detail_shows_care_and_logistics_and_expanded_health_sections():
    pid = _new_profile()
    at = AppTest.from_file(_path("views/profile_detail.py"))
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception

    subheaders = [s.value for s in at.subheader]
    assert "Spay / Neuter Status" in subheaders
    assert "Surgeries" in subheaders
    assert "Vet Visit History" in subheaders
    assert "Vets" in subheaders
    assert "🛁 Bath Tracking" in subheaders
    assert "🥣 Food Refill Tracking" in subheaders
    assert "🧳 Boarding History" in subheaders


def test_profile_detail_delete_button_has_danger_key():
    pid = _new_profile()
    at = AppTest.from_file(_path("views/profile_detail.py"))
    at.session_state["selected_profile_id"] = pid
    at.run()
    button_keys = [b.key for b in at.button]
    assert "delete_profile" in button_keys


def test_profile_detail_shows_linked_vet():
    pid = _new_profile()
    vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "123", "addr", "notes")
    db.link_vet_to_profile(pid, vet_id, is_primary=True)

    at = AppTest.from_file(_path("views/profile_detail.py"))
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception

    expander_labels = [e.label for e in at.expander]
    assert any("Dr. Rao" in label for label in expander_labels)


def test_add_profile_form_includes_care_and_logistics_section():
    at = AppTest.from_file(_path("views/add_profile.py")).run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert "🧺 Care & Logistics" in subheaders
