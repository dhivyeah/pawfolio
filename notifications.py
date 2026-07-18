"""Email digest notifications, sent via Resend on app load.

Reuses the exact same "what's due" source of truth as the dashboard (db.get_upcoming_events)
and the exact same copy generator (voice.render_event_card) -- this file only adds the parts
those two didn't already have: a tighter notification horizon, dedup against what's already
been emailed, the digest's own subject/HTML/text framing, and the actual Resend API call.
"""
import os
import random
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

import db
import voice

load_dotenv()

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_FROM_EMAIL = "Pawfolio <onboarding@resend.dev>"

# Deliberately tighter than the dashboard's 30-day display horizon -- a digest that fires
# for anything a month out would be noisy. Same underlying function, different parameter,
# not a second implementation of "what's due."
NOTIFY_HORIZON_DAYS = 7

_TIER_COLORS = {"overdue": "#C1613F", "soon": "#F0C05A", "upcoming": "#8FAE8B"}

# Countdown checkpoints, in ascending days-until. An item is notified once as it first
# crosses into each band (4-7 days out -> the "7" checkpoint, 2-3 days -> "3", 1 day -> "1",
# 0 days -> "0"), then never again for that same due date. Deliberately stops there --
# nothing fires once an item goes overdue (negative days_until). The app has no way to know
# whether an overdue vaccination/registration/etc. has actually been handled in real life or
# just hasn't been updated in Pawfolio yet, so it can't distinguish "still needs doing" from
# "done, just not logged" -- rather than guess, it stays quiet past the deadline and leaves
# the dashboard's persistent overdue tag as the source of truth for anything already missed.
MILESTONES = [0, 1, 3, 7]


def current_milestone(days_until: int):
    """Which countdown checkpoint this event currently falls into, or None if it's outside
    the notify range entirely -- further out than the horizon, or already overdue. Public
    (no underscore) because the dashboard's "mute" button needs it too, to know whether an
    event is currently email-eligible at all."""
    if days_until < 0:
        return None
    for m in MILESTONES:
        if days_until <= m:
            return m
    return None


def _urgency_tier(days_until: int) -> str:
    if days_until < 0:
        return "overdue"
    if days_until <= 3:
        return "soon"
    return "upcoming"


def event_state_key(event: dict) -> str:
    """A value that changes when an event's due-state genuinely changes, resetting its
    countdown from scratch. Most event types carry a real due_date. Birthdays (own_birthday,
    friend_birthday) don't -- their due_date is always None, and SQLite treats every NULL as
    distinct under a UNIQUE constraint, which would silently break dedup for them if due_date
    were used directly. Falling back to the actual occurrence date (today + days_until) gives
    a stable, non-null key that naturally rolls over to a new value at next year's birthday."""
    if event.get("due_date"):
        return event["due_date"]
    occurrence = date.today() + timedelta(days=event["days_until"])
    return occurrence.isoformat()


def _event_key(event: dict) -> tuple:
    return (event["type"], event["record_id"], event_state_key(event), current_milestone(event["days_until"]))


def _build_digest(events: list) -> tuple:
    """Returns (subject, html_body, text_body) for the given events, using the exact same
    per-event copy (voice.render_event_card) the dashboard cards use."""
    count = len(events)
    subject = f"🐾 Pawfolio: {count} thing{'s' if count != 1 else ''} coming up"
    intro = random.choice(voice.DIGEST_INTROS)
    outro = random.choice(voice.DIGEST_OUTROS)

    text_lines = [intro, ""]
    html_items = []
    for event in events:
        card = voice.render_event_card(event)
        color = _TIER_COLORS[_urgency_tier(event["days_until"])]
        text_lines.append(f"- {card['text']} ({card['tag']})")
        html_items.append(f"""
        <div style="padding:12px 16px;margin-bottom:10px;background:#FFF3E6;
                    border-left:4px solid {color};border-radius:10px;">
          <div style="color:#4A3225;font-size:15px;line-height:1.5;">{card['text']}</div>
          <div style="color:{color};font-size:12px;font-weight:600;margin-top:4px;">{card['tag']}</div>
        </div>""")
    text_lines += ["", outro]
    text_body = "\n".join(text_lines)

    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                background:#FFF8F0;padding:24px;border-radius:16px;">
      <h2 style="color:#4A3225;margin-top:0;">🐾 Pawfolio</h2>
      <p style="color:#4A3225;">{intro}</p>
      {''.join(html_items)}
      <p style="color:#8A7160;font-size:13px;margin-top:20px;">{outro}</p>
    </div>"""
    return subject, html_body, text_body


def _send_email(subject, html_body, text_body, api_key, to_email, from_email):
    """Returns (success, error_message)."""
    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_email, "to": [to_email], "subject": subject,
                  "html": html_body, "text": text_body},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True, None
        return False, f"Resend returned {resp.status_code}: {resp.text[:300]}"
    except requests.RequestException as e:
        return False, f"request to Resend failed: {e}"


def check_and_notify():
    """Call once per app load (see app.py -- gated to once per browser session there, since
    Streamlit re-runs this module's caller on every widget interaction otherwise). Sends at
    most one digest a day, only for events not already included in a previously-successful
    digest. Never raises -- a notification problem should never break the app itself."""
    try:
        if db.was_digest_sent_today():
            return
        events = db.get_upcoming_events(horizon_days=NOTIFY_HORIZON_DAYS)
        # get_upcoming_events has no lower bound on days_until (see KNOWN_ISSUES 8) -- it
        # returns overdue items too. Notifications intentionally stop at "due today," so
        # anything already overdue is filtered out here rather than ever reaching a
        # milestone check.
        candidate_events = [e for e in events if current_milestone(e["days_until"]) is not None]
        if not candidate_events:
            return
        already_notified = db.get_already_notified_keys()
        new_events = [e for e in candidate_events if _event_key(e) not in already_notified]
        if not new_events:
            return

        api_key = os.environ.get("RESEND_API_KEY")
        to_email = os.environ.get("NOTIFY_EMAIL")
        from_email = os.environ.get("RESEND_FROM_EMAIL", DEFAULT_FROM_EMAIL)
        if not api_key or not to_email:
            print("[notifications] RESEND_API_KEY or NOTIFY_EMAIL not set in .env -- skipping email digest.", flush=True)
            return

        subject, html_body, text_body = _build_digest(new_events)
        success, error = _send_email(subject, html_body, text_body, api_key, to_email, from_email)
        if success:
            db.mark_events_notified(_event_key(e) for e in new_events)
            db.record_digest_sent()
            print(f"[notifications] Digest sent to {to_email} ({len(new_events)} item(s)).", flush=True)
        else:
            print(f"[notifications] Digest send failed, will retry next app load: {error}", flush=True)
    except Exception as e:
        print(f"[notifications] check_and_notify() failed unexpectedly: {e}", flush=True)
