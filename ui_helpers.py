"""Small shared UI utilities used across pages."""
import os
import base64
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
            f"border-radius:{radius};display:block;border:2px solid var(--pf-border, #F0D9C0);' />",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='{size_style}display:flex;align-items:center;"
            f"justify-content:center;font-size:{placeholder_font};background:var(--pf-card-bg-alt, #FFEAD8);"
            f"border-radius:{radius};border:2px solid var(--pf-border, #F0D9C0);'>{PLACEHOLDER_EMOJI}</div>",
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
    pills = " ".join(
        f"<span style='background:var(--pf-card-bg-alt, #FFEAD8);color:var(--pf-text, #4A3225);"
        f"padding:4px 12px;border-radius:999px;border:1.5px solid var(--pf-border, #F0D9C0);"
        f"font-size:0.85em;margin:3px;display:inline-block;'>{t}</span>"
        for t in tags
    )
    st.markdown(pills, unsafe_allow_html=True)


# ---------- Icon circles + urgency badges (dashboard cards, profile due-date rows) ----------
# One shared source of truth for "what icon/color represents this kind of thing" so the
# dashboard grid and the profile page's due-date rows can't visually drift apart from each
# other over time. Icons are Font Awesome Free glyphs loaded via CDN (styles.py) rather than
# emoji, per an explicit choice to prioritize a sharper "app-like" look here over this
# codebase's usual no-external-dependency default (inline SVG mascot, base64-embedded
# photos) -- see KNOWN_ISSUES.md for the tradeoff this brings (unverified in a real browser,
# no fallback if the CDN is ever blocked).
# Third element is the icon glyph's own color. Fixed near-white (#FFFBF5) works for every
# background here except --pf-accent (gold) -- it stays light-toned in both light *and*
# dark mode (see styles.py), so white-on-gold reads as low-contrast in both, not just one.
# food_refill gets a fixed dark color instead, the one case that needs it.
_TYPE_ICON = {
    "vaccination": ("fa-syringe", "var(--pf-primary)", "#FFFBF5"),
    "medication": ("fa-pills", "var(--pf-pink)", "#FFFBF5"),
    "bath": ("fa-droplet", "var(--pf-blue)", "#FFFBF5"),
    "food_refill": ("fa-bowl-food", "var(--pf-accent)", "#4A3225"),
    "own_birthday": ("fa-cake-candles", "var(--pf-lavender)", "#FFFBF5"),
    "friend_birthday": ("fa-cake-candles", "var(--pf-lavender)", "#FFFBF5"),
    "registration": ("fa-file-lines", "var(--pf-secondary)", "#FFFBF5"),
    "boarding_checkin": ("fa-suitcase-rolling", "var(--pf-primary-hover)", "#FFFBF5"),
    "new_profile": ("fa-paw", "var(--pf-pink)", "#FFFBF5"),
}
_DEFAULT_ICON = ("fa-paw", "var(--pf-text-muted)", "#FFFBF5")


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


def icon_circle_html(item_type: str, size: int = 40) -> str:
    icon_class, bg, icon_color = _TYPE_ICON.get(item_type, _DEFAULT_ICON)
    font_size = round(size * 0.42)
    return (
        f"<div style='width:{size}px;height:{size}px;border-radius:50%;background:{bg};"
        f"display:flex;align-items:center;justify-content:center;flex-shrink:0;'>"
        f"<i class='fa-solid {icon_class}' style='color:{icon_color};font-size:{font_size}px;'></i></div>"
    )


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
    """Color intensity steps down as urgency drops: overdue/due-soon are the most
    saturated (danger red / brand orange), "this week" is medium (gold), and routine
    items are deliberately calm and muted -- low-contrast on purpose, so a screen full
    of upcoming items doesn't read as uniformly alarming."""
    tier = urgency_tier(days_until)
    if tier == "overdue":
        label, bg, color, border = f"{abs(days_until)}d overdue", "var(--pf-danger)", "#FFFBF5", "transparent"
    elif tier == "soon":
        if days_until == 0:
            label = "Due today"
        elif days_until == 1:
            label = "Due tomorrow"
        else:
            label = f"Due in {days_until}d"
        bg, color, border = "var(--pf-primary)", "#FFFBF5", "transparent"
    elif tier == "week":
        # Fixed dark text, not var(--pf-text) -- --pf-accent (gold) stays light-toned in
        # both light *and* dark mode (see styles.py), so the theme-flipping text color
        # would go light-on-light in dark mode instead of tracking the background.
        label, bg, color, border = "This week", "var(--pf-accent)", "#4A3225", "transparent"
    else:
        label, bg, color, border = "Routine", "var(--pf-card-bg-alt)", "var(--pf-text-muted)", "var(--pf-border)"
    return (
        f"<span style='background:{bg};color:{color};padding:4px 12px;border-radius:999px;"
        f"font-size:0.78em;font-weight:700;white-space:nowrap;border:1.5px solid {border};'>{label}</span>"
    )


def render_card_header(item_type: str, days_until: int = None):
    """Icon circle top-left + (if days_until is given) urgency badge top-right, as one
    row. days_until=None renders just the icon circle alone (e.g. 'New Pack Members'
    cards, which have no due date/urgency concept at all)."""
    badge = urgency_badge_html(days_until) if days_until is not None else ""
    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;'>"
        + icon_circle_html(item_type) + badge + "</div>",
        unsafe_allow_html=True,
    )


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
