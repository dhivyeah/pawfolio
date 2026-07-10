# Known Issues — for future review

Found during a schema/UI review on 2026-07-10. Bugs 1–3 (crash-level) were fixed immediately
— see git history / conversation for details. Everything below is a documented edge case, UX
gap, or structural risk that hasn't been addressed yet. Numbering matches the original review
so it can be cross-referenced.

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

5. **No validation that end dates come after start dates anywhere** — medication `end_date`
   before `start_date`, boarding `check_out` before `check_in`, vaccination `next_due_date`
   before `date_given`, spay/neuter date entered while status is "no" — all silently accepted.

6. **"Add vet visit" has no required-field check**, unlike every other "Add" form (which all
   require at least a name). A completely blank vet visit can be submitted, creating an empty
   history row with just today's date. (`views/profile_detail.py`, "Add vet visit" form.)

7. **Add Profile's "first vet visit" drops notes-only entries.** The gate is
   `if visit_date or visit_reason:` — it doesn't check `visit_notes`, so a user who only types
   notes (no date, no reason) silently loses that text on submit. (`views/add_profile.py`)

8. **Overdue items have no ceiling and no dismiss mechanism.** Vaccination/medication/bath/
   food_refill events with no lower bound on `days_until` stay on the dashboard forever once
   overdue — there's no way to acknowledge/snooze from the feed itself, only by editing the
   record on the profile page. Meanwhile `boarding_checkin` is the only event type that
   requires `days_until >= 0`, so a past check-in just silently vanishes from the feed —
   inconsistent treatment across event types that was never a deliberate, reviewed decision.
   (`db.py: get_upcoming_events`)

9. **No "checked out" / pickup reminder.** The dashboard surfaces upcoming boarding
   *check-ins* but never a "picking up Bobby today" reminder for `check_out_date`, and there's
   no "currently boarding" status indicator anywhere in the UI.

10. **"New Pack Members" has no expiry tracking beyond the raw 7-day window and no dismiss.**
    A profile stays in that section every time Home loads for a full week — fine once, could
    feel repetitive with daily use.

11. **Photo files are never cleaned up.** Deleting a profile (`db.delete_profile`) or
    replacing a photo via Edit Identity both leave the old file behind in `photos/` forever.

12. **iPhone default photo format isn't accepted.** The uploader only allows
    `png/jpg/jpeg/webp`; HEIC (default format for iOS camera photos) is rejected unless
    converted first — a plausible papercut given the persona.

13. **Editing an existing record doesn't re-validate required fields.** Only the "Add new"
    forms check for a non-empty name; the "Save" button on an existing vaccination/medication/
    surgery/etc. edit form will happily save an emptied-out name field.

## UX / consistency issues

14. **No confirmation on any sub-record delete.** Vaccination, medication, surgery, vet visit,
    bath, food refill, boarding stay, friend — every one has a single-click "Delete" with zero
    confirmation, unlike the profile-level delete which has an explicit checkbox gate.
    Especially painful for "history" tables (vet visits, boarding stays) meant to be permanent.

15. **"Unlink vet" button is styled as a red/terracotta danger button** (via the `delete_`
    key prefix in `ui_helpers.render_vet_picker`) even though unlinking is low-stakes and fully
    reversible (the vet stays in the shared directory) — visually overstates the action.

16. **No way to edit or delete a vet's own details once created.** `db.update_vet` /
    `db.delete_vet` exist but have no UI surface. A typo in a vet's phone/clinic can never be
    fixed; unlinking a vet from every profile leaves it in the directory forever with no
    cleanup path.

17. **Health tab is now quite long** — Vaccinations, Registration, Medications, Spay/Neuter,
    Surgeries, Vet Visit History, and Vets are all stacked in one tab. A lot of scrolling,
    especially on mobile, to reach the vet picker at the bottom.

18. **Duplicate list-item labels are visually indistinguishable.** E.g. two boarding stays with
    unset dates both render as `🧳 facility — ? to ?`; two vaccinations with the same name/due
    date look identical in the collapsed expander list.

19. **Untested tab-row overflow on narrow phones.** Nav icons, cards, and forms were verified
    not to overflow on mobile, but the 5-item tab row
    (`🪪 Identity | 🩺 Health | 🎾 Personality | 🐕 Social | 🧺 Care & Logistics`) was never
    specifically checked for wrapping/scrolling at ~390px width.

## Structural / maintenance risks (not bugs today, but fragile)

20. **The entire theme depends on undocumented Streamlit internals** (`data-testid`,
    `data-baseweb` attributes, structural child selectors like `> div > div` for date/select
    inputs). This already caused one real bug this session (a `help=` tooltip wrapper silently
    broke mobile button visibility). A future Streamlit version bump could silently revert
    buttons/cards/inputs to unstyled defaults with no error, just a visual regression.

21. **N+1 query pattern in the dashboard.** `get_upcoming_events` opens a fresh SQLite
    connection per profile per event type (7 sub-queries per profile), and `views/home.py`
    calls `get_profile()` again per event rather than once per profile. Fine at current scale.

22. **No index on any foreign key column** (`profile_id` everywhere, `vet_id` in
    `profile_vets` — aside from the new unique index added for the dedup fix). Every list
    query is a full table scan. Non-issue at small scale.

23. **Full photo files are base64-encoded from disk on every single Streamlit rerun**
    (`ui_helpers._image_data_uri`, no caching via `st.cache_data`). Any widget interaction
    anywhere on a page re-encodes every visible photo from scratch. Combined with Streamlit's
    200MB default upload cap and no client-side resizing/compression on upload, a handful of
    large photos could make the app feel sluggish.

24. **Contrast wasn't formally verified.** `--pf-text-muted` (`#8A7160` light / `#C9B8A8`
    dark) against the card backgrounds is a visual judgment call, not something run through an
    actual WCAG contrast checker.

## First-time-user walkthrough findings (2026-07-10)

Found by actually driving the running app end-to-end as a first-time user adding a dog and
setting up a vaccination schedule (via Playwright), not just reading code. Point 4 above (the
default-due-date trap) was confirmed live this way and is now fixed; the rest are still open.

25. **No feedback when a scheduled reminder is more than 30 days out.** Set a vaccination due
    date 36 days out, submitted, went back to Home expecting some confirmation — nothing.
    `get_upcoming_events`'s dashboard-only 30-day horizon means there's no persistent
    "your reminders are set" indicator anywhere; success reads identically to "did this even
    save?" A first-time user has no way to confirm the data stuck short of digging back into
    the profile's Health tab.

26. **No guidance on what to type into "Vaccine name."** Blank text field, no examples, no
    autocomplete for common vaccines (Rabies, DHPP, Bordetella, etc.). A first-time dog owner
    may not know standard vaccine names to enter.

27. **"Chennai Corporation Registration" appears with zero explanation.** No text anywhere
    saying what it is, whether it's required, or that it's safe to skip if you're not in
    Chennai. Reads as mandatory-adjacent to anyone unfamiliar with the program.
    (`views/add_profile.py`, `views/profile_detail.py` Health tab)

28. **🪪 (ID card) emoji on the "Identity" section header rendered as a broken/tofu box** in
    testing. It's a relatively recent Unicode emoji (2020) and Windows has historically lagged
    on emoji font updates — this may not be a headless-browser-only artifact and is worth
    checking on the actual target machine, since it's the very first section header a new user
    sees.

29. **Date input fields have a generic accessibility label.** Every `st.date_input`'s
    underlying `<input>` has `aria-label="Select a date."` regardless of which field it is
    (confirmed via DOM inspection) — a screen reader user tabbing through the Add Profile form
    would hear "Select a date" repeatedly with no indication of which date is which, relying
    entirely on correct label/input association rather than the accessible name itself.
