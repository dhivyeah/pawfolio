"""Central place for Pawfolio's visual theme. Injected once at app startup (app.py).

Warm & playful direction: soft pastels, cream background, rounded corners everywhere,
airy spacing. Layered on top of Streamlit's default layout via CSS only — no layout
primitives are rebuilt, existing st.columns/st.container/st.expander/st.tabs structure
is untouched.
"""

PAWFOLIO_CSS = """
<style>
:root {
    --pf-bg: #FFF8F0;
    --pf-card-bg: #FFF3E6;
    --pf-card-bg-alt: #FFEAD8;
    --pf-border: #F0D9C0;
    --pf-primary: #D97757;
    --pf-primary-hover: #C1613F;
    --pf-secondary: #8FAE8B;
    --pf-accent: #F0C05A;
    --pf-pink: #E8A0A0;
    --pf-danger: #C1613F;
    --pf-text: #4A3225;
    --pf-text-muted: #8A7160;
    --pf-radius-lg: 24px;
    --pf-radius-md: 16px;
    --pf-radius-sm: 10px;
    --pf-font-heading: "Segoe UI Rounded", "SF Pro Rounded", ui-rounded, "Trebuchet MS", Verdana, sans-serif;
}

@media (prefers-color-scheme: dark) {
    :root {
        --pf-bg: #241C16;
        --pf-card-bg: #2E2418;
        --pf-card-bg-alt: #362A1B;
        --pf-border: #4A3A28;
        --pf-primary: #E08A67;
        --pf-primary-hover: #ED9F80;
        --pf-secondary: #A8C6A0;
        --pf-accent: #F3CD7E;
        --pf-pink: #E8B3B3;
        --pf-danger: #E08A67;
        --pf-text: #F5E9DD;
        --pf-text-muted: #C9B8A8;
    }
}

html, body { overflow-x: hidden; }
section.main > div { max-width: 100%; }

/* ---------- Page background & spacing ---------- */
[data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stMain"] {
    background-color: var(--pf-bg);
}
[data-testid="stHeader"] { background-color: transparent; }
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
      Cancel sits next to a solid Save/Add and shouldn't compete with it, and the
      dashboard's "Mute email for this" is the same idea next to "View profile →".
   Danger (key prefix "delete_") stays its own red-outline tier, defined below. */
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

/* tier 3: ghost — Cancel/Mute buttons recede next to a solid Save/Add/View */
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondary"],
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondaryFormSubmit"],
[class*="st-key-mute_"] [data-testid="stBaseButton-secondary"],
[class*="st-key-mute_"] [data-testid="stBaseButton-secondaryFormSubmit"] {
    background-color: transparent;
    color: var(--pf-text-muted);
    border: 1.5px solid var(--pf-border);
    box-shadow: none;
    font-weight: 600;
}
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondary"]:hover,
[class*="st-key-cancel_"] [data-testid="stBaseButton-secondaryFormSubmit"]:hover,
[class*="st-key-mute_"] [data-testid="stBaseButton-secondary"]:hover,
[class*="st-key-mute_"] [data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background-color: var(--pf-card-bg-alt);
    color: var(--pf-text);
    border-color: var(--pf-text-muted);
    box-shadow: none;
    transform: none;
}

/* icon-only top nav buttons (defined in app.py by key) keep their own sizing;
   just make sure they inherit the rounded warm treatment too */
.st-key-nav_home button, .st-key-nav_profiles button {
    font-size: 1.7rem;
    line-height: 1;
    padding: 0.5rem 1rem;
    min-width: 3.6rem;
    min-height: 3rem;
    border-radius: var(--pf-radius-md);
    white-space: nowrap;
    background-color: var(--pf-card-bg-alt);
    color: var(--pf-text);
    box-shadow: none;
    border: 1.5px solid var(--pf-border);
}
.st-key-nav_home button p, .st-key-nav_profiles button p {
    white-space: nowrap;
    font-size: inherit;
}
.st-key-nav_home button:hover, .st-key-nav_profiles button:hover {
    background-color: var(--pf-card-bg);
    border-color: var(--pf-primary);
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
    background-color: var(--pf-card-bg-alt);
    color: var(--pf-text);
    box-shadow: none;
    border: 1.5px solid var(--pf-border);
}
.st-key-header_edit button:hover {
    background-color: var(--pf-card-bg);
    border-color: var(--pf-primary);
    transform: none;
}
.st-key-header_delete button:hover {
    background-color: var(--pf-card-bg);
    border-color: var(--pf-danger);
    color: var(--pf-danger);
    transform: none;
}
[data-testid="stPopoverBody"] { background-color: var(--pf-bg); }

/* ---------- Inputs ---------- */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: #FFFDFA;
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
    background-color: #FFFDFA !important;
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

/* ---------- Cards: st.container(border=True) with key prefixed "card_" or "profile_card_" ---------- */
[class*="st-key-card_"],
[class*="st-key-profile_card_"] {
    background-color: var(--pf-card-bg) !important;
    border: 1.5px solid var(--pf-border) !important;
    border-radius: var(--pf-radius-lg) !important;
    padding: 0.25rem;
    box-shadow: 0 2px 10px rgba(74, 50, 37, 0.06);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
[class*="st-key-card_"] [data-testid="stVerticalBlock"],
[class*="st-key-profile_card_"] [data-testid="stVerticalBlock"] {
    gap: 0.5rem;
}
/* profile cards on All the Pups are the one card type that's actually clickable
   (via the View button inside), so give them a tactile hover lift the others
   don't need */
[class*="st-key-profile_card_"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 18px rgba(74, 50, 37, 0.12);
    border-color: var(--pf-primary) !important;
}

/* Dashboard reminder cards carry an urgency tier in their key (see home.py) so an
   overdue vaccination doesn't read at the same visual volume as a routine one 30
   days out, or a "new pack member" welcome card. Left accent bar only — the fill
   stays the same warm card color so the feed doesn't turn into a traffic light. */
[class*="st-key-card_evt_overdue_"] {
    border-left: 4px solid var(--pf-danger) !important;
}
[class*="st-key-card_evt_soon_"] {
    border-left: 4px solid var(--pf-accent) !important;
}
[class*="st-key-card_evt_upcoming_"] {
    border-left: 4px solid var(--pf-secondary) !important;
}

/* ---------- Expanders (used as list-item rows and add/edit forms throughout) ---------- */
[data-testid="stExpander"] {
    background-color: var(--pf-card-bg);
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

/* ---------- Forms ---------- */
[data-testid="stForm"] {
    background-color: var(--pf-card-bg-alt);
    border: 1.5px solid var(--pf-border);
    border-radius: var(--pf-radius-lg);
    padding: 1.25rem 1.25rem 0.5rem;
}

/* ---------- Dialogs (st.dialog modals) ---------- */
/* The visible modal box is an unnamed direct child of the stDialog wrapper (no stable
   testid of its own) and defaults to Streamlit's plain white, which clashes with the
   warm theme everywhere else. */
[data-testid="stDialog"] > div {
    background-color: var(--pf-bg) !important;
    border-radius: var(--pf-radius-lg) !important;
}
[data-testid="stDialog"] [data-testid="stMarkdownContainer"],
[data-testid="stDialog"] h1, [data-testid="stDialog"] h2, [data-testid="stDialog"] h3 {
    color: var(--pf-text);
}

/* ---------- Tabs ---------- */
/* The tab strip's role="tablist" wrapper is what actually scrolls (current
   Streamlit no longer exposes data-baseweb="tab-list" here). When the 5 tabs
   don't fit, BaseWeb overlays absolutely-positioned "Scroll tabs left/right"
   arrow buttons at the container's edges, on top of whichever tab pill ends
   up underneath at the current scroll position (not just the scroll
   extremes) -- clicks meant for that tab land on the invisible arrow
   instead and silently do nothing. The tab-list is already horizontally
   scrollable via swipe/drag without the arrows, so drop them rather than
   try to out-position a fixed overlay. */
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
    background-color: var(--pf-primary);
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
       a stacked column of buttons (e.g. View profile / Mute email) reads as a clean
       vertical list instead of a row of oddly-sized pills. */
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondaryFormSubmit"] {
        min-height: 2.75rem;
        width: 100%;
    }
    /* Icon-only buttons (top nav, profile header edit/delete) stay compact and
       square rather than stretching full-width like text buttons do. */
    .st-key-nav_home button, .st-key-nav_profiles button,
    .st-key-header_edit button, .st-key-header_delete button {
        width: auto;
        min-width: 2.75rem;
        min-height: 2.75rem;
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

    /* Cards/expanders had comfortable desktop padding that ate a lot of a 375px-wide
       screen; keep the same rounded warm look, just tighter. */
    [class*="st-key-card_"],
    [class*="st-key-profile_card_"] {
        padding: 0.15rem;
    }
    [data-testid="stExpanderDetails"] { padding: 0.5rem 0.15rem; }
    [data-testid="stForm"] { padding: 1rem 0.85rem 0.4rem; }

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
