"""Small shared UI utilities used across pages."""
import os
import base64
import html
from datetime import date, datetime
import streamlit as st
from db import get_all_vets, create_vet, link_vet_to_profile, get_vets_for_profile, \
    unlink_vet_from_profile, set_primary_vet
import photo_storage

PLACEHOLDER_EMOJI = "🐶"

_MIME_BY_EXT = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}


def _current_access_token() -> str:
    return st.session_state.get("auth_user", {}).get("access_token")


def save_uploaded_photo(uploaded_file) -> str:
    """Upload a Streamlit UploadedFile to this user's Supabase Storage folder and
    return its storage path (stored in profiles.photo_path), or None."""
    if uploaded_file is None:
        return None
    auth_user = st.session_state.get("auth_user")
    return photo_storage.upload_photo(uploaded_file, auth_user["user_id"], auth_user["access_token"])


def _image_data_uri(photo_path: str) -> str:
    photo_bytes = photo_storage.get_photo_bytes(photo_path, _current_access_token())
    if photo_bytes is None:
        return None
    ext = os.path.splitext(photo_path)[1].lower()
    mime = _MIME_BY_EXT.get(ext, "jpeg")
    b64 = base64.b64encode(photo_bytes).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def show_photo(photo_path: str, width: int = 150, height: int = None, responsive: bool = False,
                max_width: int = None, shape: str = "rounded"):
    """Render a photo as a center-cropped square so thumbnails stay uniform regardless of
    the original image's aspect ratio. With responsive=True the square fills its container
    width (e.g. a grid card) instead of using a fixed pixel size — important on mobile where
    a stacked column is much wider than a fixed thumbnail. Pass max_width to cap how large
    it's allowed to grow (useful when the container can become the full phone width).
    shape="circle" for list/feed avatars, shape="rounded" (default) for larger detail-page images."""
    uri = _image_data_uri(photo_path) if photo_path else None
    if responsive:
        cap = f"max-width:{max_width}px;" if max_width else ""
        size_style = f"width:100%;{cap}aspect-ratio:1/1;"
        placeholder_font = "min(15vw, 4rem)"
    else:
        height = height or width
        size_style = f"width:{width}px;height:{height}px;"
        placeholder_font = f"{min(width, height)//2}px"

    radius = "50%" if shape == "circle" else "24px"

    if uri:
        st.markdown(
            f"<img src='{uri}' style='{size_style}object-fit:cover;"
            f"border-radius:{radius};display:block;border:1px solid rgba(255,255,255,0.7);' />",
            unsafe_allow_html=True,
        )
    else:
        # rgba(255,255,255,0.75) -- exact avatar background from the glassmorphism
        # redesign brief, reused here for every placeholder (not just the 40px
        # dashboard-card avatar) so a missing photo looks consistent everywhere.
        st.markdown(
            f"<div style='{size_style}display:flex;align-items:center;"
            f"justify-content:center;font-size:{placeholder_font};background:rgba(255,255,255,0.75);"
            f"border-radius:{radius};border:1px solid rgba(255,255,255,0.7);'>{PLACEHOLDER_EMOJI}</div>",
            unsafe_allow_html=True,
        )


_PUPPY_MASCOT_SVG = """
<div style="width:100%; max-width:{max_width}px; margin:0 auto;">
<svg viewBox="0 0 200 200" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg"
     role="img" aria-label="A cheerful cartoon puppy">
  <style>
    .pf-blob {{ fill: #ffe8d6; }}
    .pf-head {{ fill: #e3a869; }}
    .pf-ear {{ fill: #c98a4f; }}
    .pf-snout {{ fill: #fff6ec; }}
    .pf-feature {{ fill: #4a3225; }}
    .pf-mouth {{ stroke: #4a3225; }}
    .pf-tongue {{ fill: #f28fa3; }}
    .pf-cheek {{ fill: #f6b8a2; opacity: 0.6; }}
    @media (prefers-color-scheme: dark) {{
      .pf-blob {{ fill: #3a2f28; }}
      .pf-head {{ fill: #c98a4f; }}
      .pf-ear {{ fill: #a06b3a; }}
      .pf-snout {{ fill: #f2e4d0; }}
      .pf-feature {{ fill: #2a1c14; }}
      .pf-mouth {{ stroke: #2a1c14; }}
    }}
    @keyframes pf-wag {{
      0%, 100% {{ transform: rotate(0deg); }}
      50% {{ transform: rotate(-6deg); }}
    }}
    .pf-ear-left {{ transform-origin: 60px 60px; animation: pf-wag 3.2s ease-in-out infinite; }}
    .pf-ear-right {{ transform-origin: 140px 60px; animation: pf-wag 3.2s ease-in-out infinite reverse; }}
  </style>
  <circle class="pf-blob" cx="100" cy="105" r="95" />
  <path class="pf-ear pf-ear-left" d="M55 55 Q30 20 45 90 Q70 85 78 65 Z" />
  <path class="pf-ear pf-ear-right" d="M145 55 Q170 20 155 90 Q130 85 122 65 Z" />
  <ellipse class="pf-head" cx="100" cy="105" rx="62" ry="58" />
  <ellipse class="pf-snout" cx="100" cy="130" rx="34" ry="26" />
  <circle class="pf-cheek" cx="62" cy="120" r="12" />
  <circle class="pf-cheek" cx="138" cy="120" r="12" />
  <circle class="pf-feature" cx="78" cy="95" r="7" />
  <circle class="pf-feature" cx="122" cy="95" r="7" />
  <circle fill="white" cx="80" cy="92" r="2.2" />
  <circle fill="white" cx="124" cy="92" r="2.2" />
  <ellipse class="pf-feature" cx="100" cy="120" rx="9" ry="7" />
  <path class="pf-mouth" d="M100 127 Q100 138 88 142" fill="none" stroke-width="4" stroke-linecap="round" />
  <path class="pf-mouth" d="M100 127 Q100 138 112 142" fill="none" stroke-width="4" stroke-linecap="round" />
  <path class="pf-tongue" d="M92 140 Q100 160 108 140 Q100 150 92 140 Z" />
</svg>
</div>
"""


def show_mascot(max_width: int = 220):
    """A friendly inline SVG puppy mascot — no external image, scales responsively,
    and adapts to light/dark themes via prefers-color-scheme."""
    st.markdown(_PUPPY_MASCOT_SVG.format(max_width=max_width), unsafe_allow_html=True)


def tags_to_list(tags_str: str):
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def show_tag_pills(tags_str: str, empty_msg: str = "—"):
    tags = tags_to_list(tags_str)
    if not tags:
        st.caption(empty_msg)
        return
    # html.escape() -- tags are free-typed user input rendered via unsafe_allow_html, so an
    # unescaped "<script>..." or "<img onerror=...>" typed into e.g. "Likes" would render as
    # live HTML rather than text. Only ever shows the owner their own data today, so this was
    # self-XSS at worst, not a cross-user attack -- but profile_type already has a
    # "community_dog" option earmarked for future shared visibility (see KNOWN_ISSUES.md),
    # at which point unescaped tags would become a real stored-XSS risk against other users.
    # rgba(255,255,255,0.7) -- exact glass-pill background from the redesign brief,
    # replacing the old solid-color fill so tags match the frosted card aesthetic.
    pills = " ".join(
        f"<span style='background:rgba(255,255,255,0.7);color:var(--pf-text, #4A3225);"
        f"padding:4px 12px;border-radius:999px;border:1px solid rgba(255,255,255,0.8);"
        f"font-size:0.85em;margin:3px;display:inline-block;'>{html.escape(t)}</span>"
        for t in tags
    )
    st.markdown(pills, unsafe_allow_html=True)


# ---------- Category dots + urgency badges (dashboard cards, profile due-date rows) ----------
# One shared source of truth for "what category does this kind of thing belong to" so the
# dashboard grid and the profile page's due-date rows can't visually drift apart from each
# other. The 2026-07-19 glassmorphism redesign is explicit that color appears ONLY as a small
# dot next to a name (never a full-card fill, and no more per-type icon circles/Font Awesome --
# both retired this pass in favor of the dot). registration doesn't cleanly fit any of the
# four given categories (it's bureaucratic paperwork, not a health/care/social event) -- filed
# under "routine" rather than "health" since it's closer to a logistics chore than a medical
# one; see KNOWN_ISSUES.md for this call, carried over unchanged from the previous pass.
_CATEGORY_BY_TYPE = {
    "vaccination": "health",
    "medication": "health",
    "bath": "care",
    "food_refill": "care",
    "boarding_checkin": "care",
    "own_birthday": "social",
    "friend_birthday": "social",
    "new_profile": "social",
    "registration": "routine",
}
_DEFAULT_CATEGORY = "routine"

# health & routine (logistics-ish) get the amber/orange half of the palette, care & social
# get the teal half, per the redesign brief's own example grouping.
_CATEGORY_DOT_COLOR = {
    "health": "#ff9f4a",    # warm orange
    "routine": "#ffc93c",   # amber/yellow
    "care": "#1fb8b0",      # bright teal
    "social": "#0e7c78",    # deep teal
}


def category_for_type(item_type: str) -> str:
    """Which of the 4 card categories (health/care/social/routine) an item type
    belongs to -- the single source of truth for a card's small category dot
    color (styles.py's --pf-dot-* vars mirror the same 4 values)."""
    return _CATEGORY_BY_TYPE.get(item_type, _DEFAULT_CATEGORY)


def category_dot_html(category: str, size: int = 7) -> str:
    """The one place color signals category in this design -- a small solid dot,
    never a card fill. Returns '' for an unrecognized/None category (e.g. "New
    Pack Members" cards, which have no category concept) rather than guessing."""
    color = _CATEGORY_DOT_COLOR.get(category)
    if not color:
        return ""
    return (
        f"<span style='width:{size}px;height:{size}px;border-radius:50%;"
        f"background:{color};display:inline-block;flex-shrink:0;'></span>"
    )


def days_until_from_iso(iso_date: str):
    """days-from-today for a plain ISO date string, or None if unset/unparseable --
    shared so profile_detail.py's due-date rows compute urgency exactly the same way
    db.get_upcoming_events already does for the dashboard, rather than a second
    slightly-different implementation."""
    if not iso_date:
        return None
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d - date.today()).days


def urgency_tier(days_until: int) -> str:
    """4 buckets, most-to-least urgent. Shared by the badge below and by the dashboard
    card's container key (see home.py), so a card's left accent bar and its top-right
    badge always agree with each other about how urgent it is -- they used to be two
    separate 3-bucket computations (one via st.error/warning/success, one via the CSS
    key) that happened to line up only because both hardcoded the same <=3-day cutoff."""
    if days_until < 0:
        return "overdue"
    if days_until <= 3:
        return "soon"
    if days_until <= 7:
        return "week"
    return "routine"


def urgency_badge_html(days_until: int) -> str:
    """Exact glass-badge values from the redesign brief: semi-transparent white,
    fully rounded, small. Urgency is communicated by the label wording (and a
    slightly bolder weight for the two most time-sensitive tiers), not a second
    color -- color on this app's cards is reserved entirely for the small
    category dot (category_dot_html above)."""
    tier = urgency_tier(days_until)
    if tier == "overdue":
        label = f"{abs(days_until)}d overdue"
    elif tier == "soon":
        if days_until == 0:
            label = "Due today"
        elif days_until == 1:
            label = "Due tomorrow"
        else:
            label = f"Due in {days_until}d"
    elif tier == "week":
        label = "This week"
    else:
        label = "Routine"
    weight = 700 if tier in ("overdue", "soon") else 600
    return (
        "<span style='background:rgba(255,255,255,0.8);color:#2c2a22;padding:3px 10px;"
        f"border-radius:999px;font-size:11px;font-weight:{weight};white-space:nowrap;'>{label}</span>"
    )


def render_urgency_badge(days_until: int):
    """Just the urgency badge, right-aligned -- used on the profile page's
    due-date rows, which (unlike dashboard cards) have no pet avatar/name-row of
    their own to attach the badge to."""
    st.markdown(
        f"<div style='display:flex;justify-content:flex-end;'>{urgency_badge_html(days_until)}</div>",
        unsafe_allow_html=True,
    )


def render_name_row(name: str, category: str = None, days_until: int = None):
    """Top row of a glass card's content area: a small category dot + the name in
    bold (left), the urgency badge (right, if a due date applies). Exactly the
    'name appears once' header -- callers must NOT also prefix the message text
    below it with the name (see render_avatar_card_link). html.escape() on name
    since it's free-typed profile-name text going into raw HTML."""
    dot = category_dot_html(category) if category else ""
    badge = urgency_badge_html(days_until) if days_until is not None else ""
    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:center;gap:8px;'>"
        f"<div style='display:flex;align-items:center;gap:6px;min-width:0;overflow:hidden;'>{dot}"
        f"<span style='font-weight:700;font-size:14px;color:#2c2a22;white-space:nowrap;"
        f"overflow:hidden;text-overflow:ellipsis;'>{html.escape(name)}</span></div>"
        f"{badge}</div>",
        unsafe_allow_html=True,
    )


def render_avatar_card_link(photo_path, name: str, message: str, profile_id, key: str,
                             category: str = None, days_until: int = None, photo_size: int = 40):
    """One dashboard card's full clickable content: a 40px circular avatar, then a
    content column with the name-row (category dot + bold name + urgency badge,
    see render_name_row) on top and the message below it. The avatar AND the name
    are the *only* way to reach the profile from here (no separate 'View profile'
    button anywhere) -- Streamlit buttons can't wrap an image/markdown block
    directly, so the click target is a same-sized transparent button layered on
    top of a position:relative wrapper instead (styles.py's pf_photolink_ rules).

    `message` must NOT repeat `name` -- voice.py's templates already say e.g.
    "Bobby checks into..." on their own, so the name-row above is the only place
    the name is meant to appear as a standalone heading; this function renders
    `message` through plain st.markdown (no unsafe_allow_html, Streamlit's default
    escaping already covers any free-typed text embedded in it) exactly as given,
    with no name prefix added here."""
    with st.container(key=f"pf_photolink_wrap_{key}"):
        cols = st.columns([1, 6])
        with cols[0]:
            show_photo(photo_path, width=photo_size, height=photo_size, shape="circle")
        with cols[1]:
            render_name_row(name, category, days_until)
            st.markdown(message)
        if st.button(" ", key=f"pf_photolink_btn_{key}", help="View profile"):
            st.session_state["selected_profile_id"] = profile_id
            st.switch_page("views/profile_detail.py")


def render_field_group(title: str, rows: list):
    """A labeled section of label-left/value-right rows with a subtle divider between
    them -- used for flat profile properties (Identity, Registration, Spay/Neuter)
    instead of a plain stacked st.write() list. The group itself gets the same glass
    card treatment as every other card (styles.py's .pf-field-group rule); no
    category dot here, since a flat property group has no category/urgency concept.
    `rows` is a list of (label, value) pairs; a falsy value renders as an em dash.
    html.escape() on both since some values (breed, notes, hangout location) are
    free-typed user input rendered via unsafe_allow_html -- same reasoning as
    show_tag_pills."""
    row_html = "".join(
        f"<div class='pf-field-row'><span class='pf-field-label'>{html.escape(str(label))}</span>"
        f"<span class='pf-field-value'>{html.escape(str(value)) if value else '—'}</span></div>"
        for label, value in rows
    )
    st.markdown(f"<div class='pf-field-group-title'>{html.escape(title)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='pf-field-group'>{row_html}</div>", unsafe_allow_html=True)


_ADD_NEW_VET_OPTION = "➕ Add a new vet..."


def queue_toast(message: str, icon: str = "✅"):
    """Queue a toast to fire on the *next* script run. st.toast() called immediately
    before st.rerun() never reaches the browser — the rerun cuts the run off before the
    message is flushed to the frontend, so the confirmation silently never appears. This
    stashes the message instead; render_queued_toast() (called once at page top level)
    fires it on the fresh run that follows the rerun, where it displays normally."""
    st.session_state["_toast_queue"] = (message, icon)


def render_queued_toast():
    """Call once near the top of a page to fire a toast queued by queue_toast()."""
    queued = st.session_state.get("_toast_queue")
    if queued:
        st.session_state["_toast_queue"] = None
        st.toast(queued[0], icon=queued[1])


def request_delete(item_label: str, on_confirm, success_msg: str = None):
    """Queue a delete for confirmation. Every edit surface on the profile page is now a
    st.dialog, and Streamlit forbids opening a dialog from inside another dialog — so a
    Delete click inside an edit dialog can't open the confirm dialog directly. Instead
    this stashes the request in session_state and closes the current dialog via rerun;
    render_pending_delete_dialog() (called once at page top level, outside any dialog)
    picks it up on the next run and shows the actual confirmation."""
    st.session_state["_pending_delete"] = {
        "label": item_label, "on_confirm": on_confirm, "success_msg": success_msg,
    }
    st.rerun()


def render_pending_delete_dialog():
    """Call once near the top of a page, outside any dialog, to surface a delete
    confirmation queued by request_delete() on the previous run."""
    pending = st.session_state.get("_pending_delete")
    if pending:
        _confirm_delete_modal(pending["label"], pending["on_confirm"], pending["success_msg"])


def _clear_pending_delete():
    st.session_state["_pending_delete"] = None


@st.dialog("Confirm delete", on_dismiss=_clear_pending_delete)
def _confirm_delete_modal(item_label, on_confirm, success_msg):
    # Streamlit dialogs are dismissible by default (X button, Escape, click outside)
    # independent of the Yes/Cancel buttons below — without on_dismiss=, dismissing
    # this way skipped both handlers, so _pending_delete never got cleared. It would
    # then resurface on the very next profile_detail.py page visited (any profile,
    # not just this one), showing a confirm dialog for an unrelated record and
    # blocking that page's own buttons behind its modal backdrop until dealt with.
    st.warning(f"Delete {item_label}? This can't be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Yes, delete", key="delete_confirm_yes", use_container_width=True):
        on_confirm()
        st.session_state["_pending_delete"] = None
        queue_toast(success_msg or f"{item_label} deleted.", icon="🗑️")
        st.rerun()
    if c2.button("Cancel", key="cancel_confirm_delete", use_container_width=True):
        st.session_state["_pending_delete"] = None
        st.rerun()


@st.dialog("Link a vet")
def _link_vet_dialog(profile_id: int, owner_id: str, key_prefix: str, available_vets, choice_labels):
    # Lives outside the form, same reactive pattern as the Add Friend / Identity dialogs --
    # picking an existing vet swaps the "new vet" fields for a read-only look at that vet's
    # actual stored details instead of leaving unrelated, inert text boxes sitting there
    # (they used to stay visible and editable no matter what was chosen, which looked like
    # the selection should populate them and didn't -- anything typed into them was just
    # silently discarded if an existing vet ended up selected).
    choice_index = st.selectbox(
        "Choose a vet", options=range(len(choice_labels)),
        format_func=lambda i: choice_labels[i], key=f"{key_prefix}_choice"
    )

    with st.form(f"{key_prefix}_link_form_dialog", clear_on_submit=True):
        if choice_index == 0:
            st.caption("Fill in the fields below to add a brand new vet:")
            new_name = st.text_input("Vet name", key=f"{key_prefix}_new_name")
            new_clinic = st.text_input("Clinic name", key=f"{key_prefix}_new_clinic")
            new_phone = st.text_input("Phone number", key=f"{key_prefix}_new_phone")
            new_address = st.text_input("Address", key=f"{key_prefix}_new_address")
            new_notes = st.text_area("Notes (optional)", key=f"{key_prefix}_new_notes")
        else:
            chosen = available_vets[choice_index - 1]
            st.caption("Linking to this vet's existing entry in your shared vet directory:")
            st.markdown(f"**{chosen['vet_name']}**" + (f" — {chosen['clinic_name']}" if chosen["clinic_name"] else ""))
            if chosen["phone"]:
                st.write(f"📞 {chosen['phone']}")
            if chosen["address"]:
                st.write(f"📍 {chosen['address']}")
            if chosen["notes"]:
                st.write(chosen["notes"])
            new_name = new_clinic = new_phone = new_address = new_notes = None
        is_primary = st.checkbox("Set as primary vet", key=f"{key_prefix}_new_primary")
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Link Vet", use_container_width=True)
        cancelled = c2.form_submit_button("Cancel", key=f"cancel_{key_prefix}_link", use_container_width=True)
    if submitted:
        if choice_index == 0 and not new_name:
            st.warning("Vet name is required to add a new vet.")
        else:
            if choice_index == 0:
                vet_id = create_vet(new_name, new_clinic, new_phone, new_address, new_notes, owner_id)
            else:
                vet_id = available_vets[choice_index - 1]["id"]
            link_vet_to_profile(profile_id, vet_id, owner_id, is_primary)
            queue_toast("Vet linked.")
            st.rerun()
    if cancelled:
        st.rerun()


def render_vet_picker(profile_id: int, owner_id: str, key_prefix: str = "vet"):
    """Reusable 'select a vet or add one inline' widget. Shows vets already linked to
    this profile (with unlink / set-primary controls), then a button that opens a dialog
    to link an existing vet from this user's own vet directory or create a brand new one."""
    linked = get_vets_for_profile(profile_id, owner_id)
    if linked:
        for v in linked:
            label = f"{'⭐ ' if v['is_primary'] else ''}{v['vet_name']}"
            if v["clinic_name"]:
                label += f" — {v['clinic_name']}"
            with st.expander(label):
                if v["phone"]:
                    st.write(f"📞 {v['phone']}")
                if v["address"]:
                    st.write(f"📍 {v['address']}")
                if v["notes"]:
                    st.write(v["notes"])
                cols = st.columns(2)
                if not v["is_primary"]:
                    if cols[0].button("Set as primary", key=f"{key_prefix}_primary_{v['link_id']}", use_container_width=True):
                        set_primary_vet(profile_id, v["link_id"], owner_id)
                        queue_toast(f"{v['vet_name']} set as primary vet.", icon="⭐")
                        st.rerun()
                # Unlinking is low-stakes and fully reversible (the vet stays in the
                # shared directory, ready to relink), so it intentionally skips the
                # confirm-delete dialog and the red danger styling used for real deletes.
                if cols[1].button("Unlink", key=f"unlink_{key_prefix}_{v['link_id']}", use_container_width=True):
                    unlink_vet_from_profile(v["link_id"], owner_id)
                    queue_toast(f"{v['vet_name']} unlinked.", icon="↩️")
                    st.rerun()
    else:
        st.caption("No vets linked yet.")

    linked_vet_ids = {v["vet_id"] for v in linked}
    # Only offer vets not already linked to this profile — avoids redundant re-linking
    # and, since two vets can legitimately share a display label (same name, same/no
    # clinic), selection below is by list position, not by that label string.
    available_vets = [v for v in get_all_vets(owner_id) if v["id"] not in linked_vet_ids]
    choice_labels = [_ADD_NEW_VET_OPTION] + [
        f"{v['vet_name']} — {v['clinic_name'] or 'no clinic listed'}" for v in available_vets
    ]

    if st.button("➕ Link a vet", key=f"btn_link_{key_prefix}", use_container_width=True):
        _link_vet_dialog(profile_id, owner_id, key_prefix, available_vets, choice_labels)
