import random
import streamlit as st
from db import (
    get_upcoming_events, get_profile, get_recently_added_profiles,
    get_already_notified_keys, mark_events_notified,
)
from voice import render_event_card, render_new_profile_card, EMPTY_STATE_MESSAGES
from ui_helpers import (
    show_mascot, queue_toast, render_queued_toast, category_for_type,
    render_avatar_card_link,
)
from notifications import current_milestone, event_state_key, MILESTONES

owner_id = st.session_state["auth_user"]["user_id"]

render_queued_toast()

# The old page-level "🐾 Pawfolio" hero title + mascot + New Profile button lived
# here -- removed 2026-07-19 now that the compact brand mark is shown once,
# globally, in app.py's top bar (repeating it here would just duplicate it), and
# New Profile moved to the My Pups page, where adding a profile is contextually
# relevant. The mascot's other appearance (the empty-state illustration below)
# is untouched.

recent_profiles = get_recently_added_profiles(owner_id, days=7)
events = get_upcoming_events(owner_id, horizon_days=30)

# Upcoming (time-sensitive reminders) comes before New Pack Members
# (social/informational) -- the thing with a due date is the more urgent read.
if events:
    st.subheader("📋 Upcoming", anchor=False)
    # Fetched once for the whole list rather than per-card -- one query, not N.
    already_notified = get_already_notified_keys()
    # 2-column responsive grid: st.columns already collapses to one-per-row below the
    # existing 640px mobile breakpoint (styles.py), so a plain 2-column split here is
    # enough to get "2 columns desktop, 1 column mobile" without a separate CSS grid --
    # cards still need to be real st.container()s (not static HTML) since each one holds
    # a live mute-bell toggle, not just decorative content.
    grid_cols = st.columns(2)
    for i, event in enumerate(events):
        card = render_event_card(event)
        category = category_for_type(event["type"])
        event_key = f"card_evt_{category}_{event['type']}_{event['record_id']}"
        with grid_cols[i % 2]:
            with st.container(border=True, key=event_key):
                # Avatar + name-row (category dot, bold name, urgency badge) + full
                # message, all in one clickable unit -- the mute-bell sits in its own
                # narrow column to the right, at the card's edge, outside that
                # clickable area so it stays independently tappable. Wrapped in its
                # own keyed "cardrow_" container so styles.py can give this specific
                # column split a guaranteed-visible minimum width for the mute-bell
                # column, without also matching the *nested* avatar/content column
                # split one level down inside render_avatar_card_link (that one needs
                # to stay free to shrink/wrap, not get a hard floor).
                with st.container(key=f"cardrow_{event['type']}_{event['record_id']}"):
                    content_cols = st.columns([6, 1])
                    with content_cols[0]:
                        profile = get_profile(event["profile_id"], owner_id)
                        render_avatar_card_link(
                            profile["photo_path"] if profile else None,
                            card["profile_name"], card["text"], event["profile_id"],
                            key=f"evt_{event['type']}_{event['record_id']}",
                            category=category, days_until=event["days_until"],
                        )
                    with content_cols[1]:
                        # Only items still due for an email at all (0/1/3/7-day
                        # checkpoints, not overdue or further out than the notify
                        # horizon) get a mute option -- an item that was never going to
                        # email again has nothing to mute.
                        milestone = current_milestone(event["days_until"])
                        if milestone is not None:
                            state_key = event_state_key(event)
                            # Milestone 0 is always the last checkpoint reached, whether
                            # that's because the countdown ran its course naturally or
                            # because muting pre-recorded every remaining checkpoint at
                            # once -- so its presence means "no more emails coming this
                            # cycle" either way.
                            muted = (event["type"], event["record_id"], state_key, 0) in already_notified
                            if muted:
                                # Same plain bell glyph as the live button below, just
                                # dimmed/grayed and non-interactive -- a slash-bell (🔕)
                                # read as a "blocked/prohibited" symbol rather than
                                # "muted" at this size, so the resting AND muted states
                                # both use the same neutral 🔔 now, communicating "mute"
                                # through appearance change (dim = already done) instead
                                # of a different, more ambiguous glyph.
                                st.markdown(
                                    "<div style='text-align:center;padding-top:2px;' "
                                    "title='Muted until next cycle'>"
                                    "<span style='opacity:0.35;filter:grayscale(60%);"
                                    "font-size:0.85rem;'>🔔</span></div>",
                                    unsafe_allow_html=True,
                                )
                            elif st.button("🔔", key=f"mutebell_{event['type']}_{event['record_id']}",
                                           help="Mute email reminders for this"):
                                keys = [(event["type"], event["record_id"], state_key, m) for m in MILESTONES]
                                mark_events_notified(keys)
                                queue_toast(
                                    "Muted — no more emails for this until the due date changes. "
                                    "Still shows here on the dashboard.", icon="🔇",
                                )
                                st.rerun()
    if recent_profiles:
        st.divider()

if recent_profiles:
    st.subheader("🎉 New Pack Members", anchor=False)
    for profile in recent_profiles:
        with st.container(border=True, key=f"card_new_{profile['id']}"):
            render_avatar_card_link(
                profile["photo_path"], profile["name"], render_new_profile_card(profile),
                profile["id"], key=f"new_{profile['id']}",
            )

if not recent_profiles and not events:
    empty_cols = st.columns([1, 2, 1])
    with empty_cols[1]:
        show_mascot(max_width=180)
        st.info(random.choice(EMPTY_STATE_MESSAGES))
