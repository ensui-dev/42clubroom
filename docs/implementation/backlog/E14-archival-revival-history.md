# E14 — Archival, revival and history

| | |
|---|---|
| **Goal** | Clubs that stop are archived (read-only, nothing lost), can be revived into a new era, and their whole history stays browsable (D-13, D-14, D-23). |
| **Design** | [club.md §8.3–§8.4](../../03-backend/club.md), [history.md](../../03-backend/history.md), [01-domain-model §6.1](../../01-domain-model.md) |
| **Primary track** | A (backend), C (frontend) |
| **Depends on** | E04, E07, E09 |
| **Estimate** | 8.5 h (6 Must · 2.5 Should · 0 Could) |

## Stories

### E14-S01 · Archive a club

**Priority:** Must · **Milestone:** M4 · **Track:** A + C · **Estimate:** 2.5 h

> As an **admin**, I want to **archive a club that is no longer active** so that **the directory stays relevant while its content is preserved** (subject lifecycle: "club archival").

**Acceptance criteria**
- `POST /api/admin/clubs/{id}/archive {reason}` → status `ARCHIVED`, the current era ends, `ClubArchived` is published.
- Afterwards every write is rejected (`422 CLUB_NOT_ACTIVE` or `403 CHANNEL_WRITE_DENIED`): posts, comments, reactions, chat, joins, events, role changes. **All content stays readable** under the same read rules.
- Pending join requests and ownership invitations are cancelled (R-10); future events are cancelled (E11-S06).
- The club page shows an "Archived" banner; the directory hides it by default but lists it with the archived filter.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E14-S01-T1 | `ClubService.archive` + admin endpoint (`ClubArchived`, `ClubProfileUpdated`) | BE | 0.25 | E04-S02 | [club.md §9.3](../../03-backend/club.md) |
| E14-S01-T2 | `ClubLifecycleListener.on(ClubArchived)` in membership (bulk cancel/expire) | BE | 0.25 | T1, E07-S01 | [membership.md §9.7](../../03-backend/membership.md) |
| E14-S01-T3 | Integration test: in an archived club, post / join / create event are rejected; reading still works | TEST | 0.75 | T1, E09-S01, E07-S02 | [02-architecture §8](../../02-architecture.md) |
| E14-S01-T4 | `ArchivedBanner`, read-only states (composers hidden, join disabled), admin "Archive club" with reason dialog | FE | 1.25 | T1 | [08-frontend §9.2](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E14-S01)/archive-club`

---

### E14-S02 · Revive an archived club

**Priority:** Should · **Milestone:** M4 · **Track:** A + C · **Estimate:** 2.5 h

> As a **student**, I want to **ask to revive an archived club**, and as an **admin** to **approve it**, so that **a new generation can rebuild the club with its history intact** (goal: "clubs live longer by getting archived or rebuilt").

**Acceptance criteria**
- Any student can request the revival of an `ARCHIVED` club with a motivation (one pending request per student per club).
- Admin approval: club `ACTIVE`, era *n+1*, requester becomes Owner, previous owners become regular members (R-05), other pending requests are rejected (BR-20).
- Content from previous eras is read-only (BR-15) and labelled with its era.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E14-S02-T1 | `RevivalRequest` domain, `RevivalService` (request/approve/reject), `RevivalController`, admin revival endpoints | BE | 0.75 | E14-S01 | [club.md §9.1, §9.3–§9.4](../../03-backend/club.md) |
| E14-S02-T2 | `ClubLifecycleListener.on(ClubRevived)` in membership (R-05) | BE | 0.25 | T1, E07-S01 | [membership.md §9.7](../../03-backend/membership.md) |
| E14-S02-T3 | `RevivalDialog` on archived clubs + `RevivalQueuePage` in the admin console | FE | 1.5 | T1 | [08-frontend §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E14-S02)/club-revival`

---

### E14-S03 · Club history

**Priority:** Must · **Milestone:** M4 · **Track:** A + C · **Estimate:** 3.5 h

> As a **student or alumnus**, I want to **browse a club's history**: its eras, timeline (founded, owners changed, archived, revived) and all past posts, comments and chat, so that **the club's legacy is never lost** (subject lifecycle: "clubs history (all previous posts and comments)").

**Acceptance criteria**
- `GET /api/clubs/{id}/eras` and `GET /api/clubs/{id}/timeline` (keyset, newest first, actor/subject names resolved) work for active and archived clubs.
- The History tab: era switcher → feed filtered by `?era=n` (read-only), timeline next to it.
- Content of previous eras cannot be edited, commented or reacted to (`422 HISTORY_READ_ONLY`).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E14-S03-T1 | `history` migration, `TimelineEntry`, `TimelineProjector` (club + owner events), `TimelineQueryService`, `TimelineController` | BE | 1.0 | E04-S02, E13-S01 | [history.md §6](../../03-backend/history.md), [04-database §4.12](../../04-database.md) |
| E14-S03-T2 | Verify era read-only rules in forum and chat (`ChannelAccess.isCurrentEra`), add the missing checks | BE | 0.5 | E09-S02, E10-S02 | [forum.md §9](../../03-backend/forum.md) |
| E14-S03-T3 | `ClubHistoryPage`: `EraSwitcher`, `Timeline`, feed by era (reuses `ChannelFeed` with `era`) | FE | 2.0 | T1, E09-S01-T5 | [08-frontend §9.3](../../08-frontend.md) |

**MVP cut (saves ~0.75 h):** timeline as a simple list; era switcher only on the club's first forum channel.

**Branch:** `UNIX_CLUB/dev/feat(E14-S03)/club-history`
