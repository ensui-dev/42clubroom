# E13 — Governance: ownership, roles and groups

| | |
|---|---|
| **Goal** | Clubs outlive their members through co-ownership and transfer, and define their own structure with custom roles and groups (D-12, D-18, D-19, D-22). |
| **Design** | [membership.md §8.2, §9.5–§9.6](../../03-backend/membership.md), [group.md](../../03-backend/group.md) |
| **Primary track** | A (backend), C (frontend) |
| **Depends on** | E07 |
| **Estimate** | 11.75 h (4 Must · 7 Should · 0.75 Could) |

## Stories

### E13-S01 · Co-ownership and ownership transfer

**Priority:** Must · **Milestone:** M4 · **Track:** A + C · **Estimate:** 4 h

> As a **club owner about to graduate**, I want to **invite a member to become co-owner or transfer ownership to them** so that **the club survives my departure** (subject lifecycle: "club ownership transfer").

**Acceptance criteria**
- An owner invites an active member (`transfer` optional); the invitee sees and accepts or declines it; invitations expire after 7 days (R-11).
- Accepting adds the Owner role; with `transfer = true` the inviter steps down in the same transaction.
- An owner can step down unless they are the last owner (`422 LAST_OWNER`); concurrent step-downs can never leave zero owners (row lock).
- Admins can assign or remove owners (D-22).
- `OwnerAdded`, `OwnerSteppedDown` and `OwnerRemoved` appear in the club history (E14-S03).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E13-S01-T1 | `OwnershipService` (invite, accept, decline, revoke, step-down with `findSystemRoleForUpdate`) + events | BE | 1.0 | E07-S01 | [membership.md §9.5](../../03-backend/membership.md) |
| E13-S01-T2 | `OwnershipController`, `GET /api/me/ownership-invitations`, `AdminOwnershipController` (assign/remove owner) | BE | 0.75 | T1 | [membership.md §7](../../03-backend/membership.md) |
| E13-S01-T3 | `InvitationExpiryJob` (hourly bulk expiry) | BE | 0.25 | T1 | [membership.md §11](../../03-backend/membership.md) |
| E13-S01-T4 | `OwnershipPanel` (owners list, invite co-owner via member/user search, "Transfer ownership", step down with explanation) + invitation inbox (accept/decline) | FE | 2.0 | T2, E02-S04 | [08-frontend §9.3](../../08-frontend.md) |

**MVP cut (saves ~1.0 h):** only "Transfer ownership" (invite with `transfer = true`) + accept; no separate co-owner invite UI or expiry job.

**Branch:** `UNIX_CLUB/dev/feat(E13-S01)/ownership-transfer`

---

### E13-S02 · Custom club roles

**Priority:** Should · **Milestone:** M4 · **Track:** A + C · **Estimate:** 3.75 h

> As a **club owner**, I want to **create roles like "Event lead" or "Board" with chosen permissions and assign them to members** so that **the club's own management structure is reflected** (team requirement: flexible per-club structure).

**Acceptance criteria**
- CRUD of custom roles with permissions from the catalogue (`GET /api/permissions`); the Owner role is immutable and system roles can't be deleted (BR-10).
- Anti-escalation: you can only grant permissions you hold (`403 PERMISSION_ESCALATION`, BR-14); Owner is never assignable through roles.
- Members' role assignment is editable; effective permissions update immediately (e.g. granting `EVENT_MANAGE` to Member lets members create events).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E13-S02-T1 | `RoleService` (create/update/delete, assign roles to a member, anti-escalation), `RoleController`, `GET /api/permissions` (with descriptions), `MemberRolesChanged` | BE | 1.25 | E07-S01 | [membership.md §9.6](../../03-backend/membership.md) |
| E13-S02-T2 | `RolesEditor` (permission checkboxes with descriptions; unheld permissions disabled) + role assignment on `MembersPage` | FE | 2.5 | T1, E07-S04 | [08-frontend §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E13-S02)/custom-roles`

---

### E13-S03 · Club groups

**Priority:** Should · **Milestone:** M4 · **Track:** A + C · **Estimate:** 3.25 h

> As a **club owner (or role with `GROUP_MANAGE`)**, I want **named groups of members** (e.g. "Board") so that **I can restrict spaces to them**.

**Acceptance criteria**
- CRUD of club groups and their members; only active club members can be added (BR-13).
- Leaving the club removes the user from that club's groups (R-22); deleting a group removes it from space rules (a rule left empty fails closed).
- The temporary `group.api` implementation from E05-S01-T5 is replaced.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E13-S03-T1 | `groups` migration, `Group`/`GroupMember`, repositories, `ClubGroupService`, `ClubGroupController`, `GroupQueryService` (replaces the temporary implementation), `GroupDeleted` | BE | 1.25 | E07-S01, E05-S01-T5 | [group.md §9](../../03-backend/group.md), [04-database §4.4](../../04-database.md) |
| E13-S03-T2 | `MembershipEndedListener` (group) + `GroupDeletedListener` (space) | BE | 0.5 | T1 | [group.md §9](../../03-backend/group.md), [space.md §9](../../03-backend/space.md) |
| E13-S03-T3 | `GroupsSettings` + group picker used by `AccessRuleEditor` | FE | 1.5 | T1 | [08-frontend §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E13-S03)/club-groups`

---

### E13-S04 · Campus groups synced from 42

**Priority:** Could · **Milestone:** M5 · **Track:** A · **Estimate:** 0.75 h

> As a **club**, I want to **open a space to a campus cohort** (e.g. `pool-2026-september`, `campus-lisboa`) so that **we can reach the right students even before they join**.

**Acceptance criteria**
- At each 42 login, the user is added to (and removed from) `SYNCED` campus groups derived from pool, campus, cursus and alumni (idempotent).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E13-S04-T1 | `CampusSyncRules` + `CampusGroupSyncListener` (`UserProfileSynced`) | BE | 0.75 | E13-S03-T1, E02-S01-T4 | [group.md §8.1, §9](../../03-backend/group.md) |

**Branch:** `UNIX_CLUB/dev/feat(E13-S04)/campus-groups-sync`
