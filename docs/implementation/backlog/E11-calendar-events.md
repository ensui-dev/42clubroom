# E11 — Calendar and events

| | |
|---|---|
| **Goal** | Clubs publish events in spaces; students see a club calendar and a campus calendar, RSVP, and optionally subscribe via iCal (D-17, D-25, R-06). |
| **Design** | [calendar.md](../../03-backend/calendar.md), [08-frontend §11.3](../../08-frontend.md) |
| **Primary track** | B (backend), C (frontend) |
| **Depends on** | E05 (space access), E07 (EVENT_MANAGE) |
| **Estimate** | 10 h (6.25 Must · 1.5 Should · 2.25 Could) |

## Stories

### E11-S01 · Create and manage club events

**Priority:** Must · **Milestone:** M3 · **Track:** B + C · **Estimate:** 3.25 h

> As a **club owner (or role with `EVENT_MANAGE`)**, I want to **create, edit and cancel events in one of the club's spaces** so that **members know what's coming** (subject: "event calendar").

**Acceptance criteria**
- Creating requires `EVENT_MANAGE`, an active club and a space of the same club (BR-21); `endsAt > startsAt` (else `400 INVALID_EVENT_TIMES`).
- The event inherits the space's read rule (R-06): members-only spaces give members-only events.
- Edit and cancel publish `EventUpdated` / `EventCancelled`; cancelled events stay visible, struck through.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E11-S01-T1 | `calendar` migration | DB | 0.25 | E01-S02 | [04-database §4.9](../../04-database.md) |
| E11-S01-T2 | `ClubEvent` domain + `EventService` (schedule/edit/cancel) + events | BE | 0.75 | T1, E07-S01, E05-S01 | [calendar.md §9](../../03-backend/calendar.md) |
| E11-S01-T3 | `ClubEventController` (`POST /api/clubs/{id}/events`, `GET/PATCH /api/events/{id}`, cancel) | BE | 0.5 | T2 | [calendar.md §7](../../03-backend/calendar.md) |
| E11-S01-T4 | `EventDialog` (space selector with audience hint, date/time pickers, optional cover upload) and `EventPage` | FE | 1.75 | T3 (contract) | [08-frontend §9.3](../../08-frontend.md) |

**MVP cut (saves ~0.5 h):** no cover image; edit = cancel + recreate.

**Branch:** `UNIX_CLUB/dev/feat(E11-S01)/club-events`

---

### E11-S02 · Club and campus calendars

**Priority:** Must · **Milestone:** M3 · **Track:** B + C · **Estimate:** 2.75 h

> As a **student**, I want **a campus calendar of all events I can see (or only my clubs) and a calendar per club** so that **I can plan my week**.

**Acceptance criteria**
- `GET /api/calendar?from&to&scope=all|mine` returns only events of readable spaces (range ≤ 62 days), with club name and RSVP counts.
- Month, week and list views; clicking an event opens its page; cancelled events are visually distinct.
- `/c/:slug/events` shows the same view filtered to the club.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E11-S02-T1 | `CalendarQueryService` (range queries, `filterReadableSpaces`, batch decoration) + `CalendarController` (`/api/calendar`, `/api/clubs/{id}/events`); bind `from`/`to` as `OffsetDateTime` | BE | 1.0 | E11-S01-T2 | [calendar.md §8.2](../../03-backend/calendar.md) |
| E11-S02-T2 | `CampusCalendarPage` (All/My clubs toggle) and `ClubCalendarPage` with FullCalendar 6 | FE | 1.75 | T1 (contract) | [08-frontend §11.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E11-S02)/calendars`

---

### E11-S03 · RSVP and attendance

**Priority:** Should · **Milestone:** M3 · **Track:** B + C · **Estimate:** 1.5 h

> As a **student**, I want to **mark Going / Interested / Not going and see who's coming** so that **organisers can plan and I get reminders**.

**Acceptance criteria**
- RSVP only for readers of the event's space and only before the event ends (BR-22); counts update immediately.
- `RsvpQuery.attendees` serves notifications and reminders.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E11-S03-T1 | `Rsvp` entity, `RsvpService`, `RsvpController`, `calendar.api.RsvpQuery` | BE | 0.5 | E11-S01 | [calendar.md §5, §7](../../03-backend/calendar.md) |
| E11-S03-T2 | `RsvpButtons` on `EventPage` and calendar popover; attendees list | FE | 1.0 | T1 | — |

**Branch:** `UNIX_CLUB/dev/feat(E11-S03)/rsvp`

---

### E11-S04 · Event reminders

**Priority:** Could · **Milestone:** M5 · **Track:** B · **Estimate:** 0.75 h

> As an **attendee**, I want **a reminder the day before and an hour before** so that **I don't miss events**.

**Acceptance criteria**
- Reminder rows are created on schedule and regenerated on reschedule; the job (every minute, `SKIP LOCKED`) emits `EventReminderDue` exactly once per reminder.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E11-S04-T1 | Reminder creation in `EventService` + `ReminderScheduler` | BE | 0.75 | E11-S03, E12-S01 | [calendar.md §8.3, §9](../../03-backend/calendar.md) |

**Branch:** `UNIX_CLUB/dev/feat(E11-S04)/event-reminders`

---

### E11-S05 · Personal iCal feed

**Priority:** Could · **Milestone:** M5 · **Track:** B + C · **Estimate:** 1.5 h

> As a **student**, I want to **subscribe to my clubs' events from Google/Apple Calendar** so that **events show up where I already look**.

**Acceptance criteria**
- `POST /api/me/calendar-feed` returns a secret URL once (token stored hashed); rotating invalidates the old URL.
- `GET /ical/feeds/{token}.ics` returns valid iCalendar with the readable events of my clubs (−30 d … +180 d).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E11-S05-T1 | `FeedTokenService`, `IcalFeedService` (biweekly), `FeedTokenController`, `IcalFeedController` | BE | 1.0 | E11-S02 | [calendar.md §9](../../03-backend/calendar.md) |
| E11-S05-T2 | `FeedSubscribeDialog` in `/settings` and on the campus calendar | FE | 0.5 | T1 | — |

**Branch:** `UNIX_CLUB/dev/feat(E11-S05)/ical-feed`

---

### E11-S06 · Cancel future events when a club is archived

**Priority:** Must · **Milestone:** M4 · **Track:** B · **Estimate:** 0.25 h

> As a **student**, I want **events of an archived club to be cancelled automatically** so that **I don't show up to an event that won't happen** (R-10).

**Acceptance criteria**
- On `ClubArchived`, all `SCHEDULED` events starting in the future become `CANCELLED` (idempotent); past events stay as history.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E11-S06-T1 | `ClubArchivedListener` in calendar | BE | 0.25 | E11-S01, E14-S01-T1 | [calendar.md §6](../../03-backend/calendar.md) |

**Branch:** `UNIX_CLUB/dev/feat(E11-S06)/archive-cancels-events`
