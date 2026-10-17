# E05 — Community spaces and access control

| | |
|---|---|
| **Goal** | Every club has spaces with channels; one evaluator decides who can read or write anywhere (D-04, D-07, D-28, D-29). |
| **Design** | [space.md](../../03-backend/space.md), [01-domain-model §3–§4](../../01-domain-model.md) |
| **Primary track** | B (backend), C (frontend) |
| **Depends on** | E04-S02 (ClubApproved), E07-S01 (ClubAuthorization) |
| **Estimate** | 8 h (5 Must · 3 Should · 0 Could) |

## Stories

### E05-S01 · Space model, access evaluator and default space

**Priority:** Must · **Milestone:** M1 · **Track:** B · **Estimate:** 2.75 h

> As a **club**, we want **a default "General" space (Posts forum + Lounge chat) created on approval, and consistent access rules** so that **the club is usable immediately and private content stays private**.

**Acceptance criteria**
- **Given** a club is approved, **then** within seconds it has a space "General" (read `PUBLIC`, write `CLUB_MEMBERS`) with channels "Posts" (FORUM) and "Lounge" (CHAT). Processing the event twice creates nothing new.
- The access matrix holds (unit tests):
  - `PUBLIC` space: any logged-in user reads;
  - `CLUB_MEMBERS`: only members read/write;
  - `SPACE_ACCESS_ALL` and admins bypass;
  - archived club or archived space: nobody writes;
  - `GROUPS` with no groups: fails closed.
- A write rule broader than the read rule is normalised (R-23).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E05-S01-T1 | `space` migration (`spaces`, `channels`) | DB | 0.25 | E01-S02 | [04-database §4.5](../../04-database.md) |
| E05-S01-T2 | Domain `Space`, `Channel`, `AccessRule`, `AccessLevel` + unit tests (normalisation) | BE | 0.75 | T1 | [space.md §9](../../03-backend/space.md) |
| E05-S01-T3 | `space.api` (`SpaceAccessPolicy`, `SpaceAudience`, `ChannelAccess`, `SpaceAccess`, `ChannelType`) + `SpaceAccessEvaluator` + access-matrix unit tests (mock `ClubCatalog`, `ClubAuthorization`, `GroupMembershipQuery`) | BE | 1.25 | T2, E07-S01-T4 | [space.md §4.1, §5, §9](../../03-backend/space.md) |
| E05-S01-T4 | `DefaultSpaceProvisioner` listener on `ClubApproved` | BE | 0.25 | T2, E04-S02-T1 | [space.md §9](../../03-backend/space.md) |
| E05-S01-T5 | `group.api` interfaces (`GroupMembershipQuery`, `GroupCatalog`, `GroupSummary`, `GroupScope`) + **temporary** implementation (no groups: `false` / empty), replaced in E13-S03 | BE | 0.25 | E01-S02 | [group.md §5](../../03-backend/group.md) |

**MVP cut (saves ~0.5 h):** test only the 5 matrix rows above; skip the normalisation tests.

**Branch:** `UNIX_CLUB/dev/feat(E05-S01)/spaces-access-evaluator`

---

### E05-S02 · Spaces API and club sidebar

**Priority:** Must · **Milestone:** M1 · **Track:** B + C · **Estimate:** 2.25 h

> As a **student on a club page**, I want **a sidebar listing the spaces and channels I can read** so that **I can navigate the club's community spaces**.

**Acceptance criteria**
- `GET /api/clubs/{id}/spaces` returns only readable spaces with their channels and `{canWrite, canModerate}` flags; `GET /api/channels/{id}` returns flags and `currentEra`.
- The sidebar shows spaces with 🔒 for restricted ones; clicking a channel opens `/c/:slug/s/:space/:channel`, which renders the forum or chat view by channel type.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E05-S02-T1 | `SpaceQueryService`, `SpaceController`, `ChannelController` (GET endpoints) | BE | 0.75 | E05-S01 | [space.md §7](../../03-backend/space.md) |
| E05-S02-T2 | `SpaceSidebar` in `ClubLayout`, `ChannelPage` dispatcher (FORUM → `ChannelFeed`, CHAT → `ChatRoom`; placeholders until E09/E10) | FE | 1.5 | T1, E04-S03-T1 | [08-frontend §9.2](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E05-S02)/spaces-sidebar`

---

### E05-S03 · Manage spaces, channels and access rules

**Priority:** Should · **Milestone:** M4 · **Track:** B + C · **Estimate:** 3 h

> As a **club owner (or role with `SPACE_MANAGE`)**, I want to **create spaces and channels and set who can read and post** so that **the club can have public announcements, members-only lounges and private board rooms** (team requirement: flexible per-club structure).

**Acceptance criteria**
- Owners create, rename, reorder and archive spaces and channels. Archived ones are read-only and hidden by default.
- Rules accept `PUBLIC`, `CLUB_MEMBERS` or `GROUPS` (club groups of this club or campus groups only, BR-12, else `422 GROUP_NOT_USABLE`).
- The editor shows the effective audience ("Everyone can read · Board can post").

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E05-S03-T1 | `SpaceService` create/update/archive spaces and channels (`SPACE_MANAGE`, `GroupCatalog.assertUsableInClub`) | BE | 1.0 | E05-S02, E07-S01 | [space.md §8.3](../../03-backend/space.md) |
| E05-S03-T2 | `SpaceSettings` + `AccessRuleEditor` (level selectors, group picker, effective-audience sentence) | FE | 2.0 | T1, E13-S03 (group picker) | [08-frontend §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E05-S03)/manage-spaces`
