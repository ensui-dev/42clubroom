# E06 — Discovery and landing page

| | |
|---|---|
| **Goal** | New students find clubs without logging in (landing page + directory + public profile, D-24, R-24). |
| **Design** | [discovery.md](../../03-backend/discovery.md), [08-frontend §9.1](../../08-frontend.md) |
| **Primary track** | A (backend), C (frontend) |
| **Depends on** | E04-S02 (ClubProfileUpdated), E07-S01 (member counts) |
| **Estimate** | 5.75 h (5.75 Must · 0 Should · 0 Could) |

## Stories

### E06-S01 · Club directory read model and public API

**Priority:** Must · **Milestone:** M1 · **Track:** A · **Estimate:** 2 h

> As an **anonymous visitor**, I want **fast public endpoints for the landing page, the club list and club profiles** so that **I can discover clubs before logging in**.

**Acceptance criteria**
- **Given** a club is approved, **then** it appears in `GET /api/public/clubs` within seconds, with name, tagline, category, avatar and member count. Pending and rejected clubs never appear.
- Search `q`, `category`, `tag`, `status` (default `ACTIVE`) and `sort` (`active`, `new`, `members`, `name`) work; archived clubs appear only with `status=ARCHIVED|ALL`.
- `GET /api/public/landing` returns stats, most active, newest and categories with counts; no endpoint here requires login.
- Re-delivered or out-of-order events don't corrupt the card (idempotent projector).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E06-S01-T1 | `discovery` migration (`club_cards` with generated `tsvector`, trigram and GIN indexes) | DB | 0.25 | E01-S02 | [04-database §4.11](../../04-database.md) |
| E06-S01-T2 | `ClubCardProjector` (ClubProfileUpdated, ClubApproved, MemberJoined/Left, PostPublished) + `ClubCardRepository` upserts | BE | 0.75 | T1, E04-S02-T1 | [discovery.md §8](../../03-backend/discovery.md) |
| E06-S01-T3 | `DirectorySearchRepository` (JdbcClient), `DirectoryQueryService`, `PublicDirectoryController` (`/landing`, `/clubs`, `/clubs/{slug}`, `/categories`) | BE | 1.0 | T2 | [discovery.md §6–§8](../../03-backend/discovery.md) |

**MVP cut (saves ~0.5 h):** `name ILIKE` search only (no `tsvector`); sort by `active` and `new` only.

**Branch:** `UNIX_CLUB/dev/feat(E06-S01)/club-directory-api`

---

### E06-S02 · Landing page

**Priority:** Must · **Milestone:** M1 · **Track:** C · **Estimate:** 1.5 h

> As a **new student**, I want **an inviting landing page that shows what's happening on campus** so that **I know where to start** (subject: "main landing page").

**Acceptance criteria**
- Hero with value proposition and two CTAs ("Browse clubs", "Login with 42" / "Start a club").
- Stats (active clubs, memberships), most active clubs, newest clubs, categories (clickable → directory filter).
- Works logged out; looks good in both themes and on mobile.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E06-S02-T1 | `LandingPage` + `ClubCard` component (used by the directory too) | FE | 1.5 | E06-S01-T3, E03-S02 | [08-frontend §9.1](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E06-S02)/landing-page`

---

### E06-S03 · Club directory and public club profile

**Priority:** Must · **Milestone:** M1 · **Track:** C · **Estimate:** 2.25 h

> As a **new student**, I want to **search and filter clubs and read a club's profile before logging in** so that **I can choose a club and join in a few clicks** (UI/UX criterion).

**Acceptance criteria**
- `/clubs`: debounced search, category and tag filters, sort, "show archived" toggle, pagination. Filters are kept in the URL query.
- `/clubs/:slug/about`: public profile with a **Join** button. Logged out → `/login?returnTo=…?intent=join`, then the join resumes automatically (E07-S02).
- Archived clubs show an "Archived" badge and link to their history.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E06-S03-T1 | `ClubDirectoryPage` (search, filters, sort, archived toggle, pagination, URL state) | FE | 1.5 | E06-S02-T1 | [08-frontend §4](../../08-frontend.md) |
| E06-S03-T2 | `PublicClubProfilePage` with join CTA and intent handling | FE | 0.75 | E06-S01-T3, E07-S02-T3 | [08-frontend §11.1](../../08-frontend.md) |

**MVP cut (saves ~0.5 h):** no tag filter or pagination (cards in a grid, sorted by activity).

**Branch:** `UNIX_CLUB/dev/feat(E06-S03)/club-directory-ui`
