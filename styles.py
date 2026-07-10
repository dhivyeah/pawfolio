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
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondaryFormSubmit"] {
    background-color: var(--pf-primary);
    color: #FFFBF5;
    border: none;
    border-radius: var(--pf-radius-md);
    font-weight: 600;
    padding: 0.5rem 1.1rem;
    min-height: 2.75rem;
    box-shadow: 0 2px 6px rgba(74, 50, 37, 0.12);
    transition: background-color 0.15s ease, transform 0.1s ease;
}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background-color: var(--pf-primary-hover);
    color: #FFFBF5;
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

/* delete/danger buttons opt in via key="...delete..." */
[class*="st-key-delete_"] [data-testid="stBaseButton-secondary"] {
    background-color: transparent;
    color: var(--pf-danger);
    border: 1.5px solid var(--pf-danger);
    box-shadow: none;
}
[class*="st-key-delete_"] [data-testid="stBaseButton-secondary"]:hover {
    background-color: var(--pf-danger);
    color: #FFFBF5;
}

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
}
[class*="st-key-card_"] [data-testid="stVerticalBlock"],
[class*="st-key-profile_card_"] [data-testid="stVerticalBlock"] {
    gap: 0.5rem;
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

/* ---------- Tabs ---------- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.4rem;
    border-bottom: none;
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
    [data-testid="stMainBlockContainer"] { padding-left: 0.75rem; padding-right: 0.75rem; }
}
</style>
"""


def inject_theme(st):
    st.markdown(PAWFOLIO_CSS, unsafe_allow_html=True)
