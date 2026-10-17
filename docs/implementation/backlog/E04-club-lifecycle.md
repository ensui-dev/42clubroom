# E04 — Club lifecycle: creation, approval, club page

| | |
|---|---|
| **Goal** | Students request clubs, admins approve or reject them, approved clubs get a page. |
| **Design** | [club.md](../../03-backend/club.md) (reference slice with full code), [01-domain-model §6.1](../../01-domain-model.md) |
| **Primary track** | A (backend), C (frontend) |
| **Depends on** | E01, E02 |
| **Estimate** | 11.5 h (9.5 Must · 2 Should · 0 Could) |

## Stories

### E04-S01 · Request the creation of a club

**Priority:** Must · **Milestone:** M1 · **Track:** A + C · **Estimate:** 4.5 h

> As a **student**, I want to **request the creation of a club** so that **my community gets its own space once an admin approves it** (subject: "ability to create a new club").

**Acceptance criteria**
- **Given** I'm logged in, **when** I submit name, tagline, description, category and tags, **then** a club is created with status `PENDING_APPROVAL`, join policy `APPROVAL` and a unique slug.
- **Given** a pending club, **then** only its founder and admins can see it (`404` for others, BR-03).
- **Given** I already have 3 pending requests, **then** a fourth is refused with `422 TOO_MANY_PENDING_REQUESTS`.
- "My requests" lists my pending and rejected requests (with the rejection reason).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E04-S01-T1 | `club` migration (`clubs`, `club_eras`, `revival_requests`) | DB | 0.25 | E01-S02 | [04-database §4.2](../../04-database.md) |
| E04-S01-T2 | Domain `Club`, `ClubEra`, `EraStartReason`, `Slug`, `ClubStatus`, `JoinPolicy` + unit tests for the state machine and slug rules | BE | 0.75 | T1 | [club.md §9.1](../../03-backend/club.md) |
| E04-S01-T3 | `ClubRepository`, `ClubProperties`, `ClubService.requestCreation`, `ClubCreationRequested` event | BE | 0.5 | T2 | [club.md §9.2–§9.3](../../03-backend/club.md) |
| E04-S01-T4 | `ClubController` (`POST /api/clubs`, `GET /api/clubs/{idOrSlug}`, `GET /api/me/club-requests`), DTOs, `ClubQueryService`, `ClubDetailsAssembler` (media URLs `null` until E08) | BE | 0.5 | T3 | [club.md §9.3–§9.4](../../03-backend/club.md) |
| E04-S01-T5 | `ClubCatalog` API + `ClubCatalogService`; `ClubManagementGuard` SPI with a **temporary** admin-only implementation (replaced in E07-S01-T4) | BE | 0.5 | T3 | [club.md §5](../../03-backend/club.md) |
| E04-S01-T6 | `CreateClubWizard` (basics → description and tags → preview, React Hook Form + Zod, categories from `/api/public/categories`) and "My requests" list | FE | 2.0 | T4 (contract), E03-S02 | [08-frontend §9.3](../../08-frontend.md) |

**MVP cut (saves ~1.0 h):** a single-page form instead of the 3-step wizard.

**Branch:** `UNIX_CLUB/dev/feat(E04-S01)/club-creation-request`

---

### E04-S02 · Admin approves or rejects club requests

**Priority:** Must · **Milestone:** M1 · **Track:** A + C · **Estimate:** 2.5 h

> As an **admin**, I want to **review pending clubs and approve or reject them with a reason** so that **the directory stays curated**.

**Acceptance criteria**
- **Given** a pending club, **when** an admin approves it, **then** it becomes `ACTIVE` with era 1, and `ClubApproved` + `ClubProfileUpdated` are published.
- Reacting modules then create the founder's Owner membership (E07-S01) and the default space (E05-S01), and the club appears in the directory (E06-S01).
- Rejecting requires a reason; the founder sees it in "My requests".
- Non-admins get `403` on `/api/admin/**`.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E04-S02-T1 | `ClubService.approve/reject` + `ClubApproved`, `ClubRejected`, `ClubProfileUpdated` | BE | 0.5 | E04-S01-T3 | [club.md §9.3](../../03-backend/club.md) |
| E04-S02-T2 | `ClubAdminController` (`GET /api/admin/clubs?status=`, approve, reject) | BE | 0.25 | T1 | [club.md §9.4](../../03-backend/club.md) |
| E04-S02-T3 | Module test (`@ApplicationModuleTest` + `Scenario`): approving publishes `ClubApproved` with era 1 | TEST | 0.5 | T1 | [03-backend §9](../../03-backend/README.md) |
| E04-S02-T4 | `ApprovalQueuePage` in the admin console: list, preview, approve, reject-with-reason dialog | FE | 1.25 | T2, E15-S01 | [08-frontend §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E04-S02)/club-approval`

---

### E04-S03 · Club page

**Priority:** Must · **Milestone:** M1 · **Track:** C · **Estimate:** 2.5 h

> As a **student**, I want **each club to have its own page** with banner, description, members count, owners and a join button, so that **I understand what the club is about** (subject: "create pages for clubs").

**Acceptance criteria**
- `/c/:slug` shows banner, avatar, name, status badge, tagline, description (Markdown), member count and owners.
- The layout has a left sidebar slot (spaces, E05-S02), a main area and a right panel (about, upcoming events slot).
- Pending clubs show a "waiting for approval" state to their founder.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E04-S03-T1 | `ClubLayout`: header (banner, avatar, name, `StatusBadge`, `JoinButton` slot), sidebar slot, right panel, responsive grid | FE | 1.5 | E03-S01, E04-S01-T4 | [08-frontend §9.2](../../08-frontend.md) |
| E04-S03-T2 | `ClubHome`: about card, stats, owners list, feed slot (E09-S05), events slot (E11-S02) | FE | 1.0 | T1 | [08-frontend §9.2](../../08-frontend.md) |

**MVP cut (saves ~0.5 h):** no right panel; about and owners in the main column.

**Branch:** `UNIX_CLUB/dev/feat(E04-S03)/club-page`

---

### E04-S04 · Edit club profile and join policy

**Priority:** Should · **Milestone:** M2 · **Track:** A + C · **Estimate:** 2 h

> As a **club owner (or role with `CLUB_SETTINGS_MANAGE`)**, I want to **edit the club profile, images and join policy** so that **the page stays up to date and we choose open or approval-based membership**.

**Acceptance criteria**
- `PATCH /api/clubs/{id}` updates only the provided fields; without the permission → `403`.
- Switching `APPROVAL` → `OPEN` auto-approves pending requests (E07-S03-T2).
- Avatar and banner upload through media (E08) and appear in the directory.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E04-S04-T1 | `ClubService.updateProfile` (SPI guard, media attach, join policy) + `PATCH /api/clubs/{id}` | BE | 0.5 | E04-S01, E07-S01-T4 | [club.md §8.5, §9.3](../../03-backend/club.md) |
| E04-S04-T2 | Club settings › Profile tab (form, avatar/banner upload with `uploadMedia`, join policy switch) | FE | 1.5 | T1, E08-S02-T3 | [08-frontend §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E04-S04)/club-profile-settings`
