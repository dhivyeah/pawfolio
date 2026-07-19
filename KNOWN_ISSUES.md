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

## Adversarial / Exploratory Pass — 2026-07-19

Went beyond the structured Phase 1–4 checklist: explored the app the way a careless real user
or someone probing for weaknesses might, using direct `db.py` reproduction (isolated/self-
cleaning against production, same discipline as every other pass), `AppTest` session-state
simulation, and code review. Two findings below need **your decision before anything else** —
both are genuine cross-user data exposures, reachable through completely normal use (no
malicious intent required), found while specifically re-checking the cross-user visibility
guarantee from Part 1. Everything else is lower-stakes. Full test suite re-run clean after the
one fix applied during this pass (XSS escaping) — 72 passed, same 6 pre-existing failures.

### 🔴 Logging out doesn't clear the toast-notification queue — the next person to log in on the same browser can see a fragment of the previous user's data

- **Severity:** High — **FIXED 2026-07-19**
- **Steps to reproduce:** Log in as User A. On the Profile Detail page, do anything that shows
  a confirmation toast that names something specific — e.g. "Set as primary vet" (toast:
  "**{vet name}** set as primary vet"), unlinking a vet, removing a sibling, adding/editing a
  friend. Log out **without visiting Home or All the Pups afterward** (Profile Detail never
  triggers the toast to actually display — see Location below). Log in as a different user (or
  have someone else use the same browser) — they land on Home by default.
- **Expected vs. actual:** Expected a queued notification to either fire before logout or be
  discarded on logout. Actual, reproduced directly: the queued toast survives in
  `st.session_state` across the logout, and fires for **whoever loads Home next** — confirmed
  with a simulated handoff where User B's very first page load showed a toast containing User
  A's private vet name, with no action from B beyond just logging in and landing on the
  default page. This isn't a narrow timing race — since actions taken *on* Profile Detail don't
  consume their own toast (only Home/All the Pups do), the queued message routinely survives
  until the next visit to Home regardless of how much time passes, making "log out right after
  editing something, then someone else logs in" a very ordinary sequence to hit by accident on
  a shared or reused browser/device.
- **Location:** `app.py`'s log-out handler only clears `auth_user` and `_notify_checked` from
  `st.session_state` — never `_toast_queue`. `ui_helpers.py`'s `queue_toast()`/
  `render_queued_toast()`.
- **Why this needs your call:** The actual data exposed is narrow (one toast message, not a
  full profile), and today it only matters on a genuinely shared/reused browser session (a
  household computer, a borrowed device, or the app's own multi-tab quirks) — not remotely
  exploitable. But it's a real violation of "one user should never see any fragment of
  another's data," which was the explicit point of Phase 4, so it seemed worth flagging as
  High and asking rather than just quietly fixing or downgrading it myself. The fix itself is
  small (clear `_toast_queue` — and see the related finding below, `_pending_delete` — on
  logout), but wanted your sign-off before touching session/logout behavior again given how
  much back-and-forth debugging that area already took during setup.
- **Fixed 2026-07-19:** `_toast_queue` added to the set of keys cleared in `app.py`'s log-out
  handler, alongside `auth_user` and `_notify_checked`. Verified via a real logout-button click
  in `AppTest` (not just reasoning about the code) — a queued toast containing private data
  present before logout is confirmed gone from `st.session_state` immediately after. Full test
  suite re-run clean (72 passed, same 6 pre-existing unrelated failures). The related
  `_pending_delete` leak (Medium, below) was deliberately left open — flagged as a decision for
  you, not fixed as part of this "critical/high, no-brainers only" pass.

### 🔴 NEEDS YOUR DECISION: Logging out doesn't clear a pending delete-confirmation dialog — the next person to log in can see (but not act on) a fragment of the previous user's data

- **Severity:** Medium
- **Steps to reproduce:** Log in as User A. Click "Remove" on any record (a vaccination, a
  friend, a surgery, etc.) to queue the confirm-delete dialog, then leave without clicking
  "Yes, delete" or "Cancel" or the dialog's own X/Escape (e.g. close the browser tab entirely,
  or the browser/app crashes). Log in as a different user and visit their own Profile Detail
  page.
- **Expected vs. actual:** Expected either the dialog to be gone, or (worst case) a generic
  confirmation with no specifics. Actual, reproduced directly: User B's own profile page opens
  with a modal already up front reading "Delete the vaccination **Rabies (Owner A private
  info)**? This can't be undone." — User A's specific record name, verbatim, unprompted. If B
  were to click "Yes, delete," the underlying `delete_*` call still carries **B's** `owner_id`
  (looked up fresh from session state at click time, not A's — only the record id was
  captured), so it silently no-ops against B's own account rather than actually deleting A's
  record — confirmed no real cross-account deletion is possible here, only the informational
  leak of the label itself.
- **Location:** Same root cause as above — `app.py`'s log-out handler doesn't clear
  `_pending_delete`. `ui_helpers.py`'s `request_delete()`/`render_pending_delete_dialog()`.
  Narrower than the toast issue: Streamlit's own dialog-dismiss handling (`on_dismiss=`) already
  clears this correctly for every *normal* way of leaving the dialog (X, Escape, click-outside,
  Cancel) — only an abrupt tab close/crash leaves it dangling, so it's less likely to trigger
  in practice than the toast issue.
- **Why this needs your call:** Same reasoning as above — lower severity here since no actual
  deletion can happen and it requires a more abrupt exit, but it's the same category of bug
  and the same fix location, so flagging together rather than separately.

### Fixed during this pass: stored HTML/JS injection via tag fields (self-XSS today, real risk once sharing ships)

- **Severity:** Medium — **FIXED 2026-07-19**
- **Steps to reproduce (before the fix):** Type `<img src=x onerror=alert(1)>` into "Likes" (or
  Dislikes/Toys/Foods/Games), save, view the profile's Personality tab.
- **Expected vs. actual:** Expected the text to render literally. Actual, confirmed directly:
  `ui_helpers.show_tag_pills()` interpolated each tag into an HTML `<span>` and rendered it via
  `unsafe_allow_html=True` with no escaping — a `<script>` or `<img onerror=...>` typed into any
  tag field would execute as real HTML/JS, not display as text.
- **Why Medium, not Critical, as found:** Every tag field is scoped to the profile's own owner
  (confirmed — no query anywhere renders another owner's likes/dislikes to you), so this could
  only ever attack the same account that typed the payload in — self-XSS, not a cross-user
  attack, *today*. Flagging why it still matters: `profile_type` already has a `community_dog`
  option explicitly earmarked for future shared/public visibility (per the original Phase 4
  spec's "no shared/public visibility *yet*") — the moment that ships, this becomes a real
  stored-XSS vector against other users, so it seemed worth fixing now rather than waiting.
- **Fixed:** `show_tag_pills()` now runs each tag through `html.escape()` before interpolating
  it into the `<span>`. Verified the malicious payload above now renders as inert escaped text
  (`&lt;img src=x onerror=alert(1)&gt;`) instead of live HTML. No other `unsafe_allow_html=True`
  call site in the codebase interpolates user-controlled text unescaped — checked every one
  (`show_photo`'s image src is a base64 URI we generate, the mascot SVG is a fixed template,
  the icon-circle/urgency-badge HTML only ever contains fixed labels and integers).
- **Location:** `ui_helpers.py` — `show_tag_pills()`.

### Confirmed working: exhaustive cross-owner mutation sweep

- **Not a bug.** Extended Part 1's spot-checks to every remaining write/read function not yet
  individually tested: `update_vaccination`, `delete_vaccination`, `update_medication`,
  `delete_medication`, `update_surgery`, `delete_surgery`, `update_vet_visit`,
  `delete_vet_visit`, `update_bath`, `delete_bath`, `update_food_refill`,
  `delete_food_refill`, `update_boarding_stay`, `delete_boarding_stay`, `update_friend`,
  `delete_friend`, `update_vet`, `delete_vet`, `get_vet`. Attempted every one as an owner who
  doesn't own the target record — all either silently no-op (0 rows affected) or return
  nothing, with zero exceptions and zero actual data changes, confirmed by re-reading every
  record afterward.

### Confirmed working: no SQL injection

- **Not a bug.** Created a profile with the literal name `Rex'; DROP TABLE profiles; --` —
  stored verbatim as inert text data (every query in `db.py` uses parameterized `%s`
  placeholders, never string-formatted SQL), and the `profiles` table remained fully intact
  and queryable afterward. As expected given the existing code, but worth confirming directly
  rather than assuming.

### Confirmed working: Postgres-level constraints hold even when the app layer doesn't check first

- **Not a bug.** `create_profile()` has no application-level check on `profile_type`, but
  Postgres's own `CHECK` constraint correctly rejected an invalid value (`not_a_real_type`)
  outright — caught by `get_conn()`'s existing `except psycopg2.Error` handler and surfaced to
  the (simulated) user as the same safe generic message used for every other database error,
  never the raw constraint-violation text (which includes the full failing row, including the
  owner's UUID) — confirmed that detail only ever reaches the server-side `print()` log, never
  the UI.

### Issue: An empty/blank profile name can be saved by bypassing the UI's own validation

- **Severity:** Low
- **Steps to reproduce:** Call `db.create_profile()` directly with `"name": ""` (the real Add
  Profile form blocks this client-side, but nothing stops a differently-built caller).
- **Expected vs. actual:** Expected a database-level safeguard (`NOT NULL` plus a non-empty
  check, or similar) as a second line of defense. Actual: saved successfully with an empty
  string — `profiles.name` is `NOT NULL` but Postgres doesn't consider `''` a violation of
  that. Required-field validation exists only in the UI layer today, not the data layer.
- **Location:** `db.py` — `create_profile()`, `update_profile()`. Same theme as existing
  KNOWN_ISSUES item 13 ("editing an existing record doesn't re-validate required fields"), one
  layer deeper.

### Confirmed working: extreme and malformed dates don't crash anything

- **Not a bug.** A due date of `9999-12-31` saves and displays correctly, and correctly stays
  out of the 30-day upcoming-events list (way outside the horizon) rather than erroring. A
  fully malformed date string (`"not-a-date"`) saves without validation (no format-checking at
  the DB layer — `next_due_date` etc. are plain `TEXT`) but doesn't crash `get_upcoming_events`
  or any date-parsing code — every parsing site already wraps `datetime.strptime` in a
  `try/except ValueError` and simply skips the unparseable record rather than failing the
  whole page. A `dob` of `0001-01-01` doesn't crash `calc_age_str` either, just produces an
  absurd-but-harmless "~2025y old". (Separately: this pass's `9999-12-31` test *reinforces*,
  rather than contradicts, the already-documented "due dates >~10 years out silently fail to
  save" issue elsewhere in this file — that one is specifically about `st.date_input`'s own
  widget range limit, not the database, which this test bypassed entirely by calling `db.py`
  directly.)

### Issue: 25 concurrent requests exhaust the connection pool, surfacing as a generic "can't connect" error

- **Severity:** Low (confirms and strengthens an already-documented Low-priority item, not a
  new independent finding)
- **Steps to reproduce:** Fire 25 concurrent `link_vet_to_profile()` calls (or any other db.py
  function) from separate threads.
- **Expected vs. actual:** 10 succeeded (the pool's max size), the other 15 all failed with
  "Couldn't connect to the database right now." — a reasonable-sounding message, but the
  database was never actually unreachable; the *pool* was simply out of connections. No
  duplicate rows or corrupted state resulted from the ones that did succeed (the
  unique-constraint-guarded check-then-insert pattern held correctly under load in this test —
  a lower-concurrency race attempt, 8 threads, also produced zero duplicates). This is
  concrete, reproduced evidence for the existing "Connection pool sized for personal-app scale,
  not tested under real concurrent load" entry elsewhere in this file, which was previously
  reasoning without a live test behind it.
- **Location:** `db.py` — `_get_pool()` (`ThreadedConnectionPool(1, 10, ...)`).

### Confirmed working (with one caveat already documented elsewhere): Storage RLS and photo privacy

- **Not a bug**, but not fully re-verified live this pass either — flagging the reasoning
  rather than re-testing something Part 1 already covered structurally. Cross-user Storage
  access is enforced by a Postgres RLS policy keyed to `auth.uid()` from the caller's actual
  signed JWT (`(storage.foldername(name))[1] = auth.uid()::text`) — this is enforced by
  Supabase/Postgres itself based on a cryptographically-signed token claim, not application
  logic that could have a gap, so a live cross-account replay test wasn't repeated here (would
  have meant creating a second real confirmed account against Supabase's Auth email service,
  which is still rate-limited from earlier testing). The related, already-documented caveat
  stands: **`photo_storage.upload_photo()` still has no error handling** — reproduced directly
  this pass with a garbage access token (simulating a session that expired mid-use): raises an
  uncaught `StorageApiError` (`403, "JWS Protected Header is invalid"`). That specific message
  doesn't itself leak a hostname, but since nothing catches it, it would reach the browser as
  Streamlit's raw default exception page — full Python traceback, real server file paths,
  internal call structure — exactly the category of leak `db.py`'s `PawfolioDBError` wrapper
  was built to prevent, just not extended to this newer code path.

## Summary of this pass, by severity

- **🔴 High, fixed 2026-07-19:** toast-queue leak across logout (real content leak, easily
  triggered by ordinary use)
- **🟡 Medium, still needs your decision (same root cause, lower stakes, deliberately left open
  in the "critical/high only" fix pass):** pending-delete dialog leak across logout (label leak
  only, no actual cross-account deletion possible, requires an abrupt exit to trigger)
- **🟡 Medium, fixed already:** stored HTML/JS injection via tag fields (self-XSS today, fixed
  proactively given the risk once sharing ships)
- **🟢 Low:** empty profile name bypassable outside the UI; connection-pool exhaustion under
  concurrent load (confirms an existing entry with a live test)
- **Confirmed working, no action needed:** exhaustive cross-owner mutation sweep (every
  remaining write/read function), no SQL injection, Postgres constraints hold even without an
  app-level check, extreme/malformed dates don't crash anything, Storage RLS design is sound
  (photo-upload error handling gap already tracked separately)

## Visual Redesign Pass — "Bold Content, Calm Chrome" Color System — 2026-07-19

Replaced the per-type icon/badge colors from the 2026-07-18 polish pass with a single
app-wide color system: one accent (`--pf-primary`) for every piece of structural chrome (nav,
buttons, headers), and four fully-tinted category colors reserved for dashboard/due-date
*content* cards only (health/care/social/routine). Applied consistently to navigation (top nav
is now a pill-shaped segmented control), the dashboard grid, and the profile page (new
header/tag-pill/Identity-section hierarchy, plus the same category tint on due-date rows).
Presentation only — no changes to `db.py`, CRUD logic, auth, or notification/due-date
calculation logic. Full suite re-run clean: 72 passed, the same 6 pre-existing failures as an
unmodified checkout (confirmed by `git stash`-ing this pass's changes and re-running — those
failures exist independent of anything done here, mostly stale assertions from an earlier
profile-page refactor), no new regressions. One test (`test_top_nav_has_only_home_and_...`)
was updated, not just left passing by luck — it asserted the literal button key `"nav_home"`,
which now legitimately varies (`"nav_home_active"` vs `"nav_home"`) depending on which tab is
currently selected, since that's how the active segment's fill color is expressed.

### Choice: category mapping for dashboard/due-date cards, and where it doesn't cleanly fit

- **health** (coral/red tint): vaccinations, medications.
- **care** (soft blue tint): baths, food refills, boarding check-ins.
- **social** (pink tint): a dog's own birthday, a friend's birthday, and "New Pack Members"
  welcome cards (no due date/urgency concept, but thematically the closest fit — a
  celebratory, relationship-flavored card, not a chore).
- **routine** (soft green tint): Chennai Corporation registration renewals.
- **Doesn't cleanly apply — registration.** The instructions' own examples group "vaccines,
  meds, vet visits, surgeries" under health, but registration renewal is bureaucratic
  paperwork, not a medical event, even though it currently lives on the Health tab UI-wise.
  Filed it under **routine** instead (a logistics chore, closer to "adjacent to health" than
  "health" itself) rather than force-fitting it into the coral/red tint. Worth a second look if
  that reads oddly in practice.
  Note on the categories that *are* in the instructions' health example: this app doesn't
  currently generate dashboard reminders for surgeries or vet visits at all (`get_upcoming_events`
  only surfaces vaccinations/medications from that list — surgeries and vet visits are
  historical records with no due date), so there was nothing to categorize for those two; the
  mapping above only covers types that actually appear as dashboard/due-date cards today.
- **"community dog updates"** (mentioned in the instructions' social example) has no
  corresponding event type in the current data model — the closest existing thing is a
  `new_profile` card for a `community_dog`-type profile, already covered by the `new_profile`
  → social mapping above. Nothing further to do unless/until a real "community dog activity"
  event type gets built.

### Choice: danger-red delete buttons kept as a deliberate exception to "single accent"

- "Don't introduce other colors into buttons or navigation" was applied to every button
  *except* the existing red-outline treatment on delete/danger actions (`key="delete_..."`,
  `--pf-danger`) — kept on purpose as a standard hazard-color convention (an irreversible
  delete should look different from every other button), not an oversight. Every other button
  tier (solid primary, dashed "add new", ghost "cancel/mute") already used only
  `--pf-primary`/`--pf-text-muted` before this pass and still does.

### Scoping decision: "All the Pups" profile-list cards stay neutral, not category-tinted

- The instructions describe fully-tinted category colors as reserved for "dashboard status
  items" / content cards, and explicitly call out that the profile page's tag-pills should use
  the muted style "not the bold category colors." A dog's own profile card in the list view
  isn't itself health/care/social/routine content — it's a navigational entry point — so it
  keeps the existing neutral `--pf-card-bg` card style with the accent-colored hover lift,
  consistent with "calm chrome" for anything that isn't a status item.

### Scoping decision: dislikes/foods-to-avoid left out of the profile header's tag-pill summary

- The header's new merged "at a glance" pill row (likes, favorite toys, favorite foods,
  favorite games) intentionally excludes dislikes and foods-to-avoid — those are cautionary
  information, not "favorites," and mixing them into one undifferentiated pill row risked
  making a food allergy read the same as a favorite treat. Both fields are still shown, fully
  labeled and separated, inside the Personality tab exactly as before.

### Not visually confirmed: desktop max-width, mobile layout, and category-tint contrast

- **No browser automation tool is available in this environment** (same limitation noted for
  the Font Awesome CDN choice on 2026-07-18), so none of the following were seen rendered —
  only reasoned through from the CSS source and the dev server's absence of any runtime error:
  - The 700px `max-width` + `margin: auto` on `stMainBlockContainer`, meant to stop the
    dashboard/profile pages from stretching edge-to-edge on a laptop/desktop monitor while
    leaving mobile widths untouched (the cap has no effect once the viewport is already
    narrower than it). **Please check a real desktop-width browser window first** — this is
    the change with the most room to look wrong without being caught by any test.
  - The four category-tint background colors against their text/badge overlay in **dark
    mode** specifically — light-mode contrast (dark `--pf-text` on light pastel tints) is
    low-risk, but the dark-mode tints were hand-picked to mirror how `--pf-primary` already
    shifts lighter in dark mode (a pattern this codebase already uses and had previously
    confirmed acceptable), not measured with an actual contrast checker.
  - The pill-shaped nav's appearance at the narrowest phone widths (~375px) with two words
    ("🏠 Home", "🐾 Pups") per segment instead of the old single-emoji buttons — should fit
    comfortably next to the Log out button based on the column proportions used, but wasn't
    seen.
- **Location:** `styles.py` (`stMainBlockContainer` max-width rule, `--pf-cat-*` dark-mode
  values, `.st-key-nav_pills` rules).

## Mobile-Viewport Fixes Pass — 2026-07-19

Targeted fixes from an actual mobile-viewport review, not another general pass — each item
below maps to one specific complaint. Layout/structure only: `db.py`, CRUD, due-date, and
notification logic untouched; the category color-tinting on Upcoming cards is unchanged, only
what's layered inside each card moved. Full suite re-run clean: 72 passed, same 6 pre-existing
failures as baseline (unchanged from the previous pass, confirmed unrelated), no new
regressions. Spot-verified via `streamlit.testing.v1.AppTest` against an isolated schema (not
`public`) that: no exception on load, the old `"View profile"`/`"goto_"`/`"mute_"` buttons are
gone, the new `mutebell_...`/`pf_photolink_btn_...` buttons exist instead, the full quirky
sentences are still present verbatim in the rendered markdown, and `"📋 Upcoming"` now renders
before `"🎉 New Pack Members"`.

### Fix 1: nav tabs wrapping on mobile → icon-only pill below the breakpoint

- Each nav segment (Home / All the Pups) now renders as *two* buttons — `nav_home_full`/
  `nav_profiles_full` (icon + text) and `nav_home_icon`/`nav_profiles_icon` (icon only) — with
  CSS showing only one at a time via the existing 640px breakpoint, since a Streamlit button's
  label can't be swapped by media query. Desktop shows icon+text as before; mobile now shows
  just 🏠/🐾 instead of letting the text wrap to two lines.
- **Caught and fixed in the same pass, not left as a followup:** the pill's two segments were
  laid out with `st.columns(2)`, and this codebase's own mobile CSS deliberately makes
  `st.columns` stack to one-per-row below 640px (used everywhere else on purpose) — which would
  have broken the segmented pill into two stacked rows on exactly the phone widths this fix
  targets, if left alone. Overridden with a scoped `flex-direction: row !important` on just the
  `nav_pills` container's inner columns, so the pill stays side-by-side at every width.
- **Location:** `app.py` (renders both button variants), `styles.py` (`.st-key-nav_pills`
  rules, the `_full`/`_icon` display swap in the mobile media query).

### Fix 2: section order — Upcoming before New Pack Members

- Straightforward reorder in `views/home.py`: time-sensitive reminders now render first,
  social/informational "New Pack Members" second. Both sections' subheaders are now shown
  unconditionally whenever they have content (previously "📋 Upcoming" only got a heading if
  "🎉 New Pack Members" was also present, a quirk of always being the second section — no longer
  applicable now that either can be first).

### Fix 3 & 4: removed "View profile" buttons; photo + name are now the only nav path

- Both card types lost their `"View profile"` button entirely, per instruction — not shrunk,
  removed. `ui_helpers.render_photo_name_link()` is the replacement: it lays a transparent,
  same-sized button on top of the photo+name row (Streamlit buttons can't wrap an image
  directly, so this is a same-technique-as-everywhere-else invisible-overlay click target, not
  a real HTML link), making the photo and the name one tappable unit that goes straight to the
  profile. Used identically on both New Pack Members and Upcoming cards, satisfying "anywhere a
  pet is shown, it should be tappable" consistently across both.
- New Pack Members cards also got the tighter spacing/line-height treatment (unchanged from
  the previous pass) — combined with the removed button, the card is now just photo+sentence,
  no separate action row at all.
- Upcoming cards additionally lost the per-item icon circle (the redundant "suitcase" etc. next
  to the pet's own photo) — the category still reads through the card's tint color alone, per
  instruction. `render_urgency_badge()` (badge only, no icon) replaces `render_card_header()`
  here; `render_card_header()` (icon + badge together) is still used unchanged on the profile
  page's due-date rows, which have no photo of their own to make an icon redundant.

### Fix 4 (continued): "Mute email for this" → small bell-icon toggle

- Replaced the full outlined button with a single small icon button in the card's top-left
  corner (top-right is the urgency badge): 🔔 when mutable-and-not-yet-muted (tap to mute, same
  `mark_events_notified()` call as before), a static dimmed 🔕 with a tooltip when already
  muted (matches the old behavior of no "unmute" action existing — muting is one-way until the
  due date changes). Renders nothing in that corner for items with no milestone to mute at all
  (same condition as before, `current_milestone() is None`).

### Not visually confirmed: tap-target size and the mobile pill-vs-column-stacking override

- **Still no browser automation tool in this environment** — everything below was reasoned
  through from the CSS/DOM source, not seen on an actual phone:
  - The icon-only nav buttons (🏠/🐾) and the mute-bell (🔔/🔕) are deliberately small/quiet by
    design, but weren't checked against a real touchscreen for comfortable tap accuracy —
    worth a first-hand check specifically on the smallest phone you test with.
  - The `flex-direction: row !important` override that keeps the nav pill's two segments side
    by side despite this app's own mobile column-stacking rule is the fix with the most room to
    silently fail (a CSS specificity fight this environment can't screenshot to confirm the
    winner) — **please check this one first**, since if it loses, the nav regresses to exactly
    the two-line wrapping problem this pass was meant to fix, just via stacked columns instead
    of wrapped text.
  - The invisible-overlay click target (`pf_photolink_btn_...`) covering the photo+name row —
    confirmed present and wired to the right profile via `AppTest`, but its actual hit-box
    alignment over the visible photo/text (not spilling onto the badge above or, on Upcoming
    cards, being too short to cover a two-line-wrapped name comfortably) wasn't seen rendered.
- **Location:** `styles.py` — `.st-key-nav_pills [data-testid="stHorizontalBlock"]`,
  `.st-key-pf_photolink_wrap_`/`btn_` rules, `.st-key-mutebell_` rules.

## Glassmorphism Redesign Pass — 2026-07-19

This was specified as the single source of truth, superseding the two earlier styling passes
above — exact values (gradient background, glass-card CSS block, palette hex codes, avatar/
badge/mute-button px values) were used verbatim wherever given. `db.py`, CRUD, auth,
notifications, and due-date logic are untouched. Full suite re-run clean: 72 passed, same 6
pre-existing failures as baseline (one test, `test_profile_detail_with_selection_shows_profile`,
was updated — not just left passing — because it asserted against `st.header()`, which this
redesign deliberately replaces with styled markdown; see the accessibility note below). Spot-
verified via `AppTest` against an isolated schema that both pages load with no exception, the
exact badge/dot HTML matches the spec's values byte-for-byte, and the category-dot colors
resolve correctly per type (vaccination → `#ff9f4a`, boarding → `#1fb8b0`, confirmed in the
rendered markdown).

**Two things below are flagged as genuine conflicts needing your decision, not silently
resolved — see "Where 'name exactly once' couldn't be fully honored" and "Profile header avatar
size" in particular.**

### Where "name exactly once" couldn't be fully honored

- **Fixed:** the old bug the brief called out by name — the UI layer used to prepend
  `f"**{profile_name}** · {text}"`, which combined with `voice.py`'s own `{name}`-embedding
  templates to produce exactly the doubled pattern in the brief's example ("Bobby Dugar · Bobby
  Dugar checks into..."). That prefix is gone; the name-row header is now the only place the UI
  layer itself inserts the name.
- **Not fixed, and can't be within the given constraints:** `voice.py`'s templates were written
  to be complete, natural sentences that name the dog themselves (e.g. "Circle it in the
  calendar — Bobby is due for Rabies in 2 days...", "🐾 Bobby just joined the pack..."). Given
  "don't shorten or alter any existing quirky copy," those templates were left untouched, which
  means the name still appears a second time *within* the message, inline in the sentence — just
  not as a flat, robotic repeat anymore. This is a genuine conflict between two instructions in
  the brief (name exactly once, vs. don't touch the copy), not an oversight: satisfying "exactly
  once, period" would require editing `voice.py`'s templates to drop the leading name (e.g. to
  something like the brief's own illustrative "Checks into Dog House Red Hills in 7 days..."),
  which directly contradicts "don't alter the copy." Tell me which one wins if you want this
  fully closed — I didn't want to guess and rewrite the voice on your behalf.
- **Location:** `voice.py` (untouched), `ui_helpers.render_avatar_card_link`/`render_name_row`
  (the fixed half).

### Profile header avatar size — kept larger than the dashboard cards' 40px

- The brief's exact 40px/rgba(255,255,255,0.75) avatar spec is written as part of the
  dashboard card's structure (avatar + category dot + urgency badge). A profile's own page has
  no category or urgency concept for *itself* (categories classify events, not dogs), so
  literally reproducing "the same avatar/name-row pattern" there means the name-row (bold name,
  no dot, no badge) but not necessarily the same tiny 40px size — a profile page's whole reason
  for existing is to look at that one dog, and shrinking its photo to feed-thumbnail size felt
  like an unintended side effect of a spec written for a different context, not a deliberate
  ask. Used 88px instead, same circular/glass treatment, same `render_name_row` component as
  everywhere else. If you did mean literally 40px here too, that's a one-line change
  (`show_photo(..., width=88, ...)` → `width=40`) — flagging rather than guessing.
- **Location:** `views/profile_detail.py`, the `card_profile_header` container.

### backdrop-filter fallback: implemented via `@supports`, can't confirm which branch renders

- Rather than guessing whether the deployment browser supports `backdrop-filter` (it's broadly
  supported in evergreen Chrome/Edge/Firefox/Safari as of 2026, but this environment has no
  browser to check against), used an `@supports not (...)` block so the browser itself decides:
  full `blur(14px)` glass where supported, the exact `rgba(255,255,255,0.85)` solid fallback
  specified in the brief where it isn't. Genuinely don't know which one is rendering for you —
  if the cards look flat/opaque instead of frosted, that's the fallback firing, not a bug.
- **Location:** `styles.py`, the `@supports not ((backdrop-filter...` block right after the
  main glass-card rule.

### Card height: re-verified no fixed height anywhere in the glass-card rule

- The brief named a specific prior bug (fixed-height cards clipping longer messages) and asked
  for an explicit re-check. Confirmed by reading the CSS itself: the glass-card rule sets
  `height: auto !important; min-height: 0 !important; overflow: visible;` and no rule anywhere
  in the stylesheet sets a `max-height` or `overflow: hidden` on a card. Also confirmed
  behaviorally via `AppTest` with a full-length quirky sentence rendered inside a card — the
  complete text came back in the markdown output, nothing truncated. What wasn't (couldn't be)
  confirmed is the *pixel-level rendered* result — whether the card's visible background box
  actually grows to match, since that's a real-browser layout question this environment can't
  screenshot.

### Avatar/icon containment: added `overflow: hidden` on the clickable avatar+name wrapper

- The brief asked to "fix the avatar/icon alignment issue from before" without a specific
  repro. The most plausible candidate given this codebase's own mechanics: the invisible
  overlay button (`pf_photolink_btn_`) that makes the avatar+name clickable is
  `position: absolute; inset: 0`, and if its parent wrapper's box were ever taller than the
  avatar+name content (e.g. from wrapping text), the overlay's bounding box could extend past
  what's visibly there. Added `overflow: hidden` and a matching `border-radius` to the wrapper
  as a defensive fix so neither the avatar nor the overlay can ever visually spill past the
  card's own padding, regardless of content length. Not confirmed against the specific issue
  you saw, since it wasn't described further — if this doesn't address what you meant, tell me
  what it looked like and I'll target it directly.
- **Location:** `styles.py`, `.st-key-pf_photolink_wrap_`.

### Scoping: which existing elements did and didn't get the glass treatment

- **Got it:** Upcoming cards, New Pack Members cards, "All the Pups" profile-list cards,
  profile-page due-date record rows (vaccinations/medications/baths/food-refills/boarding,
  including the ones that previously had no container key at all — every record row is now
  keyed so none of them fall back to Streamlit's plain default box), and the Identity/
  Registration/Spay-Neuter field groups.
- **Deliberately left alone:** `st.form` (add/edit dialogs), `st.dialog` modals, and
  `st.expander` — none of these were named in the brief's card enumeration, and a translucent
  frosted *modal* overlaying frosted *cards* underneath seemed likely to hurt legibility rather
  than help it, so dialogs stay a plain opaque solid. Say the word if you want these converted
  too.
- **Category dot color mapping** (unchanged from the previous pass, still applies): health →
  `#ff9f4a` (warm orange), routine/registration → `#ffc93c` (amber), care → `#1fb8b0` (bright
  teal), social → `#0e7c78` (deep teal) — the amber/orange-vs-teal split follows the brief's own
  "health & logistics vs. care & social" example exactly.
- **Nav + profile-page tabs both use the same active-accent** (`#1fb8b0`, the brief's own
  example color) for "pick one consistently" — extended from just the top nav to the profile
  page's Health/Personality/Social/Care tabs too, since both are segmented controls and the
  brief's instruction read as one accent for that whole pattern, not just the top bar
  specifically. Flagging in case you meant only the top nav.

### Accessibility: profile name is no longer a semantic heading

- The profile page's name used to be a real `st.header()` (renders as an `<h2>`). Reusing
  `render_name_row()` there for visual consistency with the dashboard's card pattern means it's
  now styled `<div>`/`<span>` markup instead — visually a heading, but no longer one to a screen
  reader or in the page's outline. Not something the brief asked for explicitly; a side effect
  of literally reusing the shared component. Worth knowing about if accessibility matters here;
  a small fix (wrapping the name in a visually-hidden real heading alongside the styled one)
  is possible if you want it.

### Dark mode: intentionally not themed this pass

- Already flagged in the response, repeating here for the record: every value in this
  redesign is a fixed light color with no dark-mode equivalent given, and the previous design's
  dark-mode logic (flipping text to a *light* color for contrast against a *dark* background)
  would put light text on this redesign's permanently-light gradient background if left in —
  a real, not hypothetical, contrast bug. Removed rather than left broken. The app now looks the
  same regardless of the visitor's OS color-scheme setting. Tell me if you want a dark variant
  designed for this new palette.

## Glassmorphism Corrective Pass — 2026-07-19

Six specific, described bugs from an actual rendered review of the previous pass — not another
general polish. `db.py`, CRUD, auth, notifications, and due-date logic untouched. Full suite
re-run clean: 72 passed, same 6 pre-existing failures as baseline, no new regressions. Verified
via `AppTest` against an isolated schema that: all three boarding-stay message templates
(including the two named as cut off — "...They'll have a blast and pretend not to miss us." and
"...Bags are basically already packed.") now render complete and unclipped in the markdown
output; the login page's `st.tabs()` and `st.form()` load with no exception; card/button keys
match the restructured CSS selectors below.

### 1. Background: fixed a real CSS bug, not an override

- Confirmed root cause, not a guess: the previous pass applied the identical 4-layer gradient
  to *three* nested elements at once (`stAppViewContainer`, `stApp`, `stMain`). Since these are
  nested inside each other with slightly different boxes, each rendered its own independent
  copy of the gradient sized to its own box, and the innermost one's edges showed as a visible
  seam over the outer ones — that reads as exactly the "hard banded diagonal" you saw, not a
  smooth single gradient. Fixed by painting the background on `stAppViewContainer` only, with
  every descendant that could otherwise paint over it (`stApp`, `stMain`,
  `stMainBlockContainer`, `stHeader`) forced to `background: transparent !important`.
- **Also found and fixed, independent of the above:** `radial-gradient(circle at X% Y%, ...)`
  with no explicit size defaults to CSS's `farthest-corner` keyword — meaning each glow's "48%
  transparent" stop was landing 48% of the way to the *farthest corner of the whole screen*,
  not a contained local glow. On a typical laptop width that's several hundred pixels, so the
  "soft spot" was covering most of the visible area — the other real contributor to "most of
  the screen colored" instead of "near-white with three soft spots." Added an explicit `550px`
  circle size to each gradient so the 48%/45% stops resolve to a sane, contained glow radius
  instead. Position, color, and stop-percentage values are unchanged from the exact spec; only
  this implicit sizing (which CSS requires *some* value for) is now explicit.
- **Not confirmed:** the actual rendered pixels, since there's still no browser tool in this
  environment — but both causes above are concrete, verifiable CSS mechanics (nested-element
  duplication and `radial-gradient`'s own default sizing keyword), not speculation, and no
  `.streamlit/config.toml` theme override exists in this repo to be a competing cause.
- **Location:** `styles.py`, the `[data-testid="stAppViewContainer"]` rule.

### 2 & 5. Cards not glass; login form unstyled — same root cause

- **Confirmed, not a backdrop-filter support failure:** `st.form()` (which wraps the login and
  signup forms) was never added to the glass-card CSS selector list in the previous pass —
  forms were explicitly out of scope then. It was rendering with its old solid warm-peach
  background (`var(--pf-card-bg-alt)`, close to the "solid salmon" described) because that's a
  *different, older* rule that was simply never replaced, not `backdrop-filter` failing
  silently. Added `[data-testid="stForm"]` to the shared glass-card selector (background,
  blur, border, radius, shadow, and the `@supports` fallback all apply to it now identically to
  every other card), and removed the old solid-color form rule so there's no longer a
  conflicting declaration.
- **Whether `backdrop-filter` itself is rendering as true blur vs. its solid fallback still
  can't be confirmed without a browser.** What I can say concretely: the CSS is correctly
  structured for it to work (both `backdrop-filter` and `-webkit-backdrop-filter` present, the
  `@supports not (...)` fallback block is syntactically valid and will swap in
  `rgba(255,255,255,0.85)` automatically if the browser genuinely doesn't support it), and the
  background-layering fix in item 1 removes a scenario that would otherwise defeat the *visual
  effect* of a working blur even if the CSS property itself were applying correctly — if an
  opaque element sat directly behind a card, `backdrop-filter` would have nothing colorful to
  blur, and would look flat regardless of whether the property itself "worked." That specific
  scenario is now closed. If cards still look flat after this, that's genuine evidence
  `backdrop-filter` isn't supported in whatever's rendering this for you, and the fallback
  should be visibly active instead (`rgba(255,255,255,0.85)`, still frosted-*looking* just not
  blurred) — please tell me which one you're seeing.
- **The Login/Sign up tab styling itself was not changed** — `st.tabs()`'s active tab already
  uses the exact palette teal (`#1fb8b0`) from the previous pass, unrelated to the form
  background bug. If it still looks wrong once the form background fix above renders, it's a
  new, different symptom — tell me specifically what you're seeing (e.g. underline vs. fill,
  which color) and I'll target it directly rather than guessing.
- **Location:** `styles.py`, the glass-card shared selector block (now includes
  `[data-testid="stForm"]`).

### 3. Text truncation — found and removed the actual cause

- **Root cause, confirmed:** the *previous* corrective pass (mobile-viewport fixes) added
  `overflow: hidden` to `.st-key-pf_photolink_wrap_` — the container that holds both the
  avatar+name-row *and* the full message text below it — as a defensive, never-actually-
  confirmed guess at fixing a described-but-unreproduced "avatar/icon alignment" issue. Since
  that wrapper holds the message text too, `overflow: hidden` clipped it whenever the full
  quirky sentence needed more vertical space than was visible. Removed entirely — the avatar
  can't spill past the card regardless, since it has a fixed pixel size and lives in its own
  flex column, so nothing else needed to take overflow:hidden's place.
- **Also added, defensively:** explicit `white-space: normal`, `overflow: visible`,
  `text-overflow: clip`, and `max-height: none` (all `!important`) directly on the message
  paragraph rule, so a future change to an ancestor's overflow/white-space can't silently
  reintroduce clipping without also having to override these directly.
- **Verified, not just reasoned about:** re-ran the exact boarding-stay templates you quoted as
  cut off through `AppTest` — both now come back complete in the rendered markdown ("...They'll
  have a blast and pretend not to miss us." / "...Bags are basically already packed."), full
  stop included, nothing missing.
- **Location:** `styles.py`, the `.st-key-pf_photolink_wrap_` rule (the fix) and the
  `card_new_`/`card_evt_` message-paragraph rule (the added hardening).

### 4. Mute icon: confirmed correct glyph in code, likely a font-fallback rendering issue

- Checked the actual Unicode codepoint used in `views/home.py` via Python's `unicodedata`
  module: `U+1F515`, officially named "BELL WITH CANCELLATION STROKE" — the correct, standard
  mute-bell glyph (🔕), not a copy-paste mistake, and not a "no entry"/prohibited codepoint.
- Most likely explanation for it *looking* like a blocked/prohibited symbol: browsers don't
  always apply the same color-emoji font fallback inside a `<button>` element that they do for
  ordinary body text (a known class of rendering inconsistency, particularly on Windows), and
  at the glyph's previous 12px size, a monochrome fallback rendering of a bell-with-slash can
  genuinely be hard to distinguish from a generic "prohibited" circle. Fixed by explicitly
  hinting a color-emoji font stack (`"Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"`)
  on the button and sizing the glyph up slightly (12px → 14px).
- **Not confirmed:** whether this specific fix resolves the rendering on your system, since I
  can't see it rendered. If it still looks wrong, that's evidence the font-family hint isn't
  taking effect in your browser, and the next step would be a real icon (SVG or an icon font)
  instead of relying on emoji rendering at all — tell me if you'd rather go straight there.
- **Location:** `styles.py`, `.st-key-mutebell_` button rule.

### 6. Mute icon disappearing on mobile — confirmed cause: flex-shrink squeeze, not a hide rule

- Checked explicitly for any `display: none` rule that could match the mute-bell at narrow
  widths — none exists. The actual cause: the mute-bell lived in a narrow `st.columns([6, 1])`
  slot next to the avatar+name+message column. Flex children default to `min-width: auto`,
  which lets a wide/long sibling (the full message text, especially before item 3's fix) refuse
  to shrink below its own content width — on a narrow card, that pushed the 1-part mute-bell
  column down to zero available space, effectively squeezing it off-screen (present in the DOM,
  not visibly there or tappable), exactly as you guessed.
- Fixed with two rules: `min-width: 0` on every nested column inside these cards (lets the
  content column actually shrink/wrap instead of fighting for space), plus a guaranteed
  `min-width: 32px; flex-shrink: 0` floor specifically on the mute-bell's own column — scoped
  precisely via a new `cardrow_` wrapper key + direct-child CSS combinators so it can't
  accidentally also apply to the *nested* avatar/text column split one level deeper (which
  needs to stay free to shrink, not get a hard floor).
- **Location:** `styles.py`, the `min-width: 0` and `st-key-cardrow_` rules just after the
  `pf_photolink_` block; `views/home.py`, the new `cardrow_` container wrapping `content_cols`.

### Still can't confirm without a browser

Every fix above is grounded in a concrete, identifiable CSS/DOM mechanism (verified via reading
the actual generated CSS/HTML and, where possible, `AppTest`'s rendered output) rather than a
repeat of the same values with a hope it renders differently. What genuinely can't be confirmed
from this environment: the actual pixel-level result on a real phone and a real desktop
browser, and specifically whether `backdrop-filter` is rendering as true blur or its solid
fallback (see item 2/5). Please check both viewport widths and tell me what you see — if
anything on this list still doesn't match, it'll be faster to fix with a specific description
than another full pass.

## Second Corrective Pass — 2026-07-19

Translucency/glow/truncation confirmed fixed and untouched this pass, per instruction. Three
more specific items. `db.py`, CRUD, auth, notifications, and due-date logic untouched (item 1
required editing `voice.py`'s copy itself, which is content, not logic — no template's
`{detail}`/`{when}`/`{turning}` interpolation or event-type routing changed, only whether
`{name}` appears in the sentence). Full suite re-run clean: 72 passed, same 6 pre-existing
failures as baseline, no new regressions (`test_voice.py`'s assertions were rewritten to match
the new copy, not loosened to hide anything).

### 1. Name appearing twice — found and fixed at the source, not the display layer

- **Where it actually was:** `voice.py`'s templates themselves (`VACCINE_TEMPLATES_DUE`,
  `BOARDING_TEMPLATES`, `NEW_PROFILE_TEMPLATES_COMMUNITY_DOG`, etc.) — every one of them said
  the dog's name as part of the sentence (`"{name}'s little vacation at {detail} starts
  {when}..."`), which combined with the dashboard card's separate bold name-row header to show
  the name twice. The previous pass only removed a *redundant UI-layer prefix* it had added on
  top of these templates — it never touched the templates' own embedded `{name}`, which is why
  this wasn't actually fixed despite being reported fixed. Rewrote all 26 template strings
  across `VACCINE_TEMPLATES_DUE/OVERDUE`, `MED_TEMPLATES`, `REG_TEMPLATES`,
  `OWN_BIRTHDAY_TEMPLATES`, `FRIEND_BIRTHDAY_TEMPLATES`, `BATH_TEMPLATES`,
  `FOOD_REFILL_TEMPLATES`, `BOARDING_TEMPLATES`, and both `NEW_PROFILE_TEMPLATES_*` lists to
  drop the leading/embedded `{name}` and read as a standalone continuation instead (verified via
  `AppTest` that your own two examples now render byte-for-byte as you described them: *"A
  little vacation at Dog House Red Hills starts in 3 days. Bags are basically already packed."*
  and *"🐾 Has entered the chat. New community pup on the books."*). `{detail}` (a vaccine name,
  a friend's name, a food brand, a facility) was left alone in every template — it's a
  different thing than the card's own subject, not redundant with the header.
- **One consumer needed a compensating fix:** `notifications.py`'s email digest reuses these
  exact same templates (`voice.render_event_card`), but unlike the dashboard, an email digest
  lists several dogs' items in a row with **no per-item header** of its own — stripping the
  name from the shared template would have made a multi-dog digest email genuinely ambiguous
  about which line belonged to which dog. Fixed by having `_build_digest()` explicitly
  re-prepend `card["profile_name"]` (already returned alongside `card["text"]`) when building
  each digest line/HTML block, so the *email* still says the name once per item, while the
  *template* stays name-free for the dashboard's benefit. This is a genuinely different
  presentation context, not a workaround — the dashboard has a name-row, the email doesn't, so
  each needed to end up saying the name exactly once via a different mechanism.
- **Location:** `voice.py` (all template lists), `notifications.py`'s `_build_digest()`,
  `tests/test_voice.py` (assertions rewritten to check `card["profile_name"]` instead of
  `"Rex" in card["text"]`, and to explicitly assert the name is *not* in the text — a regression
  guard against this exact bug recurring).

### 2. Mute icon ambiguity — switched glyphs, not just re-styled the same one

- The previous fix kept the slash-bell (🔕) for both states and only adjusted its font/size,
  which didn't address the actual complaint (a slashed-circle shape reading as "blocked").
  Switched to your suggested fallback approach: a plain, unambiguous bell (🔔, U+1F514) for
  *both* states — normal opacity when it's an active, clickable "tap to mute" button, and the
  same glyph dimmed + grayscaled (`opacity:0.35; filter:grayscale(60%)`) for "already muted,"
  rather than a different, still-emoji-dependent glyph for the muted state. A plain bell shape
  doesn't carry the "is this a prohibition sign" ambiguity a slashed circle does even if a
  browser falls back to a monochrome rendering. No icon font was reintroduced (Font Awesome was
  deliberately retired earlier this redesign) — kept it to the one glyph, appearance-only state
  change, per your explicit fallback suggestion.
- **Location:** `views/home.py` (both the live button and the dimmed muted-state markup),
  `styles.py`'s `.st-key-mutebell_` comment.

### 3. Chain-link glyph next to section headers — Streamlit's own built-in anchor-link icon

- **Confirmed, not guessed:** Streamlit automatically renders a small hover-triggered
  "copy link to this heading" icon (a literal link/chain glyph, used for deep-linking to a page
  section) next to every `st.title()`/`st.header()`/`st.subheader()` unless explicitly disabled.
  This is a stock Streamlit feature, not a broken icon-font reference — this app has no Font
  Awesome or other icon font loaded anymore (retired earlier this redesign), and there is no
  other icon-glyph code anywhere near the "New Pack Members" subheader, so a leftover unresolved
  icon-font reference wasn't the cause. Disabled it via Streamlit's own `anchor=False` parameter
  (confirmed via source: `Anchor: TypeAlias = str | Literal[False] | None`; "If False, the
  anchor is not shown in the UI") on every `st.title()`/`st.header()`/`st.subheader()` call in
  the app, not just "New Pack Members" specifically, since it's the same stock element
  everywhere headings appear and there's no reason to keep an unused deep-link affordance on any
  of them in a single-page-per-view dashboard app like this one.
- **Verified at the protocol level, not just by reading the source:** ran the actual page
  through `AppTest` and inspected the underlying protobuf for both `st.title("🐾 Pawfolio")` and
  `st.subheader("🎉 New Pack Members")` — both report `hide_anchor: True`, confirming Streamlit
  itself will suppress the icon, as close to confirmed as this environment allows without an
  actual browser to look at.
- **Location:** every `st.title`/`st.header`/`st.subheader` call — `views/home.py`,
  `views/profile_detail.py`, `views/all_profiles.py`, `views/add_profile.py`, `login_ui.py`.

### Viewport check for this pass specifically

None of these three fixes are viewport/breakpoint-dependent (no CSS media query was touched;
`anchor=False` and the template rewrites are pure content/protocol changes, and the mute-bell
glyph swap reuses the exact sizing/positioning CSS from the previous pass, which already
included the mobile-specific `min-width`/`flex-shrink` fix for that button not disappearing on
narrow screens). Re-ran the full suite and the AppTest smoke checks with no viewport-specific
divergence possible at the code level — but as with every pass so far, the actual rendered
pixels on a real phone vs. desktop browser still can't be confirmed from this environment.
Please check both after this one.

## Third Corrective Pass — 2026-07-19

Translucency, background glow, text truncation, name-duplication, mute icon, and the stray
anchor icon are all confirmed working and untouched this pass. `db.py`, CRUD, auth,
notifications, and due-date logic untouched. Full suite: 72 passed, same 6 pre-existing
failures as baseline. **One thing worth flagging up front:** a full-suite run right after these
changes showed 5 *additional* failures beyond the usual 6, all `RuntimeError: AppTest script
run timed out after 3(s)`. Chased this down before trusting any other result — re-ran the exact
same failing test against a `git stash`-ed (fully unmodified) checkout and got the *same*
timeout 3 times out of 4 runs. This is this long session's accumulated background load (a dev
server plus many hours of manual test scripts against the same live database) straining
connection acquisition, not anything in this pass's code — confirmed environmental, not a
regression, and the failure disappeared once the full suite ran again a moment later (also
cleaned up one leftover `test_*` schema from an earlier session while investigating, unrelated
to this pass).

### 1. Nav pill grouping + excess whitespace on mobile

- **Root cause, not a guess:** the pill's two segments (Home/Pups) were each rendered inside
  their *own* nested `st.columns(2)` split inside the `nav_pills` container. That nesting meant
  there were *two* separate flex-row overrides needed (one for `nav_pills`'s own row, one for
  the nested columns-within-a-column), and on mobile the second one didn't fully apply — one
  segment ended up rendering with none of the custom pill styling, falling back to Streamlit's
  own default button box, which is taller/wider/differently-shaped than the tightly-fitted
  custom pill. That's what looked like a second, unstyled, oversized capsule floating outside
  the real one. Fixed by removing the nested columns entirely — all 4 buttons (home/profiles ×
  full/icon) are now direct siblings inside `nav_pills`, so there's only one flex row to
  control, not two.
- **Also found and fixed, same investigation:** the *outer* row (`nav_cols` in `app.py` — the
  pill column, an empty spacer column, and the logout column) had no row-not-stacked override at
  all, so on mobile it broke into 3 separate full-width stacked bars — an entire extra blank bar
  for the empty spacer column alone is real, visible dead space, independent of anything inside
  `nav_pills`. Given the same fix as `nav_pills`'s own row.
- **Vertical spacing below the nav bar:** tightened via a small negative margin on the
  `top_nav` container plus a reduced margin on the divider immediately following it (targeted
  specifically via an adjacent-sibling selector, so this doesn't affect other dividers
  elsewhere on the page).
- **Location:** `app.py` (nav button structure, no more nested `pill_cols`), `styles.py`
  (`.st-key-nav_pills` and `.st-key-top_nav` rules).

### 2. Unequal card heights within a row — flexbox stretch, no fixed height

- Streamlit's own column row is already a flex row, and `align-items: stretch` (flexbox's
  default) already stretches each column to match the row's tallest member — what was actually
  missing was threading that stretch down from the (invisible) column wrapper to the visible
  card div inside it, which otherwise just sat at its own shorter natural height with dead
  space below it in the now-taller column. Added `flex: 1` on the card itself plus
  `display:flex;flex-direction:column` on the intermediate wrappers so the stretch actually
  reaches the visible box. `height: auto` (already set on every card, needed for the
  truncation fix from the previous pass) still governs the card's *minimum* size from its own
  content — nothing in this fix can make a card shorter than its content, only taller to match
  a taller sibling, and a very long message still grows the whole row's height exactly as
  before.
- Scoped via `:has()` to only the row(s) actually containing an Upcoming card
  (`card_evt_`), not every `st.columns()` in the app — the top nav, "All the Pups" list, etc.
  don't get this and don't need it. `:has()` needs a reasonably modern browser (broadly
  supported since ~2023) — if unsupported, this specific enhancement just doesn't apply and
  cards fall back to today's independent-height look, not something visibly broken.
- **Scoping note, not extended without being asked:** the "All the Pups" profile-list grid
  (`profile_card_`, `views/all_profiles.py`) uses the same `st.columns()` pattern and could have
  the same latent unequal-height susceptibility, but wasn't reported and wasn't touched — its
  content (photo/name/type/age) is far less variable in length than a full quirky sentence, so
  it's lower-risk, but flagging in case it's noticed later.
- **Location:** `styles.py`, the new "Equal-height Upcoming cards" block.

### 3. New Pack Members emoji placement

- Moved the leading emoji to the end of the sentence in both `NEW_PROFILE_TEMPLATES_MY_DOG`
  and `NEW_PROFILE_TEMPLATES_COMMUNITY_DOG` (`voice.py`) — verified via `AppTest` that "Has
  entered the chat. New community pup on the books. 🐾" now renders exactly as you specified.
  Templates with no leading emoji to begin with were left untouched. Confirmed no colored dot
  was added to these cards (`render_avatar_card_link` is still called with no `category` for
  New Pack Members, same as before — `category_dot_html` returns an empty string when there's
  no category, so nothing renders there).
- **Deliberately left alone:** `BOARDING_TEMPLATES`' one template with a leading emoji (📦) —
  this item was scoped explicitly to "New Pack Members" cards, and Upcoming cards have a
  different layout (avatar + dot + name + badge above the message, not immediately adjacent to
  the name-row the same way), so the same clutter complaint doesn't obviously apply there. Left
  as-is rather than assumed into scope.
- **Location:** `voice.py`, `NEW_PROFILE_TEMPLATES_MY_DOG`/`NEW_PROFILE_TEMPLATES_COMMUNITY_DOG`.

### Still can't confirm without a browser

As with every pass, the exact rendered result (particularly whether the equal-height stretch in
item 2 produces any visually awkward oversized gap under a very short card next to a very long
one, which the instructions specifically asked about) can't be seen from this environment.
Please check that specific case, plus both mobile and desktop widths on all three items, and
report back anything that still looks off.

## Header/Navigation Restructure — 2026-07-19

Structural change to the top bar and where account-level actions live, not a visual-polish
pass — previously confirmed fixes (translucency, background glow, card sizing/height, name-
duplication, mute icon, emoji placement) untouched. No data-scoping change anywhere: "My Pups"
runs the exact same `owner_id`-scoped query "All the Pups" always did, just relabeled. Full
suite: 72 passed, same 6 pre-existing baseline failures, 2 new tests added specifically for
this change (nav no longer has a persistent logout/add-profile button; the account menu shows
correct profile counts).

### What changed

- **Top bar now holds exactly three things**, left to right: a compact brand mark (🐾 Pawfolio,
  icon-only below the mobile breakpoint), the Home/My Pups pill nav (unchanged mechanism from
  the previous pass, just relabeled and given a third neighbor), and a single hamburger (☰)
  icon opening an account menu.
- **Account menu** (`st.popover`, key `account_menu`): shows `"{N} pups · {M} community pups"`
  (live counts via `get_all_profiles(owner_id, profile_type=...)`, computed fresh each render —
  personal-app scale, no caching needed) and the Log out button, which moved here verbatim
  (same session-state cleanup, same toast-queue-leak fix from earlier in this project).
- **"All the Pups" → "My Pups"**: page title, `st.Page` title, and the on-page `st.title()` all
  renamed. Every underlying query is untouched — still `owner_id`-scoped, still both
  `my_dog`/`community_dog` profile types, exactly as private as before. A placeholder comment
  was added in both `app.py` (next to where the page list is built) and
  `views/all_profiles.py` explaining that the future public "All Pups" feature (Phase 5: every
  user's dog names + general location only, no private records, "friend" option) is a
  deliberately separate, not-yet-built page — this rename is not a step toward that, and
  nothing about this page's own scoping changed to prepare for it.
- **"New Profile" button**: removed from the top bar (it was never actually there — it lived on
  Home's own header, which is also now gone) and from Home entirely; it already existed on the
  My Pups page too, so no new button was added there, just confirmed it's the one surviving
  copy, positioned at the top of the list as before.
- **Home's old page-level hero** (large "🐾 Pawfolio" title + mascot illustration + its own copy
  of the New Profile button) was removed outright, not just moved — keeping it would have meant
  showing the Pawfolio brand twice on the same screen (once compact in the global top bar, once
  large immediately below it). The mascot illustration itself is untouched in its other use (the
  "nothing due" empty-state screen).

### Streamlit-specific notes on the hamburger/account-menu pattern

- **`st.popover()` is the closest native primitive, and it is a real limitation, not just a
  stylistic choice.** Streamlit has no slide-out drawer, no animated dropdown, no "menu"
  component — `st.popover()` is a click-to-toggle floating panel anchored to its trigger button.
  It's rendered as a portal (not literally positioned via ordinary document flow), so its exact
  placement relative to the trigger, and how it behaves at very narrow viewport widths, is
  governed by Streamlit's own internal implementation, not something this app's CSS can fully
  redirect. Confirmed it opens/closes correctly and its content (counts + logout) evaluates
  correctly via `AppTest`, but the actual on-screen positioning/animation at mobile width
  couldn't be seen from this environment — if it renders awkwardly close to a screen edge, or
  overlaps the nav pills, on a real narrow phone, that's a real Streamlit-popover behavior to
  work around (e.g., dropping to a `st.dialog` instead, which is a full-screen-friendlier
  component but a heavier interaction than a lightweight account menu probably wants) rather
  than a CSS fix.
- **A real, already-known quirk of `st.popover()` in this codebase, flagged for awareness even
  though it doesn't apply to *this* specific popover:** an existing comment elsewhere in
  `ui_helpers.py` notes that a popover can stay visibly open behind a `st.dialog` it triggers,
  since a dialog opening doesn't automatically close a popover underneath it. The account menu
  doesn't open any dialog from inside it (just a plain button triggering `sign_out()` +
  `st.rerun()`), so this specific failure mode doesn't apply here — noted for the next person
  who reaches for `st.popover()` in this app and might trigger a dialog from inside one.
- **Verified, not assumed:** popover content (the counts caption and the logout button) renders
  and is queryable via `AppTest` *without* needing to simulate a click to "open" it first — the
  panel's contents execute as part of the normal script run regardless of the frontend's
  visual open/closed state, which is why this pass could test the account menu's contents at
  all through `AppTest` (which has no way to simulate hovering/clicking to reveal a closed
  panel).

### Not confirmed without a browser

Same limitation as every pass so far — the compact brand mark's icon-only collapse on mobile,
the 3-way top bar's spacing at both viewport widths, and above all the popover's actual
on-screen appearance/positioning when tapped on a real phone, couldn't be seen from this
environment. Please check all of these, and specifically report back on the popover's mobile
behavior described above, since that's the one piece of this pass genuinely bounded by what
Streamlit itself can do rather than by CSS.
