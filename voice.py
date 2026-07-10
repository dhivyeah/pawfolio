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


VACCINE_TEMPLATES_DUE = [
    "PSA: {name}'s {detail} shot is due {when}. There will be treats bribed into submission for this one. 💉",
    "Reminder: {name} has a {detail} appointment coming up {when}. She has Opinions about the vet but we're going anyway.",
    "{name}'s {detail} vaccine is due {when}. Bravery levels: currently rehearsing in the mirror.",
    "Circle it in the calendar — {name} is due for {detail} {when}. The car ride there will be 10/10, the part after less so.",
]
VACCINE_TEMPLATES_OVERDUE = [
    "Uh oh — {name}'s {detail} shot was due {when} and we still haven't gone. Booking that appointment, promise. 🙈",
    "{name}'s {detail} vaccine has been overdue {when}. This is a Me Problem, not a {name} problem.",
]

MED_TEMPLATES = [
    "{name}'s course of {detail} wraps up {when}. Almost through it, good patient, much treat.",
    "Heads up: {name} finishes {detail} {when}. One more stretch of sneaking pills into cheese.",
    "{name}'s {detail} prescription runs out {when} — time to check if a refill's needed.",
]

REG_TEMPLATES = [
    "{name}'s Chennai Corporation registration renews {when}. Bureaucracy waits for no good dog. 📋",
    "Paperwork alert: {name}'s municipal registration is due {when}. The most tedious part of being a Very Official Dog.",
    "{name}'s registration needs renewing {when}. Someone has to adult around here and today it's us.",
]

OWN_BIRTHDAY_TEMPLATES = [
    "🎉 {name} turns {turning} {when}! Cake is technically for humans but try telling her that.",
    "Mark the calendar — {name}'s birthday is {when}, turning the big {turning}. Party hat optional, zoomies mandatory.",
    "{name} is about to turn {turning} {when}. Somehow still convinced she's a puppy.",
]

FRIEND_BIRTHDAY_TEMPLATES = [
    "It's almost {detail}'s birthday ({when})! {name} would like it on record that she has a gift idea (it's a stick).",
    "{detail}, a very good friend of {name}'s, has a birthday coming up {when}. Park meetup incoming?",
    "Reminder: {detail}'s birthday is {when}. {name} is already practicing her best 'happy birthday' bark.",
]

BATH_TEMPLATES = [
    "{name} is due for a bath {when}. The betrayal will be immense, the fluffiness afterward worth it. 🛁",
    "Bath day for {name} is coming up {when}. Someone's about to smell like wet dog, then like a whole new dog.",
    "Reminder: {name} needs a scrub {when}. Towel and treats standing by.",
]

FOOD_REFILL_TEMPLATES = [
    "{name}'s {detail} is running low — refill due {when}. The bowl situation is getting Serious.",
    "Heads up: time to restock {name}'s {detail} {when}. No one negotiates dinner like a hungry dog.",
    "{name}'s food refill ({detail}) is due {when}. Adding it to the list before the Sad Empty Bowl Stare begins.",
]

BOARDING_TEMPLATES = [
    "📦 {name} checks into {detail} {when}. Pack the favorite toy, act normal, no long goodbyes.",
    "Boarding alert: {name} heads to {detail} {when}. They'll have a blast and pretend not to miss us.",
    "{name}'s little vacation at {detail} starts {when}. Bags are basically already packed.",
]

NEW_PROFILE_TEMPLATES_MY_DOG = [
    "🎉 Everyone welcome {name} to Pawfolio! Official good dog status: confirmed.",
    "🐾 {name} just joined the pack here on Pawfolio. Please clap.",
    "Breaking: {name} now has a Pawfolio profile. A very big day for a very good dog.",
]
NEW_PROFILE_TEMPLATES_COMMUNITY_DOG = [
    "👋 Say hi to {name}, the newest neighborhood friend added to Pawfolio!",
    "🐾 {name} has entered the chat. New community pup on the books.",
    "New friend alert: {name} just got a Pawfolio profile of their very own.",
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
