"""Turns raw upcoming-event dicts into warm, funny, over-the-top wholesome 'posts'."""
import random


def _urgency_tag(days_until: int) -> str:
    if days_until < 0:
        return f"⚠️ {abs(days_until)}d overdue"
    if days_until == 0:
        return "🚨 today"
    if days_until == 1:
        return "⏰ tomorrow"
    return f"in {days_until}d"


# Every template below is written to stand alone with NO leading/embedded {name} --
# the dashboard card that renders this text always shows the dog's name separately
# as a bold header above it (ui_helpers.render_name_row), so a template restating
# the name here would make it read twice on the same card. {detail} (a vaccine/med
# name, a friend's name, a food brand, a facility) is a *different* thing than the
# card's own subject and is NOT redundant with the header, so those stay. The email
# digest (notifications.py) reuses these same templates but has no per-item header
# of its own -- it explicitly re-prepends card["profile_name"] itself rather than
# this file adding the name back into the shared copy.
VACCINE_TEMPLATES_DUE = [
    "PSA: {detail} shot is due {when}. There will be treats bribed into submission for this one. 💉",
    "Reminder: a {detail} appointment is coming up {when}. She has Opinions about the vet but we're going anyway.",
    "{detail} vaccine is due {when}. Bravery levels: currently rehearsing in the mirror.",
    "Circle it in the calendar — due for {detail} {when}. The car ride there will be 10/10, the part after less so.",
]
VACCINE_TEMPLATES_OVERDUE = [
    "Uh oh — {detail} shot was due {when} and we still haven't gone. Booking that appointment, promise. 🙈",
    "{detail} vaccine has been overdue {when}. This is a Me Problem, not a dog problem.",
]

MED_TEMPLATES = [
    "Course of {detail} wraps up {when}. Almost through it, good patient, much treat.",
    "Heads up: finishes {detail} {when}. One more stretch of sneaking pills into cheese.",
    "{detail} prescription runs out {when} — time to check if a refill's needed.",
]

REG_TEMPLATES = [
    "Chennai Corporation registration renews {when}. Bureaucracy waits for no good dog. 📋",
    "Paperwork alert: municipal registration is due {when}. The most tedious part of being a Very Official Dog.",
    "Registration needs renewing {when}. Someone has to adult around here and today it's us.",
]

OWN_BIRTHDAY_TEMPLATES = [
    "🎉 Turns {turning} {when}! Cake is technically for humans but try telling her that.",
    "Mark the calendar — birthday is {when}, turning the big {turning}. Party hat optional, zoomies mandatory.",
    "About to turn {turning} {when}. Somehow still convinced she's a puppy.",
]

FRIEND_BIRTHDAY_TEMPLATES = [
    "It's almost {detail}'s birthday ({when})! There's already a gift idea on record (it's a stick).",
    "{detail}, a very good friend, has a birthday coming up {when}. Park meetup incoming?",
    "Reminder: {detail}'s birthday is {when}. Already practicing the best 'happy birthday' bark.",
]

BATH_TEMPLATES = [
    "Due for a bath {when}. The betrayal will be immense, the fluffiness afterward worth it. 🛁",
    "Bath day is coming up {when}. Someone's about to smell like wet dog, then like a whole new dog.",
    "Reminder: needs a scrub {when}. Towel and treats standing by.",
]

FOOD_REFILL_TEMPLATES = [
    "{detail} is running low — refill due {when}. The bowl situation is getting Serious.",
    "Heads up: time to restock {detail} {when}. No one negotiates dinner like a hungry dog.",
    "Food refill ({detail}) is due {when}. Adding it to the list before the Sad Empty Bowl Stare begins.",
]

BOARDING_TEMPLATES = [
    "📦 Checks into {detail} {when}. Pack the favorite toy, act normal, no long goodbyes.",
    "Boarding alert: heads to {detail} {when}. They'll have a blast and pretend not to miss us.",
    "A little vacation at {detail} starts {when}. Bags are basically already packed.",
]

NEW_PROFILE_TEMPLATES_MY_DOG = [
    "Just joined Pawfolio! Official good dog status: confirmed. 🎉",
    "Just joined the pack here on Pawfolio. Please clap. 🐾",
    "Breaking: now has a Pawfolio profile. A very big day for a very good dog.",
]
NEW_PROFILE_TEMPLATES_COMMUNITY_DOG = [
    "Say hi to the newest neighborhood friend added to Pawfolio! 👋",
    "Has entered the chat. New community pup on the books. 🐾",
    "New friend alert: just got a Pawfolio profile of their very own.",
]


def _when_phrase(days_until: int) -> str:
    if days_until < 0:
        d = abs(days_until)
        return f"{d} day{'s' if d != 1 else ''} ago"
    if days_until == 0:
        return "today"
    if days_until == 1:
        return "tomorrow"
    return f"in {days_until} days"


def render_event_card(event: dict) -> dict:
    """Return {text, tag, emoji_type} for a single event."""
    when = _when_phrase(event["days_until"])
    name = event["profile_name"]
    detail = event["detail"]

    if event["type"] == "vaccination":
        templates = VACCINE_TEMPLATES_OVERDUE if event["days_until"] < 0 else VACCINE_TEMPLATES_DUE
        text = random.choice(templates).format(name=name, detail=detail, when=when)
    elif event["type"] == "medication":
        text = random.choice(MED_TEMPLATES).format(name=name, detail=detail, when=when)
    elif event["type"] == "registration":
        text = random.choice(REG_TEMPLATES).format(name=name, when=when)
    elif event["type"] == "own_birthday":
        turning = event.get("turning") or "??"
        text = random.choice(OWN_BIRTHDAY_TEMPLATES).format(name=name, when=when, turning=turning)
    elif event["type"] == "friend_birthday":
        text = random.choice(FRIEND_BIRTHDAY_TEMPLATES).format(name=name, detail=detail, when=when)
    elif event["type"] == "bath":
        text = random.choice(BATH_TEMPLATES).format(name=name, when=when)
    elif event["type"] == "food_refill":
        text = random.choice(FOOD_REFILL_TEMPLATES).format(name=name, detail=detail, when=when)
    elif event["type"] == "boarding_checkin":
        text = random.choice(BOARDING_TEMPLATES).format(name=name, detail=detail, when=when)
    else:
        text = f"{name}: {detail} — {when}"

    return {
        "text": text,
        "tag": _urgency_tag(event["days_until"]),
        "profile_id": event["profile_id"],
        "profile_name": name,
    }


def render_new_profile_card(profile: dict) -> str:
    templates = (
        NEW_PROFILE_TEMPLATES_MY_DOG if profile["profile_type"] == "my_dog"
        else NEW_PROFILE_TEMPLATES_COMMUNITY_DOG
    )
    return random.choice(templates).format(name=profile["name"])


EMPTY_STATE_MESSAGES = [
    "Nothing urgent on the horizon. Every good dog in this app is fully vaccinated, medicated on schedule, "
    "registered with the city, and nowhere near a birthday. Go enjoy a belly rub, you've earned the peace of mind. 🐾",
    "The feed is quiet. No shots due, no meds running out, no birthdays looming. Suspiciously well-organized "
    "pet parenting happening here. ✨",
    "All clear! Nothing due in the next 30 days. This is either excellent planning or a trap. Enjoy it either way.",
]

DIGEST_INTROS = [
    "Here's what the pack has on its calendar:",
    "A little bird (well, a dog) asked me to remind you about a few things:",
    "Quick digest before the tail wags become a distraction:",
    "The dogs can't email you themselves, so here we are:",
]

DIGEST_OUTROS = [
    "That's the whole list. Go pet something. 🐾",
    "Handled with care by Pawfolio, the feed that's just dogs.",
    "No further action needed except maybe a belly rub.",
    "Sent with love, some drool, and one (1) dashboard's worth of reminders.",
]
