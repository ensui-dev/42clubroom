# E15 — Admin console and platform management

| | |
|---|---|
| **Goal** | Admins have one place to approve clubs, manage archival and revival, users and local accounts, and campus groups. |
| **Design** | [identity.md §7](../../03-backend/identity.md), [group.md §7](../../03-backend/group.md), [08-frontend §4](../../08-frontend.md) |
| **Primary track** | C (frontend), A (backend) |
| **Depends on** | E02 |
| **Estimate** | 7.25 h (0.75 Must · 3.5 Should · 3 Could) |

Feature-specific admin screens live in their own epics: approval queue (E04-S02), archive action (E14-S01), revival queue (E14-S02).

## Stories

### E15-S01 · Admin layout

**Priority:** Must · **Milestone:** M1 · **Track:** C · **Estimate:** 0.75 h

> As an **admin**, I want **an admin area with navigation** (Approvals, Revivals, Clubs, Users, Campus groups) so that **platform management is separate from normal use**.

**Acceptance criteria**
- `/admin/*` is reachable only by admins (`RequireAdmin`); others are redirected home.
- Navigation shows badges with pending counts (approvals, revivals) when available.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E15-S01-T1 | `AdminLayout` (side nav, pending badges), `RequireAdmin` route group, `AdminClubsPage` (all clubs by status, links to archive) | FE | 0.75 | E03-S01, E02-S03-T1 | [08-frontend §4](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E15-S01)/admin-layout`

---

### E15-S02 · Users and local accounts

**Priority:** Should · **Milestone:** M4 · **Track:** A + C · **Estimate:** 3.5 h

> As an **admin**, I want to **create local accounts for staff or partners, promote admins and disable accounts** so that **people without 42 accounts can participate and abuse can be stopped** (D-09).

**Acceptance criteria**
- Admins list and search users, create local accounts with a temporary password, change role or status, reset passwords.
- Disabling a user or changing their role revokes their sessions immediately (BR-24).
- Local users change their password in `/settings` (`PUT /api/me/password`).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E15-S02-T1 | `LocalAccountService`, `AdminUserController`, `SessionRevocationService` | BE | 1.0 | E02-S02 | [identity.md §7, §9.7](../../03-backend/identity.md) |
| E15-S02-T2 | `UsersPage` (search, create local account dialog, role/status toggles, reset password) | FE | 1.75 | T1, E15-S01 | — |
| E15-S02-T3 | `PUT /api/me/password` + password section in `/settings` (local accounts only) | BE+FE | 0.75 | T1 | [identity.md §7](../../03-backend/identity.md) |

**Branch:** `UNIX_CLUB/dev/feat(E15-S02)/admin-users`

---

### E15-S03 · Campus groups administration

**Priority:** Could · **Milestone:** M5 · **Track:** A + C · **Estimate:** 2 h

> As an **admin**, I want to **create manual campus groups** (e.g. "BDE", "Tutors") and manage their members so that **clubs can open spaces to them**.

**Acceptance criteria**
- CRUD of `MANUAL` campus groups and their members; `SYNCED` groups are read-only (`422 GROUP_SYNCED`).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E15-S03-T1 | `CampusGroupService`, `AdminCampusGroupController`, `GET /api/campus-groups` | BE | 0.75 | E13-S03-T1 | [group.md §7](../../03-backend/group.md) |
| E15-S03-T2 | `CampusGroupsPage` | FE | 1.25 | T1 | — |

**Branch:** `UNIX_CLUB/dev/feat(E15-S03)/campus-groups-admin`

---

### E15-S04 · Operations card

**Priority:** Could · **Milestone:** M5 · **Track:** A + C · **Estimate:** 1 h

> As an **admin or developer**, I want to **see the event-outbox backlog and the email backlog** so that **stuck listeners or email problems are visible**.

**Acceptance criteria**
- An admin endpoint returns incomplete publications per listener and pending/failed emails; the admin home shows them.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E15-S04-T1 | `GET /api/admin/ops` (queries from [09-deployment §12](../../09-deployment.md)) + card in the admin home | BE+FE | 1.0 | E12-S03 | [06-messaging §8](../../06-messaging-and-realtime.md) |

**Branch:** `UNIX_CLUB/dev/feat(E15-S04)/ops-card`
