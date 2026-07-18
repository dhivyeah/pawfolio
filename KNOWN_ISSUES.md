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
- **21** — N+1 query pattern on the dashboard
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
- **42** — no in-app visibility into notification history, and no pause/mute control

### ⚪ No longer applicable
- **7** — moot. Described a gap in Add Profile's "first vet visit" block; that whole block was
  removed when Add Profile got trimmed to identity-only fields in the 2026-07-14 redesign, so
  there's nothing left to fix.

### 🔵 Needs a decision, not a fix
- **33** — friends are one-directional, siblings are symmetric. Not broken — just an
  inconsistency nobody deliberately chose, worth a call either way.
- **34** — a due item is only ever emailed once and never again unless its due date changes —
  even as it goes from "due in 7 days" to "3 days overdue." Deliberate anti-spam behavior or a
  missed-urgency gap, depending on what's actually wanted; wasn't a considered decision either
  way when it was built.

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

21. **[🟢 Low priority]** **N+1 query pattern in the dashboard.** `get_upcoming_events` opens
    a fresh SQLite connection per profile per event type (7 sub-queries per profile), and
    `views/home.py` calls `get_profile()` again per event rather than once per profile. Fine at
    current scale.

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

34. **[🔵 Needs a decision, not a fix]** **A due item is emailed at most once, ever, unless its
    due date changes.** Dedup is keyed on `(event_type, record_id, state_key)`, where
    `state_key` is the due date itself (or, for birthdays, the calendar date of that
    occurrence). That means an item mentioned once while "due in 7 days" — the outer edge of the
    notification horizon — goes completely silent from then on: it's never mentioned again as it
    becomes "due tomorrow," then "3 days overdue," then "3 weeks overdue," unless the underlying
    record is edited. This is *deliberate* anti-repeat-spam behavior, and it's what "notify once
    per item until it's marked done/updated" in the original spec literally asks for — but it
    also means the digest can't be relied on as an ongoing "this is still not done" nag the way
    the dashboard's persistent overdue tag can. Worth being explicit about which of those two
    things this is supposed to be, since right now it's the first one by construction, not by a
    considered choice between the two.

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

42. **[🟢 Low priority]** **No in-app visibility into the notification system at all** — no way
    to see when the last digest went out, what it said, or to pause/mute it temporarily, short of
    editing `.env` or querying the database directly. Consistent with "don't touch existing
    pages" for this pass, but worth knowing it's a closed box from the UI's perspective.

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
  scenario, not a theoretical edge case — and see the next item, the failure it causes isn't
  even a friendly one.
- **Location:** Infrastructure/hosting configuration, not application code — worth knowing
  about rather than something to fix in `db.py`. Supabase's dashboard has a setting to disable
  auto-pause on paid tiers; on free tier the only mitigation is some kind of periodic keep-alive
  ping, which has its own tradeoffs.

### Issue: No graceful handling if the hosted database is unreachable

- **Severity:** Medium
- **Steps to reproduce:** Point `DATABASE_URL` at an unreachable/paused/wrong database and
  load any page.
- **Expected vs. actual:** Expected a friendly, on-brand error message. Actual: `db.get_conn()`
  lets the raw `psycopg2.OperationalError` (or the connection pool's own exhaustion error)
  propagate straight up through whichever view happens to be running, and Streamlit renders it
  as a raw traceback in the app UI. Combined with the Supabase auto-pause item above, this is
  the actual failure mode a real visitor would see the first time they open Pawfolio after a
  week away: a stack trace, not "we're having trouble connecting, try again shortly."
- **Location:** `db.py`'s `get_conn()` / `_get_pool()` have no try/except around connection
  acquisition; no view file wraps its `db.*` calls either, so there's no single place currently
  positioned to catch this.

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
