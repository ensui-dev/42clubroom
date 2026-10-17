# E07 — Membership and joining

| | |
|---|---|
| **Goal** | Students join clubs (instantly or by request), clubs have owners and members, and every module can ask "may this user do X in this club?". |
| **Design** | [membership.md](../../03-backend/membership.md), [01-domain-model §3–§4, §6.2–§6.3](../../01-domain-model.md) |
| **Primary track** | A (backend), C (frontend) |
| **Depends on** | E04-S01 (ClubCatalog), E04-S02 (ClubApproved) |
| **Estimate** | 9.25 h (7.25 Must · 2 Should · 0 Could) |

## Stories

### E07-S01 · Membership model and club authorization API

**Priority:** Must · **Milestone:** M1 · **Track:** A · **Estimate:** 3 h

> As a **developer of any module**, I want **memberships with Owner/Member roles and a single `ClubAuthorization` API** so that **permission checks are consistent everywhere** (subject roles: Club Owner, Club Member, Non-member, Admin).

**Acceptance criteria**
- **Given** a club is approved, **then** its system roles Owner (all permissions) and Member exist, and the founder is an active member holding both. Processing the event twice changes nothing.
- `ClubAuthorization.require(club, actor, P)` throws `422 CLUB_NOT_ACTIVE` for non-active clubs and `403 PERMISSION_DENIED` without the permission; admins pass (R-08).
- `ClubManagementGuard` is now implemented by membership (the temporary guard from E04-S01-T5 is deleted).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E07-S01-T1 | `membership` migration (roles, memberships, membership_roles, join_requests, ownership_invitations) | DB | 0.25 | E01-S02 | [04-database §4.3](../../04-database.md) |
| E07-S01-T2 | Domain: `Membership`, `ClubRole`, `SystemRole`, `JoinRequest`, `OwnershipInvitation`, `ClubOwnership`, statuses; `ClubPermission` enum in `api` | BE | 0.75 | T1 | [membership.md §9.1](../../03-backend/membership.md) |
| E07-S01-T3 | Repositories with the documented queries (`findActive`, `findHeldRoles`, `findHolderIds`, `findSystemRoleForUpdate`…) | BE | 0.5 | T2 | [membership.md §9.2](../../03-backend/membership.md) |
| E07-S01-T4 | `ClubAuthorizationService` implementing `ClubAuthorization` + `ClubManagementGuard`; remove the temporary guard | BE | 0.5 | T3, E04-S01-T5 | [membership.md §9.3](../../03-backend/membership.md) |
| E07-S01-T5 | `MembershipAdmission` + `ClubLifecycleListener.on(ClubApproved)` | BE | 0.5 | T3, E04-S02-T1 | [membership.md §9.4, §9.7](../../03-backend/membership.md) |
| E07-S01-T6 | Module test: founder becomes owner (`Scenario`, `OwnerAdded` awaited) | TEST | 0.5 | T5 | [03-backend §9](../../03-backend/README.md) |

**Branch:** `UNIX_CLUB/dev/feat(E07-S01)/membership-authorization`

---

### E07-S02 · Join a club

**Priority:** Must · **Milestone:** M2 · **Track:** A + C · **Estimate:** 2.5 h

> As a **student**, I want to **join a club in one click (open clubs) or send a request (approval clubs)** so that **I can take part** (subject: "join clubs through the site").

**Acceptance criteria**
- `OPEN` club → `201 {status: JOINED}` and I'm a member immediately; `APPROVAL` club (default) → `202 {status: REQUESTED}`.
- Joining twice → `409 ALREADY_MEMBER`; requesting twice → `409 JOIN_ALREADY_REQUESTED`; archived club → `422 CLUB_NOT_ACTIVE`.
- `GET /api/clubs/{id}/membership/me` returns membership, roles, effective permissions and pending request/invitation. The UI uses it to show or hide controls.
- Leaving works except for the last owner (`422 LAST_OWNER`).
- Logged-out flow: Join → login → back to the club → join executes automatically.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E07-S02-T1 | `JoinService.join` + `JoinOutcome` + events (`MemberJoined`, `JoinRequested`) | BE | 0.5 | E07-S01 | [membership.md §9.4](../../03-backend/membership.md) |
| E07-S02-T2 | `MembershipController`: join, `membership/me`, `/api/me/memberships`, leave (`MemberLeft`, BR-04) | BE | 0.75 | T1 | [membership.md §7](../../03-backend/membership.md) |
| E07-S02-T3 | `JoinButton` (+ `?intent=join`), `useMyMembership` hook and `can(permission)` helper | FE | 1.25 | T2 (contract), E04-S03 | [08-frontend §11.1](../../08-frontend.md) |

**MVP cut (saves ~0.5 h):** skip "leave club" in the UI (endpoint only).

**Branch:** `UNIX_CLUB/dev/feat(E07-S02)/join-club`

---

### E07-S03 · Handle join requests

**Priority:** Must · **Milestone:** M2 · **Track:** A + C · **Estimate:** 1.75 h

> As a **club owner (or role with `MEMBER_APPROVE`)**, I want to **approve or reject join requests** so that **approval-based clubs (the default) can grow**.

**Acceptance criteria**
- Pending requests are listed with the requester and message; approve creates the membership, reject closes the request; both publish `JoinRequestDecided`.
- Requesters can cancel their pending request.
- Switching the club to `OPEN` auto-approves pending requests.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E07-S03-T1 | `JoinService.approve/reject`, cancel-mine, `JoinRequestController` | BE | 0.5 | E07-S02-T1 | [membership.md §9.4](../../03-backend/membership.md) |
| E07-S03-T2 | `ClubLifecycleListener.on(ClubProfileUpdated)`: OPEN → auto-approve | BE | 0.25 | T1 | [membership.md §9.7](../../03-backend/membership.md) |
| E07-S03-T3 | `JoinRequestsPanel` (club settings › Requests) with approve/reject | FE | 1.0 | T1 | [08-frontend §4](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E07-S03)/join-requests`

---

### E07-S04 · Members list and removal

**Priority:** Should · **Milestone:** M2 · **Track:** A + C · **Estimate:** 2 h

> As a **club member**, I want to **see who is in the club and their roles**, and as an **owner** to **remove disruptive members**, so that **the community is visible and manageable**.

**Acceptance criteria**
- `GET /api/clubs/{id}/members` (members only) lists users with avatars and roles, searchable, paginated.
- `MEMBER_REMOVE` holders remove non-owners (`MemberLeft` reason `REMOVED`); removing an owner → `403` (BR-05).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E07-S04-T1 | `MemberService` + `MemberController` (list with `UserDirectory.findByIds`, remove) | BE | 0.75 | E07-S02, E02-S04 | [membership.md §7](../../03-backend/membership.md) |
| E07-S04-T2 | `MembersPage` (search, role badges, remove action if permitted) | FE | 1.25 | T1 | [08-frontend §4](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E07-S04)/members-list`
