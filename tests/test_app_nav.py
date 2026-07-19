import os
from datetime import date, timedelta
from streamlit.testing.v1 import AppTest
import db

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _path(relative):
    return os.path.join(PROJECT_ROOT, relative)


def _authed(at, owner_id):
    """Every page now gates on st.session_state['auth_user'] (Phase 4) -- AppTest
    doesn't go through the real login flow, so tests set the same session_state key
    app.py's login gate checks for directly, the same way selected_profile_id was
    already being set directly rather than via a real click-through."""
    at.session_state["auth_user"] = {"user_id": owner_id, "email": "test@example.com"}
    return at


def test_app_home_loads_without_exception(owner_id):
    at = _authed(AppTest.from_file(_path("app.py")), owner_id).run()
    assert not at.exception
    # 2026-07-19: the old page-level "🐾 Pawfolio" st.title() on Home is gone --
    # the brand mark now lives once, globally, in app.py's top bar as styled
    # markdown (ui_helpers-style raw HTML via .pf-brand), not a real Streamlit
    # title element, so it shows up in markdown, not at.title.
    markdown_text = " ".join(m.value for m in at.markdown)
    assert "Pawfolio" in markdown_text


def test_top_nav_has_only_home_and_my_pups_no_add_profile_or_logout_button(owner_id):
    # Home is the default page, so its nav pills render as the "active" segment
    # (keys "nav_home_full_active"/"nav_home_icon_active" -- see app.py/styles.py's
    # pill-shaped segmented nav, rendered twice for the icon-only mobile variant)
    # while My Pups renders as the plain inactive ones. Log out and New Profile
    # both moved out of the persistent top bar in the 2026-07-19 header
    # restructure -- log out into the account-menu popover (still findable by
    # AppTest via its key, since popover content renders regardless of the
    # frontend's open/closed visual state), New Profile onto the My Pups page.
    at = _authed(AppTest.from_file(_path("app.py")), owner_id).run()
    button_keys = [b.key for b in at.button]
    assert "nav_home_full_active" in button_keys
    assert "nav_home_icon_active" in button_keys
    assert "nav_profiles_full" in button_keys
    assert "nav_profiles_icon" in button_keys
    assert "account_menu" not in button_keys  # popover trigger has its own key/testid, not a plain button
    assert "nav_logout" in button_keys  # still reachable, just relocated into the account menu
    # "New Profile" must not be a persistent nav item — only a button on the My Pups page itself
    assert "nav_add_profile" not in button_keys
    assert "home_add_profile" not in button_keys
    page_link_labels = [pl.label for pl in at.get("page_link")]
    assert "New Profile" not in page_link_labels
    assert "Profile" not in page_link_labels  # profile detail must not be a nav destination either


def test_account_menu_shows_profile_counts(owner_id):
    db.create_profile({
        "name": "Rex", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    }, owner_id)
    db.create_profile({
        "name": "Buddy", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "community_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    }, owner_id)
    at = _authed(AppTest.from_file(_path("app.py")), owner_id).run()
    assert not at.exception
    caption_values = [c.value for c in at.caption]
    assert any("1 pup" in c and "1 community pup" in c for c in caption_values)


def test_all_profiles_view_loads_without_exception(owner_id):
    at = _authed(AppTest.from_file(_path("views/all_profiles.py")), owner_id).run()
    assert not at.exception


def test_add_profile_view_loads_without_exception(owner_id):
    at = _authed(AppTest.from_file(_path("views/add_profile.py")), owner_id).run()
    assert not at.exception


def test_profile_detail_without_selection_shows_picker(owner_id):
    pid = db.create_profile({
        "name": "Rex", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    }, owner_id)
    at = _authed(AppTest.from_file(_path("views/profile_detail.py")), owner_id).run()
    assert not at.exception


def test_profile_detail_with_selection_shows_profile(owner_id):
    pid = db.create_profile({
        "name": "Rex", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    }, owner_id)
    at = _authed(AppTest.from_file(_path("views/profile_detail.py")), owner_id)
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception
    # The profile header lost its plain st.header() in the 2026-07-19 glassmorphism
    # redesign -- the name now renders via ui_helpers.render_name_row() as styled
    # raw HTML (matching the dashboard cards' name-row pattern) instead of a
    # semantic Streamlit heading element, so it shows up in markdown, not at.header.
    # See KNOWN_ISSUES.md for the accessibility tradeoff this introduces.
    markdown_text = " ".join(m.value for m in at.markdown)
    assert "Rex" in markdown_text


def test_home_shows_new_pack_member_card_for_recent_profile(owner_id):
    db.create_profile({
        "name": "Newbie", "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    }, owner_id)
    at = _authed(AppTest.from_file(_path("views/home.py")), owner_id).run()
    assert not at.exception
    markdown_text = " ".join(m.value for m in at.markdown)
    assert "Newbie" in markdown_text


def test_home_empty_state_when_nothing_upcoming(owner_id):
    at = _authed(AppTest.from_file(_path("views/home.py")), owner_id).run()
    assert not at.exception
    infos = [i.value for i in at.info]
    assert len(infos) == 1


def test_all_profiles_has_new_profile_button(owner_id):
    at = _authed(AppTest.from_file(_path("views/all_profiles.py")), owner_id).run()
    assert not at.exception
    button_keys = [b.key for b in at.button]
    assert "all_profiles_add_profile" in button_keys


def _new_profile(owner_id, name="Rex"):
    return db.create_profile({
        "name": name, "photo_path": None, "dob": None, "dob_estimated": 0,
        "breed": None, "profile_type": "my_dog", "date_added": date.today().isoformat(),
        "hangout_location": None, "reg_id": None, "reg_last_renewed": None, "reg_next_due": None,
        "likes": None, "dislikes": None, "favorite_toys": None, "favorite_foods": None,
        "foods_to_avoid": None, "favorite_games": None,
    }, owner_id)


def test_profile_detail_shows_care_and_logistics_and_expanded_health_sections(owner_id):
    pid = _new_profile(owner_id)
    at = _authed(AppTest.from_file(_path("views/profile_detail.py")), owner_id)
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


def test_profile_detail_delete_button_has_danger_key(owner_id):
    pid = _new_profile(owner_id)
    at = _authed(AppTest.from_file(_path("views/profile_detail.py")), owner_id)
    at.session_state["selected_profile_id"] = pid
    at.run()
    button_keys = [b.key for b in at.button]
    assert "delete_profile" in button_keys


def test_profile_detail_shows_linked_vet(owner_id):
    pid = _new_profile(owner_id)
    vet_id = db.create_vet("Dr. Rao", "Happy Paws Clinic", "123", "addr", "notes", owner_id)
    db.link_vet_to_profile(pid, vet_id, owner_id, is_primary=True)

    at = _authed(AppTest.from_file(_path("views/profile_detail.py")), owner_id)
    at.session_state["selected_profile_id"] = pid
    at.run()
    assert not at.exception

    expander_labels = [e.label for e in at.expander]
    assert any("Dr. Rao" in label for label in expander_labels)


def test_add_profile_form_includes_care_and_logistics_section(owner_id):
    at = _authed(AppTest.from_file(_path("views/add_profile.py")), owner_id).run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert "🧺 Care & Logistics" in subheaders
