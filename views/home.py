import random
import streamlit as st
from db import (
    get_upcoming_events, get_profile, get_recently_added_profiles,
    get_already_notified_keys, mark_events_notified,
)
from voice import render_event_card, render_new_profile_card, EMPTY_STATE_MESSAGES
from ui_helpers import show_photo, show_mascot, queue_toast, render_queued_toast
from notifications import current_milestone, event_state_key, MILESTONES

render_queued_toast()

header_cols = st.columns([1, 3, 1.4])
with header_cols[0]:
    show_mascot(max_width=110)
with header_cols[1]:
    st.title("🐾 Pawfolio")
    st.caption("The feed, but it's just dogs.")
with header_cols[2]:
    st.write("")
    if st.button("➕ New Profile", key="home_add_profile", use_container_width=True):
        st.switch_page("views/add_profile.py")

st.divider()

recent_profiles = get_recently_added_profiles(days=7)
events = get_upcoming_events(horizon_days=30)

if recent_profiles:
    st.subheader("🎉 New Pack Members")
    for profile in recent_profiles:
        with st.container(border=True, key=f"card_new_{profile['id']}"):
            cols = st.columns([1, 8])
            with cols[0]:
                show_photo(profile["photo_path"], width=60, height=60, shape="circle")
            with cols[1]:
                st.markdown(render_new_profile_card(profile))
                if st.button("View profile →", key=f"new_{profile['id']}"):
                    st.session_state["selected_profile_id"] = profile["id"]
                    st.switch_page("views/profile_detail.py")
    st.divider()

if events:
    if recent_profiles:
        st.subheader("📋 Upcoming")
    # Fetched once for the whole list rather than per-card -- one query, not N.
    already_notified = get_already_notified_keys()
    for event in events:
        card = render_event_card(event)
        overdue = event["days_until"] < 0
        urgency = "overdue" if overdue else ("soon" if event["days_until"] <= 3 else "upcoming")
        event_key = f"card_evt_{urgency}_{event['type']}_{event['record_id']}"
        with st.container(border=True, key=event_key):
            cols = st.columns([1, 8, 2])
            with cols[0]:
                profile = get_profile(event["profile_id"])
                show_photo(profile["photo_path"] if profile else None, width=60, height=60, shape="circle")
            with cols[1]:
                st.markdown(f"**{card['profile_name']}** · {card['text']}")
            with cols[2]:
                if urgency == "overdue":
                    st.error(card["tag"])
                elif urgency == "soon":
                    st.warning(card["tag"])
                else:
                    st.success(card["tag"])

            btn_cols = st.columns([2, 2, 3])
            with btn_cols[0]:
                if st.button("View profile →", key=f"goto_{event['type']}_{event['record_id']}"):
                    st.session_state["selected_profile_id"] = event["profile_id"]
                    st.switch_page("views/profile_detail.py")

            # Only items still due for an email at all (0/1/3/7-day checkpoints, not
            # overdue or further out than the notify horizon) get a mute option -- an
            # item that was never going to email again has nothing to mute.
            milestone = current_milestone(event["days_until"])
            if milestone is not None:
                state_key = event_state_key(event)
                # Milestone 0 is always the last checkpoint reached, whether that's
                # because the countdown ran its course naturally or because muting
                # pre-recorded every remaining checkpoint at once -- so its presence
                # means "no more emails coming this cycle" either way.
                muted = (event["type"], event["record_id"], state_key, 0) in already_notified
                with btn_cols[1]:
                    if muted:
                        st.caption("🔇 Muted until next cycle")
                    elif st.button("🔇 Mute email for this", key=f"mute_{event['type']}_{event['record_id']}", use_container_width=True):
                        keys = [(event["type"], event["record_id"], state_key, m) for m in MILESTONES]
                        mark_events_notified(keys)
                        queue_toast("Muted — no more emails for this until the due date changes. Still shows here on the dashboard.", icon="🔇")
                        st.rerun()

if not recent_profiles and not events:
    empty_cols = st.columns([1, 2, 1])
    with empty_cols[1]:
        show_mascot(max_width=180)
        st.info(random.choice(EMPTY_STATE_MESSAGES))
