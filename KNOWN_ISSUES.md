# Known Issues — for future review

Found during a schema/UI review on 2026-07-10. Bugs 1–3 (crash-level) were fixed immediately
— see git history / conversation for details. Everything below is a documented edge case, UX
gap, or structural risk. Numbering matches the original review so it can be cross-referenced.

## Priority

Fixed items aren't listed here — they're done. This covers every item still open, classified by
how urgent fixing it actually is, not by how it happened to get discovered.

### 🔴 Urgent / severe
*(none currently open)*. Every open item below is a recoverable data-integrity edge case, a
missing nice-to-have, or a structural/perf concern that's dormant at this app's current scale —
none of them block usage or lose data silently and permanently. The genuinely severe bugs found
along the way (the original crash-level 1–3, and bug 30 below) were fixed on discovery rather
than left open; nothing in that class is currently sitting unfixed.

### 🟡 Can wait
Real gaps worth fixing in the next pass — mostly silent-bad-data or missing-safety-net issues.
None of them block using the app today, but each one can produce a confusing or wrong result
that the user has no way to notice from within the app itself.
- **5** — no validation that end dates come after start dates anywhere
- **8** — overdue items never expire/dismiss, and the boarding check-in cutoff is inconsistent
  with every other event type
- **12** — HEIC photos (the iPhone camera default) are rejected outright
- **13** — editing an existing record doesn't re-validate required fields (can save an
  emptied-out name)
- **16** — no UI to fix a typo in a vet's own details, or delete one, ever
- **25** — no confirmation when a reminder is set more than 30 days out
- **32** — delete-profile warning now gives a *count* of affected other profiles but not
  *which* ones (partially fixed 2026-07-15 — see entry below)
- **35** — email digest send failures retry on every single app load with no backoff, and the
  default sender can only reach one email address until a domain is verified

### 🟢 Low priority
Papercuts, missing polish, and structural/perf risk that's dormant at the app's current scale
(a handful of profiles, one user). Worth fixing opportunistically, not worth a dedicated pass.
- **6** — "Add vet visit" has no required-field check
- **9** — no boarding pickup/checkout reminder or "currently boarding" indicator
- **10** — "New Pack Members" section has no dismiss, repeats for a full week
- **11** — deleted/replaced photo files pile up on disk forever
- **18** — two records with the same name/date look identical in their list rows
- **20** — theme leans on undocumented Streamlit internals (bigger surface area now than when
  first flagged — see re-audit note)
- **22** — no indexes on foreign key columns
- **23** — photos re-encoded from disk on every rerun (more reruns now than when first flagged,
  given how dialog-heavy the UI became — see re-audit note)
- **24** — text contrast never run through a formal WCAG checker
- **26** — no vaccine-name guidance or autocomplete
- **29** — generic "Select a date." accessibility label on every date field, regardless of which
  field it is
- **36** — email notification horizon (7 days) is hardcoded, no in-app control over it
- **37** — "today" and the once-a-day send cap are based on the server's clock, not
  timezone-aware
- **38** — `notified_events` rows are never cleaned up when the record or profile they refer to
  is deleted
- **39** — sending a digest blocks that page load until the Resend API call returns (once a day,
  at most)
- **40** — theoretical duplicate-digest race if two sessions open at nearly the same instant
- **41** — digest layout/readability untested with many due items in one email
- **42** — no in-app visibility into notification send history (a per-item mute control was
  added 2026-07-15 — see entry below)

### ⚪ No longer applicable
- **7** — moot. Described a gap in Add Profile's "first vet visit" block; that whole block was
  removed when Add Profile got trimmed to identity-only fields in the 2026-07-14 redesign, so
  there's nothing left to fix.

### 🔵 Needs a decision, not a fix
- **33** — friends are one-directional, siblings are symmetric. Not broken — just an
  inconsistency nobody deliberately chose, worth a call either way.

## Edge cases (real data scenarios that produce bad or surprising results)

4. ~~**"Add" forms default both halves of a date pair to today.**~~ **FIXED 2026-07-10.**
   Confirmed live during a first-time-user walkthrough (see points 25–29 below): opening
   "➕ Add vaccination" on Profile Detail and clicking submit without touching the due-date
   field created a vaccine record due "today," which immediately fired as a "🚨 today" alert
   on the dashboard. Fixed by defaulting the due/next/end/check-out half of every date pair to
   blank (`value=None`) in `views/profile_detail.py`'s "Add vaccination," "Add medication,"
   "Add bath record," "Add food refill record," and "Add boarding stay" forms — matching the
   pattern `views/add_profile.py` already used correctly. The "given/start/check-in" half still
   defaults to today, which is a reasonable default for "I'm logging this now."
   No validation was added preventing an end date before a start date — see point 5, still open.

5. **[🟡 Can wait]** **No validation that end dates come after start dates anywhere** —
   medication `end_date` before `start_date`, boarding `check_out` before `check_in`,
   vaccination `next_due_date` before `date_given`, spay/neuter date entered while status is
   "no" — all silently accepted.

6. **[🟢 Low priority]** **"Add vet visit" has no required-field check**, unlike every other
   "Add" form (which all require at least a name). A completely blank vet visit can be
   submitted, creating an empty history row with just today's date.
   (`views/profile_detail.py`, "Add vet visit" form.)

7. **[⚪ No longer applicable]** ~~**Add Profile's "first vet visit" drops notes-only
   entries.**~~ **MOOT 2026-07-15.** Originally: the gate was `if visit_date or visit_reason:`,
   which didn't check `visit_notes`, so a user who only typed notes (no date, no reason)
   silently lost that text on submit. Moot now — Add Profile's entire "first vet visit" section
   (along with vaccination/registration/medication/spay-neuter/surgery/vet-directory/bath/food/
   boarding/personality/friend) was removed in the 2026-07-14 redesign; the form is identity
   fields only now, everything else is added from the profile page afterward.

8. **[🟡 Can wait]** **Overdue items have no ceiling and no dismiss mechanism.**
   Vaccination/medication/bath/food_refill events with no lower bound on `days_until` stay on
   the dashboard forever once overdue — there's no way to acknowledge/snooze from the feed
   itself, only by editing the record on the profile page. Meanwhile `boarding_checkin` is the
   only event type that requires `days_until >= 0`, so a past check-in just silently vanishes
   from the feed — inconsistent treatment across event types that was never a deliberate,
   reviewed decision. (`db.py: get_upcoming_events`)

9. **[🟢 Low priority]** **No "checked out" / pickup reminder.** The dashboard surfaces
   upcoming boarding *check-ins* but never a "picking up Bobby today" reminder for
   `check_out_date`, and there's no "currently boarding" status indicator anywhere in the UI.

10. **[🟢 Low priority]** **"New Pack Members" has no expiry tracking beyond the raw 7-day
    window and no dismiss.** A profile stays in that section every time Home loads for a full
    week — fine once, could feel repetitive with daily use.

11. **[🟢 Low priority]** **Photo files are never cleaned up.** Deleting a profile
    (`db.delete_profile`) or replacing a photo via Edit Identity both leave the old file behind
    in `photos/` forever.

12. **[🟡 Can wait]** **iPhone default photo format isn't accepted.** The uploader only allows
    `png/jpg/jpeg/webp`; HEIC (default format for iOS camera photos) is rejected unless
    converted first — a plausible papercut given the persona.

13. **[🟡 Can wait]** **Editing an existing record doesn't re-validate required fields.** Only
    the "Add new" forms check for a non-empty name; the "Save" button on an existing
    vaccination/medication/surgery/etc. edit form will happily save an emptied-out name field.

## UX / consistency issues

14. ~~**No confirmation on any sub-record delete.**~~ **FIXED 2026-07-14.** Every delete
    action on the profile page (every sub-record type, plus the profile itself) now opens a
    confirm dialog (`st.dialog`) before anything is removed. Profile delete also moved off a
    checkbox-gated button into its own "Delete Profile" tab. Landed alongside a broader rework
    of the profile page: every "Add" ribbon is now a button that opens a modal instead of an
    always-present expander, every "Edit" ribbon is a compact row + Edit button that opens a
    modal, and every save/add/delete gives a toast confirmation. The expander-per-record layout
    was replaced because Streamlit's expander open/closed state turned out to be "sticky" on
    the frontend — session_state writes from Python can't force one shut once a user has
    touched it — so "Cancel" could never reliably collapse it; `st.dialog` always closes
    cleanly on rerun instead. Two non-obvious `st.dialog` constraints shaped the
    implementation: dialogs can't nest (a Delete click inside an Edit dialog queues the
    confirm dialog via session_state + rerun rather than opening it directly), and
    `st.toast()` called immediately before `st.rerun()` never reaches the browser — the rerun
    cuts the run off before the message flushes — so toasts are queued the same way and fired
    on the next run instead (`ui_helpers.queue_toast` / `render_queued_toast`).

15. ~~**"Unlink vet" button is styled as a red/terracotta danger button"**~~ **FIXED
    2026-07-14.** Renamed its key from the `delete_` prefix to `unlink_` so it no longer picks
    up the danger-button CSS rule — it still intentionally skips the confirm dialog too, since
    unlinking is low-stakes and fully reversible (the vet stays in the shared directory).

16. **[🟡 Can wait]** **No way to edit or delete a vet's own details once created.**
    `db.update_vet` / `db.delete_vet` exist but have no UI surface. A typo in a vet's
    phone/clinic can never be fixed; unlinking a vet from every profile leaves it in the
    directory forever with no cleanup path.

17. ~~**Health tab is now quite long.**~~ **FIXED 2026-07-14.** Vaccinations, Registration,
    Medications, Spay/Neuter, Surgeries, Vet Visit History, and Vets are each wrapped in their
    own `st.expander` (collapsed by default, with a live record count in the label) instead of
    all stacking fully open — landing on Health now shows a compact table of contents instead
    of a long scroll. Each section expander needed an explicit `key=` (`exp_health_vacc` etc.):
    without one, Streamlit treats the widget as a new instance whenever its label text changes
    (the record count), which reset it to collapsed right after every add/edit — the opposite
    of what an accordion should do.

18. **[🟢 Low priority]** **Duplicate list-item labels are visually indistinguishable.** E.g.
    two boarding stays with unset dates both render as `🧳 facility — ? to ?`; two vaccinations
    with the same name/due date look identical in the collapsed expander list.

19. ~~**Untested tab-row overflow on narrow phones.**~~ **FIXED 2026-07-14.** Confirmed live
    (via Playwright at 390px width): when the 5-item tab row overflows, BaseWeb's
    auto-generated "Scroll tabs left/right" arrow buttons render absolutely-positioned on top
    of whichever tab pill sits at the container edge — clicks meant for that tab (commonly
    Social, expanding a friend record pushed it right to the edge) landed on the invisible
    arrow instead and did nothing, reading as "the tabs stopped working." Fixed in `styles.py`
    by hiding the arrow buttons (`display: none`) and relying on the tab-list's existing native
    horizontal scroll (swipe/drag) to reach off-screen tabs instead. Also fixed a dead selector
    in the same rule block — current Streamlit no longer exposes `data-baseweb="tab-list"`;
    the working selector is `[role="tablist"]`.

## Structural / maintenance risks (not bugs today, but fragile)

20. **[🟢 Low priority]** **The entire theme depends on undocumented Streamlit internals**
    (`data-testid`, `data-baseweb` attributes, structural child selectors like `> div > div`
    for date/select inputs). This already caused one real bug this session (a `help=` tooltip
    wrapper silently broke mobile button visibility). A future Streamlit version bump could
    silently revert buttons/cards/inputs to unstyled defaults with no error, just a visual
    regression. The 2026-07-14/15 redesign added a lot more of this surface area (dialogs,
    popovers, per-tier button styling, tab internals) — the risk is larger than when first
    flagged, even though nothing is broken today.

21. ~~**N+1 query pattern in the dashboard.**~~ **FIXED 2026-07-18.** Was: `get_upcoming_events`
    opened a fresh SQLite connection per profile per event type (7 sub-queries per profile).
    Migrating to hosted Postgres made this expensive rather than free (each one became a real
    network round-trip), so it was rewritten during the deployment pass to fetch each record
    type once across all profiles and group in Python instead — see the Deployment Review
    section below and the commit history for detail. `views/home.py` still calls `get_profile()`
    once per event rather than caching per profile — a smaller, still-open instance of the same
    shape of issue, low-impact at current data volume.

22. **[🟢 Low priority]** **No index on any foreign key column** (`profile_id` everywhere,
    `vet_id` in `profile_vets` — aside from the unique index added for the vet-dedup fix, and
    the implicit unique index on `siblings(profile_id_a, profile_id_b)`). Every list query is a
    full table scan. Non-issue at small scale.

23. **[🟢 Low priority]** **Full photo files are base64-encoded from disk on every single
    Streamlit rerun** (`ui_helpers._image_data_uri`, no caching via `st.cache_data`). Any
    widget interaction anywhere on a page re-encodes every visible photo from scratch. Combined
    with Streamlit's 200MB default upload cap and no client-side resizing/compression on
    upload, a handful of large photos could make the app feel sluggish. The dialog-per-action
    UI added 2026-07-14 means noticeably more reruns per user action than before, so this is
    somewhat more likely to be felt now than when first flagged.

24. **[🟢 Low priority]** **Contrast wasn't formally verified.** `--pf-text-muted` (`#8A7160`
    light / `#C9B8A8` dark) against the card backgrounds is a visual judgment call, not
    something run through an actual WCAG contrast checker.

## First-time-user walkthrough findings (2026-07-10)

Found by actually driving the running app end-to-end as a first-time user adding a dog and
setting up a vaccination schedule (via Playwright), not just reading code. Point 4 above (the
default-due-date trap) was confirmed live this way and is now fixed; the rest are still open.

25. **[🟡 Can wait]** **No feedback when a scheduled reminder is more than 30 days out.** Set a
    vaccination due date 36 days out, submitted, went back to Home expecting some confirmation
    — nothing. `get_upcoming_events`'s dashboard-only 30-day horizon means there's no
    persistent "your reminders are set" indicator anywhere; success reads identically to "did
    this even save?" A first-time user has no way to confirm the data stuck short of digging
    back into the profile's Health tab.

26. **[🟢 Low priority]** **No guidance on what to type into "Vaccine name."** Blank text
    field, no examples, no autocomplete for common vaccines (Rabies, DHPP, Bordetella, etc.). A
    first-time dog owner may not know standard vaccine names to enter.

27. ~~**"Chennai Corporation Registration" appears with zero explanation.**~~ **FIXED
    2026-07-14.** Added a one-line caption inside its (now collapsed-by-default) expander:
    "Only relevant if this dog is registered with the Chennai Corporation's pet program — safe
    to leave blank otherwise."

28. ~~**🪪 (ID card) emoji rendered as a broken/tofu box.**~~ **FIXED 2026-07-14.** The
    Identity *tab* it lived on is gone — name/photo/dob/breed/type now edit from a small ✏️
    button in the profile header instead of their own tab (that tab's only other content was
    one caption line, since everything else already showed in the header above it). Add
    Profile's own "🪪 Identity" section header is gone too, for the same reason: the form was
    trimmed to identity fields only, so a section label restating "Identity" added nothing.

29. **[🟢 Low priority]** **Date input fields have a generic accessibility label.** Every
    `st.date_input`'s underlying `<input>` has `aria-label="Select a date."` regardless of
    which field it is (confirmed via DOM inspection) — a screen reader user tabbing through the
    Add Profile form would hear "Select a date" repeatedly with no indication of which date is
    which, relying entirely on correct label/input association rather than the accessible name
    itself.

## Known-issues re-audit (2026-07-15)

Went back through every item above against the current code, plus looked specifically for
anything the nickname/other-notes/friend-linking/sibling-linking/vet-reuse work (2026-07-14/15)
might have broken or introduced. One of the three new bugs found here (30) turned out to be a
real, reproducible cause of a support report earlier in that session — a "Home and All the Pups
buttons stopped responding" complaint that got diagnosed at the time as a dropped connection
from a dev-server restart. That diagnosis wasn't wrong (server restarts *do* drop old tabs'
connections), but it wasn't the whole story: bug 30 produces the identical symptom through a
completely different, code-level path, and was still live in the app until this audit found it.

30. ~~**Dismissing the delete-confirmation dialog via the native ✕ (or Escape / click-outside)
    left the app stuck.**~~ **FIXED 2026-07-15 (was 🔴 urgent — blocked all navigation until
    dealt with).** `request_delete()` stashes the pending confirmation in
    `st.session_state["_pending_delete"]`, and `render_pending_delete_dialog()` (called
    unconditionally at the top of every profile page) reopens the confirm dialog as long as
    that key is set — cleared only by the dialog's own "Yes, delete" or "Cancel" button.
    `st.dialog` is dismissible by default (✕ button, Escape, clicking the backdrop)
    independently of those two buttons, and dismissing it that way never ran either handler.
    The stale confirmation would then resurface on the *next* profile page visited — any
    profile, not just the one it was about — showing a "Delete X?" dialog for an unrelated
    record and blocking that page's own buttons behind its modal backdrop (reproduced:
    dismiss a delete-friend confirmation via ✕ on one dog's page, then Home/All the Pups
    become unclickable everywhere until that leftover dialog is dealt with). Fixed by passing
    `on_dismiss=` to `@st.dialog("Confirm delete", ...)` so the pending-delete flag clears on
    *any* dismissal path, not just the two buttons inside it.

31. ~~**"Add sibling" showed a misleading empty-state message.**~~ **FIXED 2026-07-15 (was 🟢
    low priority — wrong copy, not wrong behavior).** With zero candidates it always said
    "Every other pup in Pawfolio is already linked as a sibling" — true when every other
    profile really is already linked, but also shown (and wrong) for a brand-new install with
    only one profile total, where the real reason is "there's no second pup yet." Now
    distinguishes the two cases.

32. **[🟡 Can wait]** **Deleting a profile silently drops other profiles' links to it, with no
    warning of that specific consequence.** `friends.friend_profile_id` and both `siblings`
    columns are `ON DELETE CASCADE` — confirmed working correctly (tested directly: deleting a
    profile that another profile had linked as a friend, including a personal note on that
    friendship, removes that friend-row entirely rather than orphaning it) — but the delete
    confirmation only ever described records *on this profile*, never "this will also edit N
    other profiles." **Partially addressed 2026-07-15**: the confirmation now says how many
    other profiles reference this one as a friend or sibling before you confirm
    (`db.count_incoming_links`). Still open: it doesn't name *which* profiles, and there's no
    equivalent warning anywhere else these links are touched.

33. **[🔵 Needs a decision, not a fix]** **Friends are one-directional; siblings are
    symmetric — same-looking "pick an existing pup" feature, different relationship model.**
    Add Bobby as Mili's sibling and Bobby's own Social tab shows Mili back automatically (by
    design — confirmed working). Add Bobby as Mili's *friend* and Bobby's Social tab shows
    nothing; Mili's note about the friendship is only ever visible from Mili's side. Not
    necessarily wrong — a friendship someone privately notes down being one-sided is arguably
    realistic — but it wasn't a deliberate, discussed design choice, just a byproduct of
    siblings being built as a true many-to-many link table while friends kept their original
    one-owner shape. Worth a decision either way rather than leaving it as an accident.

## Email notifications review (2026-07-15)

New feature: a warm-voiced email digest, sent via Resend, checked once per browser session on
app load (`notifications.check_and_notify`, wired in from `app.py`), reusing
`db.get_upcoming_events` and `voice.render_event_card` as-is rather than reimplementing either.
Tested directly (not just read): first-run with no prior notification state, nothing-due
no-op, per-item dedup, the once-a-day send cap holding independently of dedup, a changed due
date correctly un-suppressing an item, and a real send through Resend confirmed landing in the
inbox. Findings below are from deliberately trying to break it, not just reading the code.

One genuine near-miss during setup, not a code bug: real Resend credentials briefly ended up in
`.env.example` (the tracked template file) instead of `.env` (the gitignored real one), because
the file that got hand-edited had the wrong name. Caught before anything was staged or
committed — confirmed via `git status`/`git diff --cached` that `.env.example` had never been
added to git at any point, so nothing was ever at risk of reaching GitHub. Fixed by moving the
real values into a correctly-named `.env` (confirmed gitignored via `git check-ignore -v`) and
restoring `.env.example` to placeholders. No code or design lesson here beyond: a `.env.example`
file is only as safe as everyone actually treating it as read-only.

34. ~~**A due item is emailed at most once, ever, unless its due date changes.**~~ **RESOLVED
    2026-07-15 — decision made and built, not just documented.** Was flagged as an open question
    ("notify once and go silent forever" vs. "keep nagging until resolved"). Redesigned into a
    third option, deliberately: notify at each of four countdown checkpoints as a due item
    crosses 7/3/1/0 days out, then stop — never notifying once something goes overdue, since the
    app has no way to know whether an overdue item was actually handled outside Pawfolio or just
    not yet updated here. `notifications.MILESTONES`, dedup now keyed on
    `(event_type, record_id, state_key, milestone)` instead of just `(event_type, record_id,
    state_key)`. A "Mute email for this" action was also added on dashboard cards (see item 42
    below) so a user can silence the remaining checkpoints for one item early if they've already
    handled it.

35. **[🟡 Can wait]** **Two related Resend operational limits, neither one fatal, both worth
    knowing about before relying on this daily.** (a) A failed send doesn't mark anything as
    notified, so the *same* digest retries on the *next* app load — correct for "don't lose a
    notification because Resend hiccuped once," but there's no backoff, so if Resend is down or
    misconfigured for an extended stretch, every single app load that day re-attempts the same
    API call. At normal personal-app usage (a handful of loads a day) this is a non-issue; it'd
    only matter under either heavy reloading or a prolonged outage. (b) The default
    `RESEND_FROM_EMAIL` (`onboarding@resend.dev`) is Resend's shared sandbox sender, which by
    Resend's own rules can only deliver to the email address on the Resend account itself —
    fine for the initial setup and confirmed working end-to-end here, but it'll silently start
    failing (retrying per (a), logged to the console, no in-app indication) if `NOTIFY_EMAIL` is
    ever pointed at a different address without first verifying a real sending domain in Resend.

36. **[🟢 Low priority]** **The 7-day notification horizon is a hardcoded constant**
    (`notifications.NOTIFY_HORIZON_DAYS`), deliberately tighter than the dashboard's 30-day
    display window so the digest doesn't fire for anything a month out — but there's no way to
    change it short of editing the constant.

37. **[🟢 Low priority]** **"Today" and the once-a-day send cap are computed from the server's
    local clock** (`date.today()`, `datetime.now()`), not any explicit timezone. A non-issue
    running locally on the same machine as the browser; would need attention if this were ever
    deployed somewhere whose server clock doesn't match the user's own timezone — the daily cap
    could reset at an unexpected hour relative to the user's actual day.

38. **[🟢 Low priority]** **`notified_events` rows are never cleaned up.** If a vaccination (or
    any other due-tracked record) is deleted, or an entire profile is deleted, its dedup rows
    stay in `notified_events` forever as harmless clutter — same shape of issue as the
    already-documented photo-file cleanup gap (11).

39. **[🟢 Low priority]** **Sending a digest blocks that particular page load until the Resend
    API call returns or times out** (10s timeout). Only happens at most once a day, and only on
    whichever load happens to be the one that triggers it — every other load that day is a pure
    local DB check with no network call, effectively instant.

40. **[🟢 Low priority]** **Theoretical duplicate-send race.** The once-a-day cap is a plain
    `SELECT` + later `INSERT`, not an atomic check-and-set. If two browser sessions happened to
    both load the app for the first time that day within the same narrow window, both could read
    "not sent yet" before either finishes sending, producing two digest emails instead of one.
    Vanishingly unlikely for a single-user local app opened from one browser at a time; would
    matter more under real concurrent access.

41. **[🟢 Low priority]** **Digest appearance was only verified with a single due item.** The
    HTML/text layout (colored left-border cards, one per event) looked clean and on-brand in
    that test — genuinely worth a look at how it reads with, say, 8-10 items at once before
    trusting it at higher volume, since that's a very plausible real digest on a day with several
    things due across multiple dogs.

42. **[🟢 Low priority]** **No in-app visibility into the notification system** — no way to see
    when the last digest went out or what it said, short of querying the database directly.
    **Partially addressed 2026-07-15**: a "Mute email for this" button on each dashboard card
    now gives per-item pause control without touching `.env` or the database — added alongside
    the item 34 redesign above. Still open: no send history/log visible anywhere in the UI.

## E2E QA Test Pass — 2026-07-15

Full end-to-end pass across Add/Edit/Delete Profile, Dashboard, Vet entity, Boarding history,
Notifications, and edge cases (empty DB, long text, special characters, duplicate names, date
extremes). Logged here in the format requested for this pass rather than the numbered-prose
style above. Two new issues found; everything else tested clean. See conversation/test scripts
for full pass/fail detail per area — only actual defects are logged below, not passing checks.

### Issue: Due dates more than ~10 years in the future silently fail to save

- **Severity:** Medium
- **Steps to reproduce:**
  1. Open any dialog with a due-date field — e.g. a profile's Health tab → Vaccinations →
     Add vaccination.
  2. Type a due date more than ~10 years from today into "Next due date" (e.g. today is
     2026-07-15; type `2037/06/15`).
  3. Submit the form.
- **Expected vs. actual:** Expected the date to either save as typed, or the app to visibly
  reject/clamp the out-of-range date and explain why. Actual: the record saves, a "Vaccination
  added." success toast appears, but the due date is silently dropped and displays as "next due
  unset" — no error, no warning, nothing to tell the user the date didn't take. Confirmed the
  threshold sits between 10 and 11 years out (9y and 10y out both saved correctly in testing;
  11y out silently failed every time).
- **Location:** `views/profile_detail.py` — every `st.date_input(..., value=None)` call that
  has no explicit `max_value` set: vaccination `next_due_date`, medication `end_date`,
  registration `reg_next_due`/`reg_last_renewed`, bath `next_due_date`, food refill
  `next_refill_date`, boarding `check_in_date`/`check_out_date`. Root cause is almost certainly
  Streamlit's own default navigable range for an unbounded `date_input` (~today ± 10 years) —
  the fix is adding an explicit `max_value` (and `min_value`, for symmetry) to each of these
  calls, the same way the DOB field already does.

### Issue: Hard browser refresh on a Profile Detail page silently switches to a different, arbitrary profile

- **Severity:** Medium
- **Steps to reproduce:**
  1. Open any dog's profile page.
  2. Refresh the browser tab (F5 / hard reload — not just clicking around inside the app).
- **Expected vs. actual:** Expected to either stay on the same dog's profile, or get some
  indication the view changed. Actual: `st.session_state["selected_profile_id"]` doesn't survive
  a hard reload (Streamlit starts a fresh session on a new WebSocket connection, which is
  expected Streamlit behavior), so the page falls back to a bare "Pick a profile" selectbox
  defaulting to whichever profile sorts first alphabetically — silently showing a *different dog*
  with no banner or message explaining why the view changed. Data itself is never lost (verified
  separately that edits persist correctly in the database across both a refresh and a full app
  restart) — this is purely a navigation/orientation gap. Worth fixing since a user who refreshes
  mid-edit could reasonably think their change didn't save, when really they're just looking at
  a different dog.
- **Location:** `views/profile_detail.py`, the `if not profile_id:` fallback block (roughly
  lines 21–31) that back-fills a missing `selected_profile_id` from session state.

## Deployment Review — 2026-07-18

Migrated storage from local SQLite to hosted Supabase Postgres, deployed to Streamlit
Community Cloud, and did a mobile-responsive CSS pass. Findings below are what's still open
after that work; two significant performance issues found along the way (connection-per-query
overhead, and an N+1 query pattern in `get_upcoming_events`) were fixed during the same pass
rather than left open — see the commit history, not this list, for those.

### Issue: Supabase free-tier database auto-pauses after 7 days of inactivity

- **Severity:** High
- **Steps to reproduce:** Don't open Pawfolio (or otherwise query the Supabase project) for
  7+ consecutive days.
- **Expected vs. actual:** Expected the app to keep working whenever visited. Actual: Supabase
  free-tier projects automatically pause after a week with no API activity. The next visit
  after that will fail to connect (or hang while Supabase wakes the project back up, which
  isn't instant) until the project is manually resumed from the Supabase dashboard. For a
  personal app that might not be opened daily, this is a real, likely-to-actually-happen
  scenario, not a theoretical edge case. (What a visitor actually *sees* when this happens was
  a separate, worse problem — raw tracebacks leaking infrastructure details — found in the
  2026-07-19 pass below and fixed there; this entry is about the pause itself, which is still
  a real, unaddressed risk.)
- **Location:** Infrastructure/hosting configuration, not application code — worth knowing
  about rather than something to fix in `db.py`. Supabase's dashboard has a setting to disable
  auto-pause on paid tiers; on free tier the only mitigation is some kind of periodic keep-alive
  ping, which has its own tradeoffs.

### Issue: Streamlit Community Cloud cold-start can take 45–90+ seconds and produce inconsistent intermediate rendering

- **Severity:** Medium
- **Steps to reproduce:** Visit the deployed app after it's been idle long enough for
  Streamlit Cloud to have spun its container down (free tier does this after a period of no
  traffic), or hit it with several rapid fresh sessions in a short window.
- **Expected vs. actual:** Expected a loading indicator followed by working content within a
  few seconds. Actual: verified the deployed app does eventually render correctly every time
  (confirmed via three separate full-page screenshots, each showing accurate live data with
  zero errors) — but getting there took anywhere from ~10s to 60s+ across different attempts,
  and during that window the page can be in visually-complete-but-not-yet-interactive states.
  This is Streamlit Community Cloud's own infrastructure cold start (separate from, and in
  addition to, the in-app database cold-start latency that was already fixed this pass) — free
  tier apps spin down when idle and take real time to spin back up. Not a bug in Pawfolio's
  code, but a real characteristic of where it's hosted, worth knowing about rather than being
  surprised by.
- **Location:** N/A (Streamlit Community Cloud infrastructure, not application code).
- **Update:** confirmed as more than theoretical — a real cold session showed the injected
  `<style>` block as literal visible page text instead of an applied stylesheet (raw CSS
  source, unstyled, on-screen). Root cause: `inject_theme()` ran *after* `init_db()` and
  `check_and_notify()` in `app.py`, both of which can take several real seconds against
  Postgres on a cold session — Streamlit streams each element to the browser as its `st.*`
  call executes, so the stylesheet simply hadn't arrived yet while those ran. Fixed by moving
  `inject_theme(st)` to immediately after `st.set_page_config()`, before any of the slow
  calls, so styling arrives first regardless of how long the rest of the page takes. Did not
  reproduce on a second load (confirmed transient, resolved by a manual refresh at the time),
  consistent with a narrow cold-start timing window rather than a persistent per-visit bug.

### Issue: `.env` and Streamlit Cloud secrets are two separate, manually-synced copies of the same values

- **Severity:** Low
- **Steps to reproduce:** Rotate any credential (Resend API key, Supabase database password)
  in one place.
- **Expected vs. actual:** Expected one source of truth. Actual: the local `.env` file and
  Streamlit Cloud's secrets manager each hold an independent copy of `RESEND_API_KEY`,
  `NOTIFY_EMAIL`, `RESEND_FROM_EMAIL`, and `DATABASE_URL`. Updating one doesn't touch the
  other, so a rotated credential can silently work locally while the deployed app keeps using
  the old one (or vice versa) until both are updated by hand.
- **Location:** N/A (operational/process gap, not application code).

### Issue: Connection pool sized for personal-app scale, not tested under real concurrent load

- **Severity:** Low
- **Details:** `db.py`'s connection pool is a `ThreadedConnectionPool(1, 10, ...)` — sized for
  one person occasionally checking in on a handful of dogs, not verified under genuine
  concurrent multi-user load. If usage ever grows past a few simultaneous sessions, requests
  beyond the pool's 10 connections would queue rather than fail outright, but that's untested
  reasoning, not a measured result. Fine at current scale; worth revisiting if Pawfolio ever
  gets shared with more than one household.
- **Location:** `db.py`, `_get_pool()`.

### Mobile UX: minor icon-button stacking on profile detail header

- **Severity:** Low
- **Details:** On a stacked mobile layout, the profile header's edit (pencil) and delete
  (trash) icon buttons each land in their own full-width row instead of sitting side by side
  next to the photo the way they do on desktop. Still clearly visible and comfortably tappable
  (confirmed in mobile screenshots) — just a little more vertical space spent than strictly
  necessary. Everything else tested clean across dashboard, profile list, profile detail, and
  the add-profile form at 390px width: no horizontal overflow anywhere, buttons/inputs all
  meet a comfortable touch-target size, long text wraps instead of forcing scroll.
- **Location:** `views/profile_detail.py` header layout (`header_cols`), `styles.py` mobile
  media query.

## Security / Usability / Edge-Case Test Pass — 2026-07-19

Full pass against the live deployed app (mypawfolio.streamlit.app) and its hosted Supabase
Postgres database, run before Phase 4 (auth) is built. Treats "no login yet" as the current
known state, not something to silently fix here — flagged below so it's tracked.

**Confirmed clean (no findings):**
- Full git history (every commit, all branches) re-scanned for secrets: clean. Deployed page
  source and 144 captured live network requests scanned for the Resend key / DB connection
  string / Supabase host pattern: zero matches.
- SQL injection: `'; DROP TABLE profiles; --'`, `' OR '1'='1`, UNION-based payloads, and a
  50,000-character string all round-tripped safely as literal stored text via `create_profile`
  — every query in `db.py` uses parameterized `%s` placeholders, never string-built SQL. Table
  intact, real data untouched after every attempt.
- XSS: `<script>alert(1)</script>` and `<img src=x onerror=alert(2)>` stored and redisplayed as
  literal escaped text, never executed (confirmed no `dialog` event fired, confirmed via direct
  DB round-trip and earlier UI-level testing with the same payloads).
- App is served over HTTPS (`https://mypawfolio.streamlit.app/`), confirmed directly.
- Environment variables: with `DATABASE_URL` genuinely unset (not just missing from the current
  process but with `.env` loading also disabled, to accurately simulate the deployed environment
  where no `.env` file is ever present), `db.py` raises a clear `RuntimeError` rather than
  silently falling back to anything — there is no local-file fallback left to fall back to.
- Resend/notifications failure handling: still confirmed graceful from the earlier deployment
  review — a simulated Resend API failure doesn't crash the app and doesn't mark events as
  falsely notified, so it retries cleanly on the next load. This is a real, working contrast to
  the database-error handling gap below.
- Regression: `get_upcoming_events` sorting/computation, the milestone notification logic, and
  the digest dedup functions were all re-verified directly against the live hosted database
  after all the deployment-phase changes and produce correct results.

### Issue: Any visitor can add, edit, or delete any data — expected for this phase, but flagging as required

- **Severity:** High
- **Steps to reproduce:** Open the public URL with no account, no login prompt anywhere.
  Create, edit, or delete any profile, vet, or record.
- **Expected vs. actual:** Expected (per the stated project plan — auth is Phase 4, not yet
  built). Actual, confirmed: there is currently zero barrier between "has the URL" and "can
  permanently delete Bobby Dugar's entire profile and every record on it." Logging this
  formally per instruction, not fixing it now — this is the single largest exposure until
  Phase 4 lands, and is the item most worth deciding on urgently if the URL is going to be
  shared or discovered before then.
- **Location:** Whole app — no authentication layer exists anywhere in `app.py` or any view.

### Issue: Database connection failures leak internal infrastructure details and full server-side tracebacks to any visitor

- **Severity:** High
- **Steps to reproduce:** Trigger any `psycopg2` connection failure — simulated locally by
  pointing `DATABASE_URL` at an invalid Supabase project (safe simulation, real production
  database never touched). In practice this is not a hypothetical: it's exactly what a real
  visitor would hit if they open Pawfolio while the Supabase free-tier project has auto-paused
  (see the existing "Supabase free-tier auto-pauses" entry above) — the two issues share one
  root cause and one fix.
- **Expected vs. actual:** Expected a friendly, on-brand "having trouble connecting, try again
  shortly" message. Actual, confirmed via direct capture of the rendered page: Streamlit's
  default error display shows the raw `psycopg2.OperationalError` — including the Supabase
  pooler hostname, its resolved IP address, and the port number — followed by a full Python
  traceback exposing internal server file paths and the app's internal function call chain
  (`init_db` → `get_conn` → `_get_pool` → psycopg2 internals), plus "Ask Google" / "Ask ChatGPT"
  buttons clearly meant for a developer's own debugging session, not a public visitor. No
  password or full connection string leaks, but meaningful infrastructure reconnaissance
  information does.
- **Location:** No `.streamlit/config.toml` exists in the project, so Streamlit's default
  `client.showErrorDetails` (full tracebacks) is in effect. `db.py`'s `get_conn()`/`_get_pool()`
  have no try/except of their own, and no view file wraps its `db.*` calls either, so an
  uncaught exception is the only thing that currently happens on a connection failure.
- **Fixed:** `get_conn()` now catches connection/query failures, logs the real error
  server-side via `print()` (still visible in Streamlit Cloud's logs), and raises a new
  `PawfolioDBError` carrying only a sanitized message. `app.py` catches that specific
  exception type around init/notification-check/page-render and shows "🐾 Pawfolio can't
  reach its database right now. This is usually temporary — try refreshing in a minute or
  two." instead. Deliberately scoped to `PawfolioDBError` only, not `Exception` broadly, so
  an unrelated real bug still surfaces normally rather than being masked. Verified locally
  with a simulated unreachable database: no hostname/IP/file-path/traceback reaches the
  page, and the real detail is still logged server-side for debugging.

### Issue: Supabase connection uses the full-privilege `postgres` role, not a scoped-down one

- **Severity:** Medium
- **Steps to reproduce:** `SELECT current_user, rolbypassrls, rolcreaterole, rolcreatedb FROM
  pg_roles WHERE rolname = current_user` against the configured `DATABASE_URL`.
- **Expected vs. actual:** Expected the app to connect with a role scoped to only what
  Pawfolio's own tables need. Actual, confirmed: the connection authenticates as `postgres`,
  Supabase's default project-owner role — `rolbypassrls: True` (bypasses any Row Level
  Security), `rolcreaterole: True`, `rolcreatedb: True`. This is the role the standard Supabase
  connection-string instructions hand you by default, not a misconfiguration specific to this
  setup, but it does mean the blast radius of `DATABASE_URL` ever leaking is the entire Supabase
  project, not just Pawfolio's data. `DATABASE_URL` itself is properly secret-managed (confirmed
  clean in the git-history and network scans above), so this is a defense-in-depth gap, not an
  active exposure right now.
- **Location:** Supabase project configuration (not application code) — tightening this means
  creating an additional restricted Postgres role with grants limited to Pawfolio's own tables
  and using that role's connection string instead of the default `postgres` one.

### Issue: Concurrent edits silently overwrite each other with no warning

- **Severity:** Medium
- **Steps to reproduce:** Open the same profile in two browser sessions (two tabs, or two
  devices). In session A, edit and save one field (e.g. breed). Before refreshing session B,
  edit and save a *different* field there (e.g. nickname) using session B's now-stale copy of
  the record.
- **Expected vs. actual:** Expected either both changes to merge, or some warning that the
  record changed underneath the second save. Actual, confirmed directly against the database:
  session B's save silently reverts session A's change back to its old value — every
  `update_profile`-style call writes the *entire* row from whatever the form loaded it as,
  with no version check, so the second save always wins completely and the first save's change
  vanishes without either session being told. Low real-world likelihood with a single user
  today, but a real, structural gap the moment Pawfolio is used from more than one device/tab
  at once (easy to hit accidentally — e.g. phone and laptop open to the same profile).
- **Location:** `db.py` — every `update_*` function (`update_profile`, `update_vaccination`,
  etc.) does an unconditional `UPDATE ... WHERE id = %s` with no `updated_at`/version column to
  detect a stale write.

### Usability: no onboarding context for a first-time visitor

- **Severity:** Low
- **Details:** Walked through the live app with no prior context. The empty-state and
  in-progress copy is charming and functionally clear moment-to-moment (button labels are
  obvious, "New Profile" is the clear first action), but there's no explanation anywhere of
  *what this app is for*, whose dogs these are, or that a random visitor's edits are real and
  permanent (ties directly into the no-auth item above — a visitor has no way to know this
  isn't a public demo/sandbox). Not blocking, since every individual screen is self-explanatory,
  but worth a short "About Pawfolio" note somewhere once there's an audience beyond one person.
- **Location:** `views/home.py` (no intro copy beyond the tagline "The feed, but it's just
  dogs.").

### Usability: loading states use Streamlit's generic skeleton, no Pawfolio-specific messaging

- **Severity:** Low
- **Details:** While data is being fetched (especially noticeable on a cold Supabase/Streamlit
  Cloud session, per the existing cold-start entries above), the page shows Streamlit's default
  gray skeleton blocks with no app-specific loading message. Not broken — it resolves into
  correct content every time it was tested — just a missed opportunity to keep the warm,
  quirky voice going through the wait instead of a generic loading placeholder.
- **Location:** No explicit `st.spinner()`/loading copy anywhere in `views/home.py` or `app.py`.

## Phase 4 Auth Review — 2026-07-18

Added Supabase Auth (email/password) and per-user `owner_id` data scoping, closing the
"anyone with the URL can edit my data" gap. Migrated to Supabase Storage for photos (private
bucket + RLS, server-side download instead of literal signed URLs — see note below). Data
isolation was tested directly, both automated and against the real production schema; the
items below are what's still open, per the requested review pass, not fixed silently.

### Note: "private + signed URLs" was requested, but photos are served a different way

- **Not a bug** — flagging so the actual mechanism is understood, since it doesn't literally
  match what was asked for by name. Photos live in a **private** Storage bucket protected by
  Row Level Security (each user can only read/write their own `{owner_id}/...` folder), which
  matches the "private" half of the request. But rather than generating a signed URL (a
  temporary public link with an expiry), the app fetches photo bytes server-side through an
  authenticated, request-scoped Supabase client and embeds them directly as base64 `data:`
  URIs in the page — the same technique already used for every image in this app since photos
  were only ever local files. Net effect is equal-or-stronger privacy (there's never a
  fetchable URL for a photo at all, signed or otherwise, so nothing can leak via a shared link
  or browser history) without signed-URL expiry/regeneration complexity. Worth knowing in case
  a future feature (e.g. public sharing) specifically needs a real shareable URL — that would
  need signed URLs added on top of this, not a replacement for it.
- **Location:** `photo_storage.py` (`get_photo_bytes`), `ui_helpers.py` (`_image_data_uri`).

### Issue: Signing up with an already-registered email shows a misleading "success" message

- **Severity:** Medium
- **Steps to reproduce:** Sign up with an email that already has a confirmed Pawfolio account
  (tested directly against the real account created for this migration).
- **Expected vs. actual:** Expected either an error ("that email already has an account") or a
  clear message. Actual: Supabase's signup API deliberately returns a success-shaped response
  for this case (`needs_confirmation: true`, no error) — this is intentional anti-enumeration
  behavior on Supabase's part, so an attacker can't probe which emails are registered by
  comparing error messages, and it's working correctly for that purpose. But the app's copy
  takes that response at face value and tells the user "🐾 Account created! Check your email
  for a confirmation link" — no account was created and (in most Supabase configurations) no
  email is sent, so a real user who forgot they'd already signed up is told to go check an
  email that isn't coming, then gets a confusing "incorrect password" if they try to log in
  with the new password they just chose. Does not leak security info (that part is fine by
  design) — purely a misleading-copy problem for a legitimate confused user.
- **Location:** `login_ui.py`, the `success and info["needs_confirmation"]` branch — can't
  actually distinguish "brand-new signup, awaiting confirmation" from "email already existed"
  using what `auth.sign_up()` currently returns from Supabase's API.

### Issue: No forgotten-password / password-reset flow anywhere in the UI

- **Severity:** High
- **Steps to reproduce:** Forget your password. Look for a way to recover the account from the
  login screen.
- **Expected vs. actual:** Expected a "Forgot password?" link sending a reset email (Supabase
  Auth supports this natively via `auth.reset_password_for_email()`). Actual: no such link or
  flow exists anywhere in `login_ui.py`. A locked-out user has no self-service path back into
  their own data — the only recovery today is a manual reset from the Supabase project
  dashboard, which isn't something an end user can do themselves.
- **Location:** `login_ui.py` (missing entirely), `auth.py` (no `reset_password` wrapper).
- **Fixed 2026-07-18:** Added a "Forgot password?" expander on the login tab
  (`auth.request_password_reset`) that emails a reset link without revealing whether the
  address has an account (matches Supabase's own anti-enumeration behavior — deliberately
  doesn't repeat the duplicate-signup mistake above). This Supabase project uses the
  "implicit" auth flow, so the link actually redirects back with the session tokens in the
  URL *fragment* (`#access_token=...&type=recovery`), not the query string — fragments never
  reach the server, so `st.query_params` can't see them directly. Discovered this by testing
  end-to-end against a real inbox (first attempt, built against the `token_hash`/query-string
  flow, landed back on a plain login page instead of the reset form). Fixed with a small
  client-side JS shim in `app.py` (`streamlit.components.v1.html`) that reads
  `window.parent.location.hash` and rewrites the URL to carry the same values as query
  params, which `st.query_params` then reads to hand off to `render_password_reset()`. That
  screen sets the session and new password together in one step
  (`auth.complete_password_reset`, now taking `access_token`/`refresh_token` directly rather
  than a `token_hash` needing a separate exchange), using a throwaway Supabase client scoped
  to just that call rather than the shared module-level one — `update_user()` needs a real
  saved session in the client instance itself (no way to pass it a bearer token directly,
  unlike the Storage calls), and reusing the shared client would risk one browser session's
  recovery bleeding into another's concurrent login. **Not yet confirmed end-to-end with the
  corrected code** — the first live click-through (before the fragment fix) landed on a plain
  login page instead of the reset form, which is what surfaced the fragment/query-string bug
  in the first place; a second attempt after the fix hit Supabase's own rate limit before
  reaching the email. Re-test once the rate limit clears: request a reset, click the email
  link, confirm it lands on "Set a new password" rather than back on login. **One manual step
  still required for production:** the reset link's target
  (`APP_URL`, defaults to `https://mypawfolio.streamlit.app`) must be on this Supabase
  project's Redirect URLs allow-list (Authentication → URL Configuration in the dashboard),
  or Supabase silently redirects somewhere else instead. **Minor tradeoff worth knowing:**
  moving the tokens from fragment to query string means they briefly appear in a form that
  *is* sent to the server (query strings, unlike fragments, are included in the HTTP
  request) — low risk for a short-lived, single-use, immediately-consumed token against a
  server that isn't logging full request paths, but worth remembering if request logging is
  ever added.

### Issue: Login session never refreshes and doesn't survive a browser refresh

- **Severity:** Medium
- **Details:** Two related gaps found while testing session persistence:
  1. `auth.sign_in()` stores only the short-lived `access_token` in `st.session_state`,
     discarding Supabase's `refresh_token` entirely. Supabase access tokens commonly expire
     around an hour. Nothing in the app re-authenticates or refreshes after that — regular
     dog-profile data keeps working fine the whole time (it goes straight to Postgres via
     `db.py`, independent of the Supabase Auth session), but photo operations specifically
     start failing once the token expires: `photo_storage.get_photo_bytes()` catches the
     error and quietly returns `None` (an existing photo just stops rendering, no message),
     while `photo_storage.upload_photo()` has no error handling at all, so uploading or
     replacing a photo past that point would surface as an unhandled exception rather than a
     friendly message. A user would see "everything else still works but photos broke" with
     no indication why or how to fix it (short of logging out and back in).
  2. Separately, a plain browser refresh (not just long idle time) also logs the user out
     immediately — `st.session_state` is in-memory per Streamlit session with nothing
     persisted to a cookie or `localStorage`, so reloading the tab seconds after logging in
     lands back on the login screen. This came up directly while testing today (a stray
     background process on the same port made a refresh necessary, and required logging in
     again from scratch).
- **Location:** `auth.py` (`sign_in()` — no `refresh_token` captured or used anywhere),
  `photo_storage.py` (`upload_photo()` has no try/except, unlike `get_photo_bytes()` and
  `delete_photo()`), `app.py`/`login_ui.py` (session lives only in `st.session_state`, no
  persistence layer).

### Verified: cross-user data isolation (mostly — see correction below)

- **Not a bug** — confirmed working for every profile/vet/child-record query, noting it
  explicitly since it was the core ask for this phase. Checked two ways: (1) four dedicated
  automated tests exercising `get_all_profiles`, `update_profile`, `delete_profile`, and
  `get_upcoming_events` with a second owner's data present, all passing; (2) directly against
  the real production schema — after migrating the 5 existing profiles and 1 vet to the real
  account's `owner_id`, `get_all_profiles()` and `get_all_vets()` scoped to that `owner_id`
  return exactly those records and nothing else.
- **Correction (2026-07-18 full test pass):** the claim "no query anywhere in `db.py` omits
  the `owner_id` filter" written here originally turned out to be wrong — see the "Cross-owner
  data leak via friend-linking" finding below, found during a full Phase 1–4 regression pass.
  One relationship (`friends.friend_profile_id`) does not get the same defense-in-depth
  ownership check every other cross-reference (siblings, vet links) already has. Leaving this
  note in place rather than quietly rewriting history, since the original claim was tested
  incompletely — it checked the tables directly, not every JOIN across tables.

## Full Phase 1–4 Regression Pass — 2026-07-18

End-to-end test pass across everything built so far: core CRUD (Phase 1), care/logistics,
email notifications, hosted deployment, and multi-user accounts/data scoping (Phase 4).
Testing only, per instructions — nothing below was fixed as part of this pass. Covered: a
full `db.py` audit (every query, checked for owner_id scoping), live cross-owner reproduction
attempts (two real throwaway owner UUIDs, tried to read/edit/delete each other's data through
every write/read function, and through session_state tampering — the closest equivalent to
URL manipulation in this app's architecture, since profile selection is never driven by a URL
query param anywhere in the codebase), the full automated test suite, and a code-level review
of session/login edge cases and mobile CSS. No browser automation tool is available in this
environment, so mobile responsiveness could only be reviewed at the CSS level, not visually
confirmed on an actual small screen — flagged below rather than silently assumed fine.

### Issue: Cross-owner data leak via friend-linking

- **Severity:** High — **FIXED 2026-07-18**
- **Steps to reproduce:** Call `db.add_friend(profile_id, name, None, notes, owner_b,
  friend_profile_id=<a profile_id owned by owner_a>)`, then `db.get_friends(profile_id,
  owner_b)`.
- **Expected vs. actual:** Expected `add_friend` to reject linking to a profile it doesn't
  own, the same way `add_sibling` (checks both profiles belong to the caller before creating
  the link) and `link_vet_to_profile` (checks both the profile and the vet) already do.
  Actual, reproduced directly: `add_friend` only verifies the profile being added *to*, never
  the linked `friend_profile_id`. The insert succeeds, and every subsequent `get_friends()`
  call for that profile then returns the other owner's dog's `linked_name`, `linked_dob`, and
  `linked_photo_path` (a real Supabase Storage path, which also reveals the other owner's
  Auth UUID as its folder prefix) — confirmed via a live reproduction against two real
  throwaway owner ids, not just reasoning about the code.
- **Why it's not currently exploitable through the app itself:** the "Add friend → link to an
  existing pup" picker in `views/profile_detail.py` only ever offers candidates from
  `get_all_profiles(owner_id)` — the current user's own dogs — so a normal user clicking
  through the UI can never actually select another owner's profile to link. The gap is real at
  the `db.py` layer, not reachable at the UI layer today. That said, it's the one place in the
  whole data-access layer that relies on the *caller* (the UI) to have already done the
  scoping, rather than enforcing it itself — every other similar cross-reference doesn't trust
  the caller. Flagging as High rather than Critical because there's no live exploit path today
  (would need direct DB access or a future caller that doesn't scope its own candidate list),
  but it's a real gap in the core guarantee this whole phase was built around, not merely a
  theoretical one — recommend treating it as a "fix before it matters" item rather than
  deferring indefinitely.
- **Location:** `db.py` — `add_friend()` (no ownership check on `friend_profile_id`) and
  `get_friends()` (the `LEFT JOIN profiles lp` has no `lp.owner_id = %s` condition). Compare
  to `add_sibling()`'s `owned_count != 2` check and `link_vet_to_profile()`'s `owns_profile`/
  `owns_vet` checks for the pattern this should follow.
- **Fixed 2026-07-18:** `add_friend()` now checks, before inserting, that `friend_profile_id`
  (when provided) belongs to the same `owner_id` as `profile_id` — raises `PawfolioDBError`
  otherwise, matching `add_sibling()`'s pattern exactly. `get_friends()`'s `LEFT JOIN` also
  gained `AND lp.owner_id = p.owner_id` as a second, independent layer of defense on the read
  side, so even a row that somehow got created without going through `add_friend()` (a future
  migration script, manual DB edit, etc.) still can't surface another owner's name/photo/dob —
  it would just fall back to showing the friend's name as it was at link time, the same
  graceful fallback already used when a linked profile is deleted. Verified with a live
  reproduction in an isolated test schema: the exact cross-owner call that leaked data before
  now raises `PawfolioDBError("Couldn't link that profile as a friend.")`; a same-owner linked
  friend and a freeform (non-linked) friend both still work exactly as before. Full test suite
  re-run clean afterward (72 passed, same 6 pre-existing unrelated failures, no new ones).

### Issue: Logging out doesn't clear `selected_profile_id`

- **Severity:** Medium
- **Steps to reproduce:** Log in as User A, open a specific dog's profile, log out, log in as
  User B on the same browser session (shared device), and land on Profile Detail without
  picking a dog first (e.g. it's still the active page from A's session).
- **Expected vs. actual:** Expected either the normal "pick a profile" screen or a clean
  redirect to Home. Actual, reproduced directly: User B sees "This profile no longer exists,"
  since `selected_profile_id` still holds User A's profile id and `get_profile` correctly
  returns nothing for User B's `owner_id` — **no data leaks** (confirmed: this is a UX
  confusion finding, not a security one, the owner-scoping itself holds correctly here), but
  it's a needlessly alarming message for someone who just logged in.
- **Location:** `app.py`'s log-out handler only clears `auth_user` and `_notify_checked` from
  `st.session_state`, not `selected_profile_id`.

### Confirmed working: original "anyone with the URL" exposure gap is closed

- **Not a bug.** `app.py` checks `st.session_state.get("auth_user")` and calls `st.stop()`
  before any profile data is queried or any page (`Home`, `All the Pups`, `New Profile`,
  `Profile`) can run — confirmed this check happens before `pg.run()`, and since Streamlit's
  `st.navigation` model re-executes `app.py` from the top on *every* page navigation (there's
  no separate URL route that skips app.py's own script body), there's no way to reach any view
  file without passing this gate first. Confirmed live earlier in this same session: visiting
  the app with no session produces only the login screen, nothing else.

### Confirmed working: cross-owner rejection on every other write path

- **Not a bug.** Live reproduction (two real throwaway owner ids) confirmed correct rejection
  for: `add_sibling` (cross-owner link → `PawfolioDBError`), `link_vet_to_profile` (linking
  another owner's vet → `PawfolioDBError`), `delete_vet` (cross-owner delete → silent no-op,
  target vet still exists for its real owner), `unlink_vet_from_profile` (cross-owner unlink →
  silent no-op, link still exists). Matches the existing automated tests
  (`test_update_profile_ignores_other_owners_id`, `test_delete_profile_ignores_other_owners`,
  etc.), extended here to the vet/sibling paths those tests didn't cover.

### Confirmed working: session_state tampering (this app's equivalent of URL manipulation)

- **Not a bug.** This architecture has no URL-query-param-driven navigation for profile
  selection anywhere (`selected_profile_id` is only ever set from within the app's own click
  handlers — confirmed via a full-codebase search), so the closest realistic attack is
  tampering with `st.session_state` directly. Simulated via `AppTest`: logged in as owner B
  with `selected_profile_id` forced to owner A's profile id. Result: "This profile no longer
  exists," no data rendered — `get_profile`'s owner filter holds.

### Confirmed working: per-user notification digest cap

- **Not a bug.** `was_digest_sent_today`/`record_digest_sent` are correctly isolated per
  owner — verified live that recording a digest as sent for owner A does not affect owner B's
  independent "sent today" status. (No dedicated automated test exists for this specifically;
  covered here by direct reproduction instead.)

### Confirmed working: full regression suite, no new failures

- **Not a bug.** `pytest tests/ -v` → 72 passed, 6 failed — the same 6 that were already
  failing before any of today's changes, all pre-existing and unrelated (stale assertions
  against a page layout from before the 2026-07-14 redesign — see the "Same exact 6
  pre-existing failures" confirmation earlier in this file). Dashboard due-date logic, all
  CRUD, and notification dedup logic are all exercised by this suite and all still pass with
  the full owner_id scoping in place.

### Not independently verified this pass: mobile responsiveness

- **Severity:** N/A (testing gap, not a finding)
- **Details:** No browser automation tool is available in this environment, so mobile
  layout could only be reviewed at the CSS source level (`styles.py`'s `@media (max-width:
  640px)` block), not visually confirmed on an actual narrow viewport. Phase 4 didn't touch
  `styles.py` at all, and the new login/signup/reset screens use only standard Streamlit
  primitives (`st.tabs`, `st.form`, `st.text_input`, `st.expander`) already covered by the
  existing global button/heading rules — reasoned to be fine, not confirmed fine. Recommend
  an actual phone/DevTools-narrow-viewport check of the login screen and the "Forgot
  password?" expander specifically, since those are new since the last visual mobile pass.

### Not independently verified this pass: password reset end-to-end click-through

- **Severity:** N/A (testing gap, not a finding — tracked in detail in the Phase 4 Auth
  Review section above)
- **Details:** The fragment/query-string bug was caught and fixed, but the corrected version
  hasn't been click-tested to completion yet — Supabase's rate limit was hit right after the
  fix. Re-test once it clears.

## Visual Polish Pass — Dashboard & Profile Due-Dates — 2026-07-18

Applied the requested layout/color treatment to the dashboard and profile-detail health
section: a 2-column responsive grid for the dashboard's Upcoming feed, icon circles + urgency
badges on every card, and the same treatment extended to the profile page's due-date rows
(vaccinations, non-ongoing medications, baths, food refills, boarding check-ins,
registration). Tag pills for likes/dislikes/toys/foods turned out to already be implemented
(`ui_helpers.show_tag_pills`, already applied everywhere those fields display) — nothing to
change there. Presentation only, per instructions: no changes to `db.py`, CRUD logic, auth,
or notification logic. Full test suite re-run clean after every step (72 passed, same 6
pre-existing unrelated failures, no new ones — including one additional flaky failure,
`test_app_home_loads_without_exception`, seen twice under full-suite load but passing every
time in isolation; looks like test-suite connection-pool contention, not a real issue, but
noting it since it's new *noise* even if not a new *failure*).

### Choice: Font Awesome (CDN) instead of emoji for icon circles

- Explicitly chosen over emoji when asked directly, on the condition it's free — it is (the
  Free tier, loaded from cdnjs.cloudflare.com, no account or API key needed, no cost). This is
  a deliberate departure from this codebase's usual no-external-dependency default (inline SVG
  mascot, base64-embedded photos, no other CDN resources anywhere) in favor of a sharper
  "app-like" look for these specific icon circles.
- **Not visually confirmed** — no browser automation tool is available in this environment, so
  the `@import` actually resolving, the icon glyphs actually rendering, and their exact visual
  weight next to the emoji used everywhere else on the page could only be reasoned about from
  the CSS/HTML source, not seen. **Please check this first** — open the local app and confirm
  the dashboard cards show real icon glyphs (syringe, droplet, cake, etc.), not empty circles
  or a fallback box glyph. If the CDN import doesn't work for any reason (corporate firewall,
  ad-blocker blocking cdnjs, offline use), every icon circle would silently show as a plain
  colored circle with no glyph inside (Font Awesome's own missing-icon behavior, not a broken-
  image icon or a crash) — degrades gracefully, but isn't invisible-if-broken the way the rest
  of the app's zero-dependency approach otherwise guarantees.
- **Location:** `styles.py` (the `@import` line, first rule in the stylesheet), `ui_helpers.py`
  (`_TYPE_ICON`, `icon_circle_html`).

### Fixed during this pass: gold-badge text contrast in dark mode

- Caught during the review pass itself, fixed immediately rather than left open (small,
  contained CSS-value change, not a design decision needing sign-off). The "This week" badge
  and the food-refill icon circle both sit on `--pf-accent` (gold), which stays light-toned in
  *both* light and dark mode by design (see `styles.py`'s `:root` vs `@media
  (prefers-color-scheme: dark)` blocks) — using the theme-flipping `var(--pf-text)` for the
  badge label, and a fixed near-white for the icon glyph, both meant light-colored text landed
  on a light gold background in dark mode specifically (and was marginal even in light mode).
  Fixed by giving both a fixed dark color (`#4A3225`) instead of following the theme variable —
  correct in both modes now, since the gold background itself doesn't change between them.
  Every other icon-circle/badge color pairing was checked the same way and found fine (their
  backgrounds are dark/saturated enough in both modes for the fixed near-white to stay
  readable) — this was the one exception.
- **Location:** `ui_helpers.py` — `_TYPE_ICON["food_refill"]`'s icon color,
  `urgency_badge_html()`'s `"week"` tier.

### Scoping decision: "New Pack Members" cards left unchanged

- The icon-circle/badge treatment was applied to the Upcoming feed and to due-date rows on the
  profile page, per the instructions' explicit examples. "New Pack Members" cards (shown above
  the Upcoming feed when a profile was added in the last 7 days) were deliberately left in
  their original single-column layout with no icon circle — they're a celebration/announcement
  card with no due date or urgency concept, not an "upcoming/status" item, so neither half of
  the new pattern (type icon signaling *what kind* of due thing this is, urgency badge
  signaling *how soon*) cleanly applies. Flagging the scoping choice explicitly in case a
  celebratory 🎉 icon circle (no badge) is wanted there too for pure visual consistency across
  the whole dashboard page — easy to add if so, just deliberately left out rather than
  overreaching past what was actually asked for.

### Not independently verified this pass: actual mobile rendering of the new grid

- Same limitation as the Phase 1–4 regression pass above — no browser tool available, so the
  2-column dashboard grid collapsing to 1 column on a narrow viewport could only be reasoned
  about (it relies on Streamlit's existing `st.columns` auto-stacking behavior below the
  established 640px breakpoint, already relied on elsewhere in `styles.py`), not seen. Also
  worth an eye on the icon-circle + badge header row specifically at narrow widths — it's a
  `display:flex; justify-content:space-between` row that hasn't been checked against a very
  long urgency label (e.g. "14d overdue") on the smallest supported phone width.
