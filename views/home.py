import random
import streamlit as st
from db import get_upcoming_events, get_profile, get_recently_added_profiles
from voice import render_event_card, render_new_profile_card, EMPTY_STATE_MESSAGES
from ui_helpers import show_photo, show_mascot

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
            if st.button("View profile →", key=f"goto_{event['type']}_{event['record_id']}"):
                st.session_state["selected_profile_id"] = event["profile_id"]
                st.switch_page("views/profile_detail.py")

if not recent_profiles and not events:
    empty_cols = st.columns([1, 2, 1])
    with empty_cols[1]:
        show_mascot(max_width=180)
        st.info(random.choice(EMPTY_STATE_MESSAGES))
