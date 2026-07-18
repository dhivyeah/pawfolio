"""Login/signup screen shown before any app content when nobody's authenticated yet.

Not registered as an st.Page -- it replaces the whole app chrome (no top nav, no
dashboard) rather than being one more destination inside it, so app.py calls
render_login_signup() directly and st.stop()s afterward instead of handing off to
st.navigation.
"""
import streamlit as st

import auth


def render_login_signup():
    header_cols = st.columns([1, 3])
    with header_cols[0]:
        st.write("")
        st.markdown(
            "<div style='font-size:4rem;text-align:center;'>🐾</div>",
            unsafe_allow_html=True,
        )
    with header_cols[1]:
        st.title("Pawfolio")
        st.caption("The feed, but it's just dogs. Sign in to see yours.")

    st.divider()

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("Enter both email and password.")
            else:
                with st.spinner("Logging in..."):
                    success, session, error = auth.sign_in(email, password)
                if success:
                    st.session_state["auth_user"] = session
                    st.rerun()
                else:
                    st.error(error)

        with st.expander("Forgot password?"):
            with st.form("forgot_password_form"):
                reset_email = st.text_input("Email", key="reset_email")
                reset_submitted = st.form_submit_button("Send reset link")
            if reset_submitted:
                if not reset_email:
                    st.error("Enter your email.")
                else:
                    with st.spinner("Sending..."):
                        success, error = auth.request_password_reset(reset_email)
                    if success:
                        st.success(
                            "🐾 If that email has a Pawfolio account, a reset link is on "
                            "its way — check your inbox."
                        )
                    else:
                        st.error(error)

    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input(
                "Password", type="password", key="signup_password",
                help="At least 6 characters.",
            )
            confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
            submitted = st.form_submit_button("Sign up", use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("Enter both email and password.")
            elif password != confirm:
                st.error("Passwords don't match.")
            else:
                with st.spinner("Creating your account..."):
                    success, info, error = auth.sign_up(email, password)
                if success and info["needs_confirmation"]:
                    st.success(
                        "🐾 Account created! Check your email for a confirmation link, "
                        "then come back and log in."
                    )
                elif success:
                    st.success("🐾 Account created! You can log in now.")
                else:
                    st.error(error)


def render_password_reset(access_token: str, refresh_token: str):
    """Shown instead of the login/signup tabs when the URL carries a recovery link's
    ?type=recovery&access_token=...&refresh_token=... (app.py's JS shim moves these here
    from the URL fragment Supabase actually redirects with, then checks st.query_params for
    them before the normal auth gate). One form, one shot: setting the session and the new
    password happen together in auth.complete_password_reset -- there's no separate "verify"
    step to keep the user logged in through, and this app has no other reason to hold a
    recovery session open."""
    st.title("🐾 Pawfolio")
    st.subheader("Set a new password")

    # st.query_params.clear() triggers its own rerun, so the success message can't be shown
    # in the same pass that clears it -- a session_state flag lets the "done" state survive
    # into the next rerun, where the confirmation and button actually get to render.
    if st.session_state.get("_password_reset_done"):
        st.success("🐾 Password updated! Log in below with your new password.")
        if st.button("Continue to log in"):
            st.session_state.pop("_password_reset_done", None)
            st.query_params.clear()
            st.rerun()
        return

    with st.form("reset_password_form"):
        new_password = st.text_input(
            "New password", type="password", key="new_password", help="At least 6 characters."
        )
        confirm = st.text_input("Confirm new password", type="password", key="confirm_new_password")
        submitted = st.form_submit_button("Set new password", use_container_width=True)

    if submitted:
        if not new_password:
            st.error("Enter a new password.")
        elif new_password != confirm:
            st.error("Passwords don't match.")
        else:
            with st.spinner("Updating your password..."):
                success, error = auth.complete_password_reset(access_token, refresh_token, new_password)
            if success:
                st.session_state["_password_reset_done"] = True
                st.rerun()
            else:
                st.error(error)
                st.caption("Request a new reset link from the login screen if this one has expired.")
