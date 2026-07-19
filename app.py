import streamlit as st
import streamlit.components.v1 as components
from db import init_db, get_all_profiles, PawfolioDBError
from styles import inject_theme
from notifications import check_and_notify
from login_ui import render_login_signup, render_password_reset
import auth

st.set_page_config(page_title="Pawfolio", page_icon="🐾", layout="wide")

# Injected before any slow work below (DB init, notification check) so the browser gets
# the stylesheet as early as possible in the stream, rather than after -- Streamlit sends
# each element to the frontend as its st.* call executes, so on a cold session where
# init_db()/check_and_notify() take a few real seconds against Postgres, the old ordering
# left a window where the page could show unstyled/raw content while waiting on them.
inject_theme(st)

# This Supabase project uses the "implicit" auth flow, so a password-reset email's link
# redirects back with the session tokens in the URL *fragment*
# (#access_token=...&type=recovery), not the query string -- fragments are resolved
# entirely client-side and never reach the server, so st.query_params can't see them
# directly. This tiny script reads the fragment from the parent page (Streamlit components
# render same-origin, so window.parent.location works) and, if it looks like a recovery
# link, rewrites the URL to carry the same values as query params instead, which the
# st.query_params check just below *can* read once the resulting reload happens.
components.html(
    """
    <script>
    (function() {
        var hash = window.parent.location.hash;
        if (hash && hash.indexOf("type=recovery") !== -1 && hash.indexOf("access_token=") !== -1) {
            var params = new URLSearchParams(hash.substring(1));
            var qs = new URLSearchParams({
                type: "recovery",
                access_token: params.get("access_token") || "",
                refresh_token: params.get("refresh_token") || "",
            });
            window.parent.location.replace(window.parent.location.pathname + "?" + qs.toString());
        }
    })();
    </script>
    """,
    height=0,
)

# Checked before anything else -- including the normal login gate -- since someone
# completing a password reset is by definition not logged in yet, and doesn't need the
# database touched at all to set a new password.
if st.query_params.get("type") == "recovery" and st.query_params.get("access_token"):
    render_password_reset(st.query_params["access_token"], st.query_params.get("refresh_token", ""))
    st.stop()

# Everything below that can touch the database is wrapped in one handler for
# PawfolioDBError -- a Supabase project that's paused (free tier auto-pauses after a
# week idle) or otherwise briefly unreachable used to surface as Streamlit's default
# raw traceback: full server file paths, the Supabase pooler's hostname and resolved
# IP, "Ask ChatGPT" buttons -- a developer debug view shown to any random visitor.
# Deliberately catches only PawfolioDBError, not Exception in general -- a genuine bug
# elsewhere in the app should still surface normally rather than being hidden behind a
# "database trouble" message that would send debugging in the wrong direction.
try:
    # Gated to once per browser session, same reasoning as the notification check below
    # -- init_db() is a batch of idempotent CREATE TABLE IF NOT EXISTS / ADD COLUMN IF
    # NOT EXISTS statements. Cheap against a local SQLite file, but Postgres now means
    # each one is a network round-trip to Supabase, so re-running the whole batch on
    # every single widget click (Streamlit's normal rerun-the-script-top-to-bottom
    # model) would add needless latency to everything in the app, not just page loads.
    if not st.session_state.get("_db_initialized"):
        init_db()
        st.session_state["_db_initialized"] = True

    # Phase 4: everything past this point is per-user, so nothing past it can run until
    # someone's actually logged in. render_login_signup() replaces the whole app chrome
    # (no top nav, no dashboard) rather than being one more page inside it -- st.stop()
    # right after means nothing below this block executes on an unauthenticated load.
    if not st.session_state.get("auth_user"):
        render_login_signup()
        st.stop()

    owner_id = st.session_state["auth_user"]["user_id"]
    user_email = st.session_state["auth_user"]["email"]

    # "On app load" means once per browser session, not once per rerun -- app.py
    # re-executes top to bottom on every widget interaction anywhere in the app
    # (Streamlit's normal execution model), so an unconditional call here would
    # re-check on every single click.
    if not st.session_state.get("_notify_checked"):
        check_and_notify(owner_id, user_email)
        st.session_state["_notify_checked"] = True

    home_page = st.Page("views/home.py", title="Home", icon="🏠", default=True)
    # Renamed "All the Pups" -> "My Pups" (2026-07-19) -- still exactly the same page,
    # same owner_id-scoped query, same both-profile-types visibility. This is NOT the
    # future public "All Pups" feature (Phase 5: every user's dog names + general
    # location only, no private records, with a "friend" option) -- that's intentionally
    # not built yet. When it is, it belongs as its own new st.Page here, separate from
    # this one, since the two need very different data-scoping (this page stays
    # owner-private; that one would deliberately cross owners for name/location only).
    my_pups_page = st.Page("views/all_profiles.py", title="My Pups", icon="🐾")
    add_profile_page = st.Page("views/add_profile.py", title="New Profile", icon="➕")
    profile_detail_page = st.Page("views/profile_detail.py", title="Profile", icon="🐶")

    pg = st.navigation(
        [home_page, my_pups_page, add_profile_page, profile_detail_page],
        position="hidden",
    )

    # Top bar: compact brand mark (left), Home/My Pups as a pill-shaped segmented
    # control (center), and a single hamburger/account menu (right) -- log out and
    # "New Profile" both used to live directly in this bar/on the Home page; both
    # moved out (log out into the account menu below, New Profile onto the My Pups
    # page itself, where adding a profile is actually contextually relevant) so this
    # bar only ever holds primary navigation, not page-specific or account-level
    # actions. Which nav segment is "active" isn't something Streamlit's own
    # st.button tracks, so it's expressed by swapping in a differently-keyed button
    # (styles.py styles "_active" as the filled segment) based on which page
    # st.navigation() actually picked for this run.
    #
    # Each nav segment is rendered *twice* -- an icon+text "_full" button and an
    # icon-only "_icon" button -- with CSS (styles.py) showing only one at a time
    # based on viewport width. Streamlit can't swap a button's own label by media
    # query, so both exist and the hidden one just never gets a chance to be
    # clicked; this is what stops "Home"/"My Pups" from wrapping to two lines on a
    # phone-width screen instead of collapsing to icon-only.
    #
    # All 4 nav buttons are direct children of the nav_pills container -- NOT
    # nested inside a second st.columns() split (an earlier version did that, and
    # the extra column layer was the actual cause of one segment rendering outside
    # the pill unstyled on mobile -- see KNOWN_ISSUES.md history). With no nested
    # columns inside nav_pills, there's no risk of that recurring.
    is_home_active = pg is home_page
    is_my_pups_active = pg is my_pups_page
    with st.container(key="top_nav"):
        header_cols = st.columns([2.4, 6.2, 1.4])
        with header_cols[0]:
            # Compact brand mark -- icon-only on mobile (CSS hides the text span
            # below the same 640px breakpoint the nav pills use), icon+text on
            # desktop. Replaces the old large hero title that used to live on the
            # Home page itself; showing it once, globally, here, means Home no
            # longer needs to repeat it as its own page header.
            st.markdown(
                "<div class='pf-brand'><span class='pf-brand-icon'>🐾</span>"
                "<span class='pf-brand-text'>Pawfolio</span></div>",
                unsafe_allow_html=True,
            )
        with header_cols[1]:
            with st.container(key="nav_pills"):
                home_clicked = st.button(
                    "🏠 Home", key="nav_home_full_active" if is_home_active else "nav_home_full"
                )
                home_icon_clicked = st.button(
                    "🏠", key="nav_home_icon_active" if is_home_active else "nav_home_icon", help="Home"
                )
                pups_clicked = st.button(
                    "🐾 My Pups", key="nav_profiles_full_active" if is_my_pups_active else "nav_profiles_full"
                )
                pups_icon_clicked = st.button(
                    "🐾", key="nav_profiles_icon_active" if is_my_pups_active else "nav_profiles_icon",
                    help="My Pups",
                )
                if home_clicked or home_icon_clicked:
                    st.switch_page(home_page)
                if pups_clicked or pups_icon_clicked:
                    st.switch_page(my_pups_page)
        with header_cols[2]:
            # Account menu: a single hamburger icon opening a small popover with an
            # account-level summary and log out -- the only account-level actions
            # in the app, deliberately separated from the primary Home/My Pups
            # navigation next to it. st.popover() is the closest native Streamlit
            # primitive to a dropdown/slide-out menu; see KNOWN_ISSUES.md for how
            # it behaves here specifically (it's a real click-to-open floating
            # panel, not a custom-animated drawer -- Streamlit has no such
            # component to reach for).
            with st.popover("☰", key="account_menu", help=f"Logged in as {user_email}"):
                my_dog_count = len(get_all_profiles(owner_id, profile_type="my_dog"))
                community_count = len(get_all_profiles(owner_id, profile_type="community_dog"))
                st.caption(
                    f"{my_dog_count} pup{'s' if my_dog_count != 1 else ''} · "
                    f"{community_count} community pup{'s' if community_count != 1 else ''}"
                )
                st.divider()
                if st.button("🚪 Log out", key="nav_logout", use_container_width=True):
                    auth.sign_out()
                    # _toast_queue also cleared here -- otherwise a toast queued by this user's
                    # last action (e.g. "Dr. Rao set as primary vet") can survive the logout and
                    # fire for whoever logs in next on this same browser session, leaking a
                    # fragment of this user's data to them. See KNOWN_ISSUES.md, "toast-queue
                    # leak across logout" -- confirmed via direct reproduction, not theoretical.
                    for key in ("auth_user", "_notify_checked", "_toast_queue"):
                        st.session_state.pop(key, None)
                    st.rerun()

    st.divider()

    pg.run()
except PawfolioDBError:
    st.error(
        "🐾 Pawfolio can't reach its database right now. This is usually temporary — "
        "try refreshing in a minute or two."
    )
    st.stop()
