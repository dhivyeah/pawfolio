from voice import render_event_card, render_new_profile_card, EMPTY_STATE_MESSAGES


def _event(event_type, **overrides):
    base = {
        "type": event_type,
        "profile_name": "Rex",
        "profile_id": 1,
        "profile_type": "my_dog",
        "detail": "Rabies",
        "days_until": 5,
        "due_date": "2026-08-01",
    }
    base.update(overrides)
    return base


def test_render_vaccination_due_card():
    card = render_event_card(_event("vaccination", days_until=5))
    # 2026-07-19: templates no longer restate the dog's name in card["text"] --
    # the dashboard shows it separately as a bold header, so a template repeating
    # it here would make the same card say the name twice. profile_name is still
    # returned in the dict for callers (the dashboard's header, the email
    # digest) that need it themselves.
    assert card["profile_name"] == "Rex"
    assert "Rex" not in card["text"]
    assert "Rabies" in card["text"]
    assert card["tag"] == "in 5d"


def test_render_vaccination_overdue_card():
    card = render_event_card(_event("vaccination", days_until=-2))
    assert "overdue" in card["tag"]
    assert "Rex" not in card["text"]


def test_render_medication_card():
    card = render_event_card(_event("medication", detail="Antibiotic", days_until=1))
    assert "Antibiotic" in card["text"]
    assert "Rex" not in card["text"]
    assert card["tag"] == "⏰ tomorrow"


def test_render_registration_card():
    card = render_event_card(_event("registration", days_until=0))
    assert card["profile_name"] == "Rex"
    assert "Rex" not in card["text"]
    assert card["tag"] == "🚨 today"


def test_render_own_birthday_card():
    card = render_event_card(_event("own_birthday", turning=3, days_until=10))
    assert card["profile_name"] == "Rex"
    assert "Rex" not in card["text"]
    assert "3" in card["text"]


def test_render_own_birthday_card_missing_turning_falls_back():
    card = render_event_card(_event("own_birthday", turning=None, days_until=10))
    assert "??" in card["text"]


def test_render_friend_birthday_card():
    card = render_event_card(_event("friend_birthday", detail="Buddy", days_until=3))
    assert "Buddy" in card["text"]
    # Rex is the *profile's own* name here (redundant with the card header, so
    # removed from the template) -- Buddy is the friend's name, a different dog
    # entirely, which is real content the template still needs to say.
    assert card["profile_name"] == "Rex"
    assert "Rex" not in card["text"]


def test_render_new_profile_card_my_dog():
    text = render_new_profile_card({"name": "Rex", "profile_type": "my_dog"})
    assert "Rex" not in text
    assert text


def test_render_new_profile_card_community_dog():
    text = render_new_profile_card({"name": "Fido", "profile_type": "community_dog"})
    assert "Fido" not in text
    assert text


def test_render_bath_card():
    card = render_event_card(_event("bath", days_until=3))
    assert card["profile_name"] == "Rex"
    assert "Rex" not in card["text"]
    assert card["tag"] == "in 3d"


def test_render_food_refill_card():
    card = render_event_card(_event("food_refill", detail="Kibble Co", days_until=2))
    assert "Kibble Co" in card["text"]
    assert card["profile_name"] == "Rex"
    assert "Rex" not in card["text"]


def test_render_boarding_checkin_card():
    card = render_event_card(_event("boarding_checkin", detail="Happy Tails", days_until=7))
    assert "Happy Tails" in card["text"]
    assert card["profile_name"] == "Rex"
    assert "Rex" not in card["text"]


def test_empty_state_messages_present():
    assert len(EMPTY_STATE_MESSAGES) > 0
    assert all(isinstance(m, str) and m for m in EMPTY_STATE_MESSAGES)
