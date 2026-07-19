"""Central place for Pawfolio's visual theme. Injected once at app startup (app.py).

2026-07-19: rebuilt around a glassmorphism direction that is the single source of
truth for the app's look, superseding every earlier styling pass — soft layered
radial-gradient background, frosted translucent cards, a small sunshine/teal
palette used only as tiny category dots (never full-card fills). Layered on top of
Streamlit's default layout via CSS only — no layout primitives are rebuilt, existing
st.columns/st.container/st.expander/st.tabs structure is untouched.

Dark mode is intentionally NOT themed in this pass: every background/card value
below is a fixed light color given exactly as specified, with no dark-mode
equivalent provided. The previous design's dark-mode block flipped text to a light
color for readability against a dark background — running that same logic against
this new, permanently-light gradient would put light text on a light background and
break readability outright, so it's been removed rather than left in as a bug. See
KNOWN_ISSUES.md.
"""

PAWFOLIO_CSS = """
<style>
:root {
    --pf-bg: #fbfaf5;
    --pf-card-bg-alt: #FFEAD8;
    --pf-border: #F0D9C0;
    --pf-primary: #D97757;
    --pf-primary-hover: #C1613F;
    --pf-danger: #C1613F;
    --pf-text: #4A3225;
    --pf-text-muted: #8A7160;
    --pf-input-bg: #FFFDFA;
    --pf-radius-lg: 24px;
    --pf-radius-md: 16px;
    --pf-radius-sm: 10px;
    --pf-font-heading: "Segoe UI Rounded", "SF Pro Rounded", ui-rounded, "Trebuchet MS", Verdana, sans-serif;

    /* Segmented-control active fill (top nav pill, profile-page tabs) -- one
       accent, picked from the palette below, used consistently everywhere a tab
       needs to show "this one is selected." */
    --pf-accent-active: #1fb8b0;
    --pf-accent-active-hover: #178f89;

    /* Category palette -- amber/orange family for health & logistics-ish items,
       teal family for care & social, per the brief's own grouping example. Used
       ONLY as a small 7px dot next to a card's name, never as a card fill --
       see ui_helpers.category_dot_html(). */
    --pf-dot-health: #ff9f4a;
    --pf-dot-routine: #ffc93c;
    --pf-dot-care: #1fb8b0;
    --pf-dot-social: #0e7c78;
}

html, body { overflow-x: hidden; }

/* Desktop/wide viewports: constrain and center the main content column instead of
   stretching cards and text edge-to-edge on a wide monitor. This is only an upper
   bound -- on a phone the block is already narrower than the cap, so it has no
   effect there, and the mobile media query further down still controls side
   padding independently. */
[data-testid="stMainBlockContainer"] {
    max-width: 650px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}

/* ---------- Page background: three soft circular glows on a near-white base ----------
   Applied to exactly ONE element (stAppViewContainer, the true full-page box) and
   nowhere else -- the previous pass set the identical background independently on
   stAppViewContainer/stApp/stMain all at once, which are nested inside each other.
   Each one has a slightly different box (padding/scrollbars), so each rendered its
   OWN copy of the gradient positioned relative to ITS OWN box, and the innermost
   one's edges showed as a visible seam over the outer ones -- that's what was seen
   as a "hard banded diagonal" line, not a CSS override fight. Fixed by painting the
   gradient once and forcing every descendant that could otherwise paint over it
   (stApp, stMain, stMainBlockContainer, stHeader) to stay fully transparent.

   The gradient itself also needed one addition beyond the exact given values: an
   explicit circle size (550px). radial-gradient's size defaults to "farthest-corner"
   when no size is given, which for a full-viewport box means each glow's "48%
   transparent" stop lands 40-50% of the way to the FARTHEST corner of the whole
   screen -- on a typical laptop width that's 800px+, so the "soft spot" ends up
   covering most of the visible area instead of staying a contained glow, which is
   the other half of what read as a hard, screen-wide color blend rather than "most
   of the screen staying neutral/white." The position/color/stop-percentage values
   below are unchanged from the exact spec; only this implicit sizing is now
   explicit, which is required to get the "soft, separate, faded" result actually
   described. See KNOWN_ISSUES.md. */
[data-testid="stAppViewContainer"] {
    background:
      radial-gradient(circle 550px at 18% 15%, #ffe27a 0%, transparent 48%),
      radial-gradient(circle 550px at 85% 20%, #6fd6d1 0%, transparent 48%),
      radial-gradient(circle 550px at 50% 95%, #ffd166 0%, transparent 45%),
      #fbfaf5 !important;
}
[data-testid="stApp"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stHeader"] {
    background: transparent !important;
}
[data-testid="stMainBlockContainer"] {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* ---------- Typography ---------- */
[data-testid="stMainBlockContainer"], [data-testid="stApp"] {
    color: var(--pf-text);
}
h1, h2, h3, [data-testid="stHeading"] {
    font-family: var(--pf-font-heading);
    color: var(--pf-text);
    font-weight: 700;
    letter-spacing: 0.01em;
}
[data-testid="stCaptionContainer"] {
    color: var(--pf-text-muted);
}
p, li, label, [data-testid="stMarkdownContainer"] {
    line-height: 1.65;
}

/* ---------- Buttons ---------- */
/* Three-tier hierarchy so a screen full of buttons doesn't shout at one volume:
   1. Solid fill (default) — the one action a screen actually wants you to take:
      Save, Create Profile, confirm-delete's "Yes, delete", View, Link Vet, etc.
   2. Dashed outline (key prefix "btn_add_"/"btn_link_") — "add something new".
      Reads like a blank card waiting to be filled in, distinct from "commit this
      change", and there are 9 of these on the profile page alone so they needed
      their own, lighter register.
   3. Ghost outline (key prefix "cancel_"/"mute_") — recedes on purpose; every dialog's
      Cancel sits next to a solid Save/Add and shouldn't compete with it.
   Danger (key prefix "delete_") stays its own red-outline tier, defined below.
   This tier system wasn't part of this redesign's brief (which scopes color to the
   background/cards/dots/nav) and is left as-is. */
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondaryFormSubmit"] {
    background-color: var(--pf-primary);
    color: #FFFBF5;
    border: none;
    border-radius: var(--pf-radius-md);
    font-weight: 600;
    padding: 0.45rem 1.1rem;
    min-height: 2.5rem;
    box-shadow: 0 2px 6px rgba(74, 50, 37, 0.12);
    transition: background-color 0.15s ease, transform 0.1s ease, box-shadow 0.15s ease;
}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background-color: var(--pf-primary-hover);
    color: #FFFBF5;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(74, 50, 37, 0.16);
}
[data-testid="stBaseButton-secondary"]:active,
[data-testid="stBaseButton-secondaryFormSubmit"]:active {
    transform: scale(0.98);
}
[data-testid="stBaseButton-secondary"]:disabled,
[data-testid="stBaseButton-secondaryFormSubmit"]:disabled {
    background-color: var(--pf-border);
    color: var(--pf-text-muted);
    box-shadow: none;
    transform: none;
}

/* tier 2: "add something new" — dashed outline, quieter than a commit action */
[class*="st-key-btn_add_"] [data-testid="stBaseButton-secondary"],
[class*="st-key-btn_link_"] [data-testid="stBaseButton-secondary"] {
    background-color: transparent;
    color: var(--pf-primary);
    border: 1.5px dashed var(--pf-primary);
    box-shadow: none;
    font-weight: 600;
}
[class*="st-key-btn_add_"] [data-testid="stBaseButton-secondary"]:hover,
[class*="st-key-btn_link_"] [data-testid="stBaseButton-secondary"]:hover {
    background-color: var(--pf-card-bg-alt);
    color: var(--pf-primary-hover);
    border-color: var(--pf-primary-hover);
    box-shadow: none;
    transform: none;
}

/* tier 3: ghost — Cancel buttons recede next to a solid Save/Add/View */
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondary"],
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondaryFormSubmit"] {
    background-color: transparent;
    color: var(--pf-text-muted);
    border: 1.5px solid var(--pf-border);
    box-shadow: none;
    font-weight: 600;
}
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondary"]:hover,
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background-color: var(--pf-card-bg-alt);
    color: var(--pf-text);
    border-color: var(--pf-text-muted);
    box-shadow: none;
    transform: none;
}

/* Top nav: Home/All the Pups as a pill-shaped segmented control, filled with the
   single active-accent color (--pf-accent-active, the palette's bright teal, per
   the brief's own example) when selected, muted neutral text otherwise. The
   container itself (key="nav_pills") is the rounded pill backdrop; each button is
   one segment. app.py switches a button's key between the plain and "_active"
   variant based on which page is currently showing, since that's the only way to
   express "this one is selected right now" through Streamlit's own button.

   Each segment is actually *two* buttons (key suffix "_full" = icon+text,
   "_icon" = icon-only) with only one shown at a time via the media query below --
   Streamlit's button label can't be conditionally swapped by viewport, so both
   render and CSS picks which one is visible, rather than letting "Home"/"Pups"
   text wrap to two lines on a narrow screen.

   All 4 buttons are DIRECT children of nav_pills now (app.py) -- an earlier
   version put them inside a nested st.columns(2) split (one column per segment),
   which needed its own flex/stacking override on top of nav_pills' own, and on
   mobile that second layer of override didn't fully apply: one segment ("Pups")
   ended up rendering as Streamlit's own default button box instead of picking up
   the pill's shared styling, which is what looked like a second, unstyled,
   oversized capsule floating outside the real pill. With no nested columns left,
   there's only ONE flex row to control (nav_pills' own stVerticalBlock, below),
   not two, so there's nothing left for an override to miss. */
[class*="st-key-nav_pills"] {
    display: inline-flex;
    width: fit-content;
    background-color: rgba(255, 255, 255, 0.55);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.7);
    border-radius: 999px;
    padding: 0.25rem;
}
/* Sequential elements inside a plain st.container() stack vertically by
   default (Streamlit's normal block flow) -- turned into a single-row flex
   layout here, sized to its own content only (no stretching to fill whatever
   width its parent column happens to have). */
[class*="st-key-nav_pills"] > [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center;
    gap: 0.25rem;
    width: fit-content;
}
.st-key-nav_home_full button, .st-key-nav_home_icon button,
.st-key-nav_home_full_active button, .st-key-nav_home_icon_active button,
.st-key-nav_profiles_full button, .st-key-nav_profiles_icon button,
.st-key-nav_profiles_full_active button, .st-key-nav_profiles_icon_active button {
    font-size: 0.95rem;
    line-height: 1;
    padding: 0.5rem 1rem;
    min-height: 2.5rem;
    border-radius: 999px;
    white-space: nowrap;
    box-shadow: none;
    border: none;
    font-weight: 600;
}
.st-key-nav_home_full button, .st-key-nav_home_icon button,
.st-key-nav_profiles_full button, .st-key-nav_profiles_icon button {
    background-color: transparent;
    color: var(--pf-text-muted);
}
.st-key-nav_home_full button:hover, .st-key-nav_home_icon button:hover,
.st-key-nav_profiles_full button:hover, .st-key-nav_profiles_icon button:hover {
    background-color: rgba(255, 255, 255, 0.5);
    color: var(--pf-text);
}
.st-key-nav_home_full_active button, .st-key-nav_home_icon_active button,
.st-key-nav_profiles_full_active button, .st-key-nav_profiles_icon_active button {
    background-color: var(--pf-accent-active);
    color: #FFFBF5;
}
.st-key-nav_home_full_active button:hover, .st-key-nav_home_icon_active button:hover,
.st-key-nav_profiles_full_active button:hover, .st-key-nav_profiles_icon_active button:hover {
    background-color: var(--pf-accent-active-hover);
    color: #FFFBF5;
}
/* Desktop default: icon+text segment shown, icon-only segment hidden -- swapped
   the other way round below the mobile breakpoint (see the media query). */
.st-key-nav_home_icon, .st-key-nav_home_icon_active,
.st-key-nav_profiles_icon, .st-key-nav_profiles_icon_active {
    display: none;
}

/* The outer top_nav row (nav_pills | empty spacer | logout, app.py's
   nav_cols = st.columns([3.4, 7.6, 2])) needs the same row-not-stacked
   treatment nav_pills' own inner row gets, or it breaks into 3 separate
   full-width stacked bars below the mobile breakpoint -- an extra blank bar for
   the empty spacer column alone is real, visible dead space at the top of the
   page, independent of anything happening inside nav_pills itself. */
[class*="st-key-top_nav"] [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center;
}
/* Tightened vertical rhythm around the nav bar -- Streamlit's default spacing
   between stacked top-level elements (the nav row, then the divider below it,
   then the page's own header content) is generous enough on its own to read as
   an oversized gap once the nav row itself is just a compact pill plus a small
   logout button, not a full-height banner. */
[class*="st-key-top_nav"] {
    margin-bottom: -0.5rem;
}
[class*="st-key-top_nav"] + [data-testid="stElementContainer"] hr {
    margin: 0.5rem 0;
}

/* ---------- Mute-bell toggle (Upcoming cards) ---------- */
/* key prefix "mutebell_" -- a small 24px circular icon button in a card corner,
   replacing what used to be a full outlined "Mute email for this" button.

   U+1F515 (🔕, "BELL WITH CANCELLATION STROKE") was tried first and confirmed
   correct at the Unicode level, but still read as a "blocked/prohibited" symbol
   rather than "mute" once rendered -- likely a font-fallback issue rendering a
   slashed-circle shape at small size regardless of which specific bell glyph was
   used. Switched to the plain, unambiguous bell (U+1F514 🔔) for BOTH states
   instead of a different glyph for "muted": the resting/clickable state is a
   normal-opacity 🔔, and "already muted" is the *same* glyph dimmed/grayscaled
   (see home.py) rather than swapped for a different, still-emoji-rendering-
   dependent icon. A plain bell shape doesn't have the same "is this a
   prohibition sign" ambiguity a slashed circle does, even in a monochrome
   fallback font. Kept the color-emoji font-family hint from the previous
   attempt regardless, since it's a real, valid hardening either way. */
[class*="st-key-mutebell_"] [data-testid="stBaseButton-secondary"] {
    background-color: rgba(255, 255, 255, 0.55);
    color: var(--pf-text);
    border: none;
    box-shadow: none;
    width: 24px;
    height: 24px;
    min-width: 24px;
    min-height: 24px;
    padding: 0;
    border-radius: 50%;
    font-size: 14px;
    line-height: 1;
    font-family: "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji", sans-serif;
}
[class*="st-key-mutebell_"] [data-testid="stBaseButton-secondary"]:hover {
    background-color: rgba(255, 255, 255, 0.8);
    box-shadow: none;
    transform: none;
}

/* ---------- Photo/name as one clickable unit (dashboard + profile cards) ---------- */
/* Streamlit buttons can't wrap an <img>/markdown block directly, so "make the
   avatar and name both tappable" is done by layering a same-sized transparent
   button (key "pf_photolink_btn_...") on top of a position:relative wrapper (key
   "pf_photolink_wrap_...") holding the avatar+text -- see
   ui_helpers.render_avatar_card_link(). This is the *only* way to reach a profile
   from these cards (no "View profile" button anywhere on them anymore).

   IMPORTANT: this wrapper must NEVER get `overflow: hidden` -- a previous pass
   added it here specifically to keep the avatar circle from visually spilling
   past the card edge, but since this wrapper also contains the full wrapping
   message text below the name-row, `overflow: hidden` on it clipped that text
   instead (the confirmed cause of messages getting cut off mid-sentence). The
   avatar can't spill regardless, since show_photo() gives it a fixed pixel
   width/height and flex-shrink:0 by nature of being a dedicated column -- the
   overflow:hidden wasn't fixing a real containment problem, it was just also
   clipping real content. Kept position:relative only. */
[class*="st-key-pf_photolink_wrap_"] {
    position: relative;
    cursor: pointer;
}
[class*="st-key-pf_photolink_btn_"] {
    position: absolute;
    inset: 0;
    z-index: 2;
    margin: 0;
}
[class*="st-key-pf_photolink_btn_"] button {
    width: 100%;
    height: 100%;
    min-height: unset;
    opacity: 0;
    padding: 0;
    border: none;
    background: transparent;
    box-shadow: none;
    cursor: pointer;
}
/* Every nested st.columns() inside one of these cards (avatar|content, and the
   outer content|mute-bell split in home.py) must be free to shrink and wrap --
   flex children default to min-width:auto, which lets a long/wide sibling refuse
   to shrink below its own content width and instead push a narrower sibling
   (the mute-bell) out of the visible card entirely on a narrow screen. This is
   the confirmed cause of the mute-bell "disappearing" on mobile -- not a
   display:none rule, an actual flex layout squeeze. */
[class*="st-key-card_evt_"] [data-testid="stColumn"],
[class*="st-key-card_new_"] [data-testid="stColumn"],
[class*="st-key-card_profile_header"] [data-testid="stColumn"] {
    min-width: 0 !important;
}
/* ...except the mute-bell's own column, which needs the opposite: a guaranteed
   floor so the general min-width:0 above doesn't let IT shrink away to nothing.
   Scoped to the outer content/mute-bell split specifically (a direct child of the
   "cardrow_" wrapper in home.py), not the nested avatar/content split one level
   deeper inside it, via the ">" child combinators. */
[class*="st-key-cardrow_"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
    min-width: 32px !important;
    flex-shrink: 0 !important;
    flex-grow: 0 !important;
}

/* delete/danger buttons opt in via key="...delete..." — covers both plain buttons and
   form-submit buttons, since record "Delete" actions live inside st.form rows. */
[class*="st-key-delete_"] [data-testid="stBaseButton-secondary"],
[class*="st-key-delete_"] [data-testid="stBaseButton-secondaryFormSubmit"] {
    background-color: transparent;
    color: var(--pf-danger);
    border: 1.5px solid var(--pf-danger);
    box-shadow: none;
}
[class*="st-key-delete_"] [data-testid="stBaseButton-secondary"]:hover,
[class*="st-key-delete_"] [data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background-color: var(--pf-danger);
    color: #FFFBF5;
}

/* small round icon buttons on the profile header: edit (pencil) and delete (trash) —
   both used to be their own tabs; now they're one tap from anywhere on the page */
.st-key-header_edit button, .st-key-header_delete button {
    font-size: 1.15rem;
    line-height: 1;
    padding: 0.4rem 0.7rem;
    min-width: 2.6rem;
    min-height: 2.6rem;
    border-radius: 999px;
    background-color: rgba(255, 255, 255, 0.55);
    color: var(--pf-text);
    box-shadow: none;
    border: 1px solid rgba(255, 255, 255, 0.7);
}
.st-key-header_edit button:hover {
    background-color: rgba(255, 255, 255, 0.8);
    border-color: var(--pf-accent-active);
    transform: none;
}
.st-key-header_delete button:hover {
    background-color: rgba(255, 255, 255, 0.8);
    border-color: var(--pf-danger);
    color: var(--pf-danger);
    transform: none;
}
/* ---------- Brand mark (top bar, left) ---------- */
/* Compact icon+text -- icon-only below the mobile breakpoint (same 640px cutoff
   the nav pills use), via CSS hiding the text span rather than a second
   Streamlit element, since this is static markup, not an interactive widget
   whose label Streamlit itself can't conditionally swap. */
.pf-brand {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-family: var(--pf-font-heading);
    font-weight: 700;
    font-size: 1.15rem;
    color: var(--pf-text);
    white-space: nowrap;
    padding: 0.4rem 0;
}
.pf-brand-icon { font-size: 1.35rem; line-height: 1; }

/* ---------- Account menu (hamburger, top bar right) ---------- */
/* key "account_menu" -- an st.popover(), the closest native Streamlit primitive
   to a dropdown/slide-out account menu (see KNOWN_ISSUES.md for how it behaves
   here specifically). Trigger button styled the same small-circular-icon
   register as the profile header's edit/delete buttons. */
.st-key-account_menu button {
    font-size: 1.2rem;
    line-height: 1;
    padding: 0.4rem 0.7rem;
    min-width: 2.6rem;
    min-height: 2.6rem;
    border-radius: 999px;
    background-color: rgba(255, 255, 255, 0.55);
    color: var(--pf-text);
    box-shadow: none;
    border: 1px solid rgba(255, 255, 255, 0.7);
}
.st-key-account_menu button:hover {
    background-color: rgba(255, 255, 255, 0.8);
    border-color: var(--pf-accent-active);
    transform: none;
}
/* The popover's floating panel content -- matches the glass aesthetic used
   everywhere else instead of Streamlit's plain white default. */
[data-testid="stPopoverBody"] {
    background: rgba(255, 255, 255, 0.85) !important;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.7) !important;
    border-radius: 16px !important;
}

/* ---------- Inputs ---------- */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: var(--pf-input-bg);
    border: 1.5px solid var(--pf-border) !important;
    border-radius: var(--pf-radius-sm) !important;
    color: var(--pf-text);
}
/* Date input / selectbox / multiselect render their visible "box" on an inner BaseWeb
   wrapper div (auto-generated class names, not the <input> itself), so target it
   structurally instead of relying on those unstable classes. */
[data-testid="stDateInput"] > div > div,
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    background-color: var(--pf-input-bg) !important;
    border: 1.5px solid var(--pf-border) !important;
    border-radius: var(--pf-radius-sm) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--pf-primary) !important;
    box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.15) !important;
}
[data-testid="stDateInputField"] input {
    color: var(--pf-text);
}
[data-testid="stFileUploaderDropzone"] {
    background-color: var(--pf-card-bg-alt) !important;
    border: 1.5px dashed var(--pf-border) !important;
    border-radius: var(--pf-radius-md) !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background-color: var(--pf-primary);
    color: #FFFBF5;
    border-radius: var(--pf-radius-sm);
}
input[type="checkbox"], input[type="radio"] {
    accent-color: var(--pf-primary);
}

/* ==================================================================
   Glass cards -- the ONE card treatment used everywhere: dashboard
   Upcoming/New-Pack-Members cards, "All the Pups" profile cards, profile-page
   due-date record rows, the Identity/Registration/Spay-Neuter field groups, AND
   the login/signup form (stForm) -- that last one was missing entirely in the
   previous pass (forms were deliberately left out of scope), which is why it
   rendered as a flat solid color mismatched against the new background instead
   of picking up any of this treatment. Exact values as specified. No fixed
   height anywhere in this block, on purpose -- a card must grow with its
   content, never clip or overflow it (this was a named bug in an earlier
   version; explicitly re-checked this pass, see KNOWN_ISSUES.md).
   ================================================================== */
[class*="st-key-card_"],
[class*="st-key-profile_card_"],
[class*="st-key-card_rec_"],
.pf-field-group,
[data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.6) !important;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.7) !important;
    border-radius: 18px !important;
    padding: 15px 17px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
    height: auto !important;
    min-height: 0 !important;
    overflow: visible;
    transition: box-shadow 0.15s ease;
}
/* backdrop-filter isn't universally supported (older Safari/Firefox, some
   in-app webviews) -- @supports auto-detects that at render time and swaps in a
   solid semi-transparent white instead of silently losing the translucency
   effect. Which branch actually fires couldn't be confirmed visually this pass
   (no browser tool available here) -- see KNOWN_ISSUES.md. */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
    [class*="st-key-card_"],
    [class*="st-key-profile_card_"],
    [class*="st-key-card_rec_"],
    .pf-field-group,
    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.85) !important;
    }
}
[class*="st-key-card_"] [data-testid="stVerticalBlock"],
[class*="st-key-profile_card_"] [data-testid="stVerticalBlock"] {
    gap: 0.5rem;
}
/* profile cards on All the Pups are the one card type that's actually clickable
   (via the View button inside), so give them a tactile hover lift the others
   don't need */
[class*="st-key-profile_card_"]:hover {
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.1);
    border-color: rgba(255, 255, 255, 0.9) !important;
}

/* ---------- Equal-height Upcoming cards within the same row ---------- */
/* Two cards side by side in the same grid_cols row (home.py) currently size
   independently to their own message length, which looks unbalanced even though
   neither is actually broken. Fix is pure flexbox stretch, not a fixed height:
   Streamlit's own column row is already a flex row, and align-items:stretch
   (flexbox's own default) already makes each stColumn match the row's tallest
   member -- what was missing is threading that stretched height down through the
   column's inner vertical-block wrapper to the actual visible card div, which
   otherwise just sits at its own shorter natural height inside the now-taller
   (but invisible) column, leaving dead space below it instead of visibly
   stretching. flex:1 on the card lets it grow to fill that space; height:auto
   (set on every card by the shared glass-card rule above) still governs its
   *minimum* size from content, so a very long message still grows the whole
   row's height exactly as before -- nothing here can make a card shorter than
   its own content, only taller to match a sibling.

   Scoped via :has() to only the row(s) that actually contain an Upcoming card,
   not every st.columns() in the app (top nav, "All the Pups" list, etc. don't
   need or want this). :has() needs a reasonably modern browser (Chrome/Edge/
   Safari all support it; Firefox since 2023) -- if it's not supported, this
   simply doesn't apply and cards fall back to today's independent-height
   behavior, not something visibly broken. */
[data-testid="stHorizontalBlock"]:has([class*="st-key-card_evt_"]) {
    align-items: stretch;
}
[data-testid="stHorizontalBlock"]:has([class*="st-key-card_evt_"]) > [data-testid="stColumn"] {
    display: flex;
}
[data-testid="stHorizontalBlock"]:has([class*="st-key-card_evt_"]) > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {
    width: 100%;
    display: flex;
    flex-direction: column;
}
[data-testid="stHorizontalBlock"]:has([class*="st-key-card_evt_"]) [class*="st-key-card_evt_"] {
    flex: 1;
}

/* ---------- Field groups: label-left/value-right rows (profile Identity section
   and other flat property displays). .pf-field-group itself is styled by the
   shared glass-card rule above (including its 15/17px padding); rows below only
   add vertical padding, letting the group's own horizontal padding provide the
   inset instead of double-padding each row. ---------- */
.pf-field-group-title {
    font-weight: 700;
    color: var(--pf-text-muted);
    text-transform: uppercase;
    font-size: 0.78em;
    letter-spacing: 0.05em;
    margin: 1.4rem 0 0.5rem;
}
.pf-field-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.pf-field-row:last-child {
    border-bottom: none;
}
.pf-field-label {
    color: var(--pf-text-muted);
    font-weight: 600;
    font-size: 0.9em;
    flex-shrink: 0;
}
.pf-field-value {
    color: var(--pf-text);
    text-align: right;
}

/* ---------- Dashboard/record card copy: exact type spec ---------- */
/* "New Pack Members" and "Upcoming" cards keep their full quirky sentence
   (voice.py) at full length -- what changed is the chrome around it, not the
   text. Message paragraphs (plain st.markdown, not the raw-HTML name-row) get
   the exact muted/compact treatment specified; the name-row itself is styled
   inline where it's built (ui_helpers.render_avatar_card_link/render_name_row)
   since it's raw HTML, not a plain markdown <p>. */
[class*="st-key-card_new_"] [data-testid="stVerticalBlock"],
[class*="st-key-card_evt_"] [data-testid="stVerticalBlock"] {
    gap: 0.3rem;
}
[class*="st-key-card_new_"] [data-testid="stMarkdownContainer"] p,
[class*="st-key-card_evt_"] [data-testid="stMarkdownContainer"] p {
    font-size: 13.5px;
    line-height: 1.55;
    color: #63604f;
    margin: 0;
    /* Defensive, explicit guards against truncation -- normal wrapping, never
       clipped, never forced onto one line. None of these were literally set
       anywhere in this stylesheet before either (the real bug was the
       overflow:hidden on the ancestor wrapper, fixed above), but making the
       "never truncate" intent explicit here means a future change to an
       ancestor's overflow/white-space can't silently reintroduce it. */
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-wrap: break-word;
    -webkit-line-clamp: unset;
    display: block;
    max-height: none !important;
}

/* ---------- Expanders (used as list-item rows and add/edit forms throughout) ---------- */
[data-testid="stExpander"] {
    background-color: rgba(255, 255, 255, 0.5);
    border: 1.5px solid var(--pf-border);
    border-radius: var(--pf-radius-lg);
    overflow: hidden;
    margin-bottom: 0.6rem;
}
[data-testid="stExpander"] summary {
    font-weight: 600;
    color: var(--pf-text);
}
[data-testid="stExpanderDetails"] {
    padding: 0.5rem 0.25rem;
}

/* Forms (stForm) now get the shared glass-card treatment above -- see that block's
   comment for why they were missing it before. Nothing left to style here. */

/* ---------- Dialogs (st.dialog modals) ---------- */
/* The visible modal box is an unnamed direct child of the stDialog wrapper (no stable
   testid of its own) and defaults to Streamlit's plain white, which would clash with
   the new palette. Kept a plain solid (not glass) on purpose -- a modal overlaying
   the page should stay fully legible/opaque, not translucent; this redesign's brief
   didn't ask for dialogs to become glass cards. */
[data-testid="stDialog"] > div {
    background-color: var(--pf-bg) !important;
    border-radius: var(--pf-radius-lg) !important;
}
[data-testid="stDialog"] [data-testid="stMarkdownContainer"],
[data-testid="stDialog"] h1, [data-testid="stDialog"] h2, [data-testid="stDialog"] h3 {
    color: var(--pf-text);
}

/* ---------- Tabs (profile page: Health/Personality/Social/Care) ---------- */
/* Same segmented-control treatment and active-accent color as the top nav pill,
   per "pick one consistently." The tab-scroll-arrow-hiding behavior below is
   unrelated to this redesign -- see its own comment. */
[data-testid="stTabs"] [role="tablist"] {
    gap: 0.4rem;
    border-bottom: none;
}
[data-testid="stTabs"] button[aria-label*="Scroll tabs"] {
    display: none;
}
[data-testid="stTab"] {
    border-radius: var(--pf-radius-md);
    padding: 0.4rem 0.9rem;
    color: var(--pf-text-muted);
    font-weight: 600;
}
[data-testid="stTab"][aria-selected="true"] {
    background-color: var(--pf-accent-active);
    color: #FFFBF5 !important;
}
[data-testid="stTab"][aria-selected="true"] p {
    color: #FFFBF5 !important;
}
[data-baseweb="tab-highlight"] { background-color: transparent !important; }

/* ---------- Dividers ---------- */
[data-testid="stMarkdownContainer"] hr {
    border-color: var(--pf-border);
}

/* ---------- Alerts (info/success/warning/error) ---------- */
[data-testid="stAlertContainer"] {
    border-radius: var(--pf-radius-lg);
    border: none;
}

/* ---------- Radio (filter on All the Pups) ---------- */
[data-testid="stRadio"] label {
    color: var(--pf-text);
}

@media (max-width: 640px) {
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
    [data-testid="stMainBlockContainer"] { padding-left: 0.75rem; padding-right: 0.75rem; }
    /* The 4 profile tabs fit comfortably on most phones but were a few px too wide
       on the narrowest ones (375–390px) with default padding; tighten just the tabs
       rather than shrinking type or padding everywhere. */
    [data-testid="stTabs"] [role="tablist"] { gap: 0.15rem; }
    [data-testid="stTab"] { padding: 0.4rem 0.55rem; }
    [data-testid="stTab"] p { font-size: 0.85rem; }

    /* Streamlit already stacks st.columns to one-per-row below this width on its own
       (no layout rebuild needed here) -- what's left is making sure everything that
       lands in a full-width mobile column is actually comfortable to read and tap,
       not just narrower. */

    /* Buttons: comfortably above the ~44px touch-target guideline, and full-width so
       a stacked column of buttons reads as a clean vertical list instead of a row
       of oddly-sized pills. */
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondaryFormSubmit"] {
        min-height: 2.75rem;
        width: 100%;
    }
    /* Nav pill segments, the mute-bell toggle, and icon-only buttons (profile
       header edit/delete) all stay sized to their own content rather than
       stretching full-width like ordinary text buttons do. */
    .st-key-nav_home_full button, .st-key-nav_home_icon button,
    .st-key-nav_home_full_active button, .st-key-nav_home_icon_active button,
    .st-key-nav_profiles_full button, .st-key-nav_profiles_icon button,
    .st-key-nav_profiles_full_active button, .st-key-nav_profiles_icon_active button,
    [class*="st-key-mutebell_"] button {
        width: auto;
    }
    .st-key-header_edit button, .st-key-header_delete button,
    .st-key-account_menu button {
        width: auto;
        min-width: 2.75rem;
        min-height: 2.75rem;
    }

    /* Brand mark: icon only below the breakpoint, same reasoning as the nav
       pills -- "Pawfolio" as text would otherwise compete for the same limited
       width the nav pills and hamburger also need on a phone screen. */
    .pf-brand-text {
        display: none;
    }

    /* Below the breakpoint: swap the nav pill's icon+text segment for its
       icon-only twin instead of letting "Home"/"My Pups" wrap to two lines. */
    .st-key-nav_home_full, .st-key-nav_home_full_active,
    .st-key-nav_profiles_full, .st-key-nav_profiles_full_active {
        display: none;
    }
    .st-key-nav_home_icon, .st-key-nav_home_icon_active,
    .st-key-nav_profiles_icon, .st-key-nav_profiles_icon_active {
        display: block;
    }

    /* Long unbroken values (breed descriptions, notes, emails in vet cards) were
       able to force the page wider than the viewport instead of wrapping, which is
       what actually causes horizontal scrolling on a phone -- not the layout grid
       itself, which Streamlit already reflows. */
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] {
        overflow-wrap: break-word;
        word-break: break-word;
    }

    /* Glass cards (including the login/signup form) keep the same rounded/frosted
       look on mobile, just a little tighter than the desktop 15px/17px so they
       don't eat too much of a 375px-wide screen. */
    [class*="st-key-card_"],
    [class*="st-key-profile_card_"],
    .pf-field-group,
    [data-testid="stForm"] {
        padding: 12px 14px !important;
    }
    [data-testid="stExpanderDetails"] { padding: 0.5rem 0.15rem; }

    /* Text inputs/textareas/selects/date pickers: taller so they're easy to tap
       accurately, same rounded styling as desktop. */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stDateInput"] > div > div,
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div {
        min-height: 2.75rem;
    }

}
</style>
"""


def inject_theme(st):
    st.markdown(PAWFOLIO_CSS, unsafe_allow_html=True)
