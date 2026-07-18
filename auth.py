"""Supabase Auth wrapper -- email/password signup, login, logout.

Deliberately separate from db.py's direct-Postgres data access: this module only ever
talks to Supabase's Auth (GoTrue) service via the official client, using the public
`anon` key (safe to ship, not a secret in the same sense as the database password or the
`service_role` key -- it's designed to be used from a client that hasn't authenticated
yet, which is exactly this module's job). Data queries still go straight to Postgres via
db.py, unaffected by whether Supabase's PostgREST/Data API layer is enabled at all.
"""
import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

# Where a password-reset email's link sends the browser back to. Supabase requires this to
# be on the project's Redirect URLs allow-list (Authentication -> URL Configuration in the
# dashboard) or it silently falls back to the project's default Site URL instead.
APP_URL = os.environ.get("APP_URL", "https://mypawfolio.streamlit.app")

_client: Client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_ANON_KEY are not set. Add them to your .env file "
                "(see .env.example) -- Project Settings -> API in your Supabase dashboard."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def _friendly_auth_error(e: Exception) -> str:
    """Supabase's auth errors are already reasonably safe to show as-is (they don't leak
    infrastructure details the way a raw psycopg2 error does -- see db.PawfolioDBError for
    that problem elsewhere), but the raw wording is written for a developer reading API
    docs, not someone typing their password into a warm, quirky pet-tracking app. This
    maps the handful that come up in normal use to copy that matches the rest of the app;
    anything unrecognized falls through to a still-safe generic message rather than a raw
    exception string, since new Supabase error wording could otherwise leak straight to
    the UI un-reviewed."""
    msg = str(e).lower()
    if "already registered" in msg or "already exists" in msg or "user already registered" in msg:
        return "That email already has an account — try logging in instead."
    if "invalid login credentials" in msg or "invalid email or password" in msg:
        return "Incorrect email or password."
    if "email not confirmed" in msg:
        return "Almost there — check your email for a confirmation link before logging in."
    if "password" in msg and ("least" in msg or "short" in msg or "6 char" in msg or "weak" in msg):
        return "Password must be at least 6 characters."
    if "invalid" in msg and "email" in msg:
        return "That doesn't look like a valid email address."
    if "rate limit" in msg or "too many" in msg:
        return "Too many attempts — please wait a moment and try again."
    return "Something went wrong. Please try again in a moment."


def sign_up(email: str, password: str):
    """Returns (success, info, error). On success, `info` is a dict with at least
    `user_id` and `email`; it also carries `needs_confirmation=True` if Supabase's
    default "confirm your email" setting is on for this project, since that changes
    what the signup UI should tell the user to do next (check email vs. just log in)."""
    try:
        resp = _get_client().auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return False, None, _friendly_auth_error(e)
    if not resp.user:
        return False, None, "Sign up didn't go through. Please try again."
    # Supabase returns a user but no session when email confirmation is required --
    # session is only populated once the account is actually usable.
    needs_confirmation = resp.session is None
    return True, {
        "user_id": resp.user.id,
        "email": resp.user.email,
        "needs_confirmation": needs_confirmation,
    }, None


def sign_in(email: str, password: str):
    """Returns (success, session, error). On success, `session` is a dict with
    `user_id`, `email`, `access_token` -- everything app.py needs to stash in
    st.session_state for the rest of that browser session."""
    try:
        resp = _get_client().auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        return False, None, _friendly_auth_error(e)
    if not resp.user or not resp.session:
        return False, None, "Login didn't go through. Please try again."
    return True, {
        "user_id": resp.user.id,
        "email": resp.user.email,
        "access_token": resp.session.access_token,
    }, None


def sign_out():
    """Best-effort -- what actually logs the user out of *this* app is app.py clearing
    st.session_state, not this call succeeding. Supabase's own session (server-side) is
    tidied up here too, but a network hiccup here shouldn't block a user from logging out
    of their own session state."""
    try:
        _get_client().auth.sign_out()
    except Exception as e:
        print(f"[auth] sign_out() call failed (non-fatal, session_state is cleared regardless): {e}", flush=True)


def request_password_reset(email: str) -> tuple[bool, str | None]:
    """Returns (success, error). Deliberately reports success even if the email has no
    account -- Supabase's own `reset_password_for_email` never reveals whether an email is
    registered (same anti-enumeration behavior as sign_up), so the caller should show a
    generic "if that email has an account, a link is on its way" message regardless, rather
    than trying to distinguish the two cases (which isn't possible from this response and
    would be misleading to claim either way -- see the signup duplicate-email finding in
    KNOWN_ISSUES.md for what happens when a caller doesn't respect that). `success=False`
    only for a genuine request failure: rate limiting, malformed email, network error."""
    try:
        _get_client().auth.reset_password_for_email(email, {"redirect_to": APP_URL})
        return True, None
    except Exception as e:
        return False, _friendly_auth_error(e)


def complete_password_reset(access_token: str, refresh_token: str, new_password: str) -> tuple[bool, str | None]:
    """Returns (success, error). This Supabase project uses the "implicit" auth flow, so the
    emailed recovery link already carries a ready-to-use access_token/refresh_token pair
    (in the URL *fragment* -- app.py has a small JS shim that moves them into the query
    string, since fragments never reach the server) rather than a token_hash needing a
    separate verify_otp() exchange. Uses a fresh, dedicated client rather than the shared
    module-level one: unlike the Storage calls in photo_storage.py (which authenticate via a
    custom header and stay stateless), GoTrue's `update_user()` reads whatever session is
    saved *in the client instance's own memory* -- there's no way to pass a bearer token to
    it directly. Recovering a session onto the shared client would risk it bleeding into a
    concurrent, unrelated browser session's sign_in/sign_up call in this same Streamlit
    process; a throwaway client scoped to just this one recovery avoids that entirely."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_ANON_KEY are not set. Add them to your .env file "
            "(see .env.example) -- Project Settings -> API in your Supabase dashboard."
        )
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    try:
        client.auth.set_session(access_token, refresh_token)
    except Exception as e:
        return False, _friendly_auth_error(e)
    try:
        client.auth.update_user({"password": new_password})
        return True, None
    except Exception as e:
        return False, _friendly_auth_error(e)
