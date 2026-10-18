# E02 — Identity and authentication

| | |
|---|---|
| **Goal** | Students log in with 42, staff and partners with a local password; the session works across instances; the SPA knows who is logged in. |
| **Design** | [identity.md](../../03-backend/identity.md), [07-security.md](../../07-security.md), [08-frontend §8](../../08-frontend.md) |
| **Guide** | Backend (E02-S01, E02-S02, E02-S04-T1): [guide 02a](../guide/02a-authentication.md), step by step with every file |
| **Primary track** | A (backend), C (frontend) |
| **Depends on** | E01 |
| **Estimate** | 8 h (8 Must · 0 Should · 0 Could) |

## Stories

### E02-S01 · Login with 42

**Priority:** Must · **Milestone:** M0 · **Track:** A · **Estimate:** 3.5 h

> As a **42 student**, I want to **log in with my intra account** so that **I don't need another password and my profile is filled in automatically**.

**Acceptance criteria**
- **Given** a 42 account, **when** I click "Login with 42" and accept, **then** I land on `/` logged in and `GET /api/me` returns my login, display name and avatar.
- **Given** I log in a second time, **then** my profile is refreshed and no duplicate user is created.
- **Given** no session, **when** the SPA calls `GET /api/me`, **then** it gets `401` (not a redirect).
- **Given** my login is in `APP_ADMIN_BOOTSTRAP_LOGINS`, **then** my first login makes me `ADMIN`.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E02-S01-T1 | Register the 42 OAuth app with the 3 redirect URIs (dev, local prod, `https://42clubroom.ensui.dev`); share `FT_CLIENT_ID/SECRET` privately | OPS | 0.25 | — | [09-deployment §9](../../09-deployment.md) |
| E02-S01-T2 | `identity` migration, `User` entity, enums, `UserRepository` | BE | 0.5 | E01-S02 | [identity.md §9.1–§9.2](../../03-backend/identity.md), [04-database §4.1](../../04-database.md) |
| E02-S01-T3 | `FortyTwoProfileMapper`, `FortyTwoOAuth2UserService`, `ClubroomOAuth2User` | BE | 0.5 | T2 | [identity.md §9.3](../../03-backend/identity.md) |
| E02-S01-T4 | `UserProvisioningService` + `UserRegistered` / `UserProfileSynced` events, `IdentityProperties` | BE | 0.5 | T2 | [identity.md §9.4](../../03-backend/identity.md) |
| E02-S01-T5 | `SecurityConfig` (URL rules, OAuth2 login, 401 entry point, logout), `SpaCsrfTokenRequestHandler`, Spring Session Redis config | BE | 1.0 | T3 | [07-security §3](../../07-security.md) |
| E02-S01-T6 | `MeController` + `MeResponse` + `UserDirectoryService.requireMe` | BE | 0.25 | T4 | [identity.md §9.5–§9.6](../../03-backend/identity.md) |
| E02-S01-T7 | Tests: mapper unit test with a sample `/v2/me` JSON; `@WebMvcTest` asserting 401 on `/api/me` without session | TEST | 0.5 | T5 | [03-backend §9](../../03-backend/README.md) |

**MVP cut (saves ~0.5 h):** skip T7's web test; keep the mapper test (42's JSON is the riskiest part).

**Branch:** `UNIX_CLUB/dev/feat(E02-S01)/login-with-42`

---

### E02-S02 · Local login and admin bootstrap

**Priority:** Must · **Milestone:** M0 · **Track:** A · **Estimate:** 1.5 h

> As an **admin or external partner without a 42 account**, I want to **log in with a username and password** so that **I can use the platform** (subject: "login with 42intra & password").

**Acceptance criteria**
- **Given** `APP_BOOTSTRAP_ADMIN_USERNAME/PASSWORD` are set, **when** the app starts, **then** that local admin exists (created once).
- **Given** valid credentials, **when** `POST /api/auth/login`, **then** `200 MeResponse` and a `SESSION` cookie; invalid ones give `401 INVALID_CREDENTIALS`.
- `POST /api/auth/logout` returns `204` and the session is gone.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E02-S02-T1 | `LocalUserDetailsService`, `LocalUserDetails`, `LocalPrincipal`, `localAuthenticationManager` + `PasswordEncoder` beans | BE | 0.5 | E02-S01-T5 | [identity.md §9.5](../../03-backend/identity.md), [07-security §3](../../07-security.md) |
| E02-S02-T2 | `AuthController` (`/api/auth/login`, `/api/auth/csrf`) | BE | 0.5 | T1 | [identity.md §9.5](../../03-backend/identity.md) |
| E02-S02-T3 | `AdminBootstrap` runner | BE | 0.25 | T1 | [identity.md §9.8](../../03-backend/identity.md) |
| E02-S02-T4 | Test: local login success and failure (integration with Testcontainers) | TEST | 0.25 | T2 | — |

**Branch:** `UNIX_CLUB/dev/feat(E02-S02)/local-login`

---

### E02-S03 · Authentication UI

**Priority:** Must · **Milestone:** M0 · **Track:** C · **Estimate:** 2.25 h

> As a **visitor**, I want **a clear login page and to come back where I was after logging in** so that **joining a club takes as few clicks as possible**.

**Acceptance criteria**
- **Given** I'm logged out, **when** I open a protected route, **then** I'm sent to `/login?returnTo=…`, and after logging in (42 or local) I'm back on that route.
- `returnTo` values that are not relative paths are ignored (open-redirect protection).
- The top bar shows my avatar with a menu (Settings, Admin if admin, Logout).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E02-S03-T1 | `useMe`, `RequireAuth`, `RequireAdmin`, `safeReturnTo`, `PostLoginRedirect` | FE | 0.75 | E01-S04 | [08-frontend §8](../../08-frontend.md) |
| E02-S03-T2 | `LoginPage`: "Login with 42" button + local login form (React Hook Form + Zod), error display | FE | 1.0 | T1 | [08-frontend §8](../../08-frontend.md) |
| E02-S03-T3 | Top-bar user menu, logout (`POST /api/auth/logout` + `queryClient.clear()`) | FE | 0.5 | T1, E03-S01 | [08-frontend §8](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E02-S03)/auth-ui`

---

### E02-S04 · User directory API

**Priority:** Must · **Milestone:** M1 · **Track:** A · **Estimate:** 0.75 h

> As a **developer of other modules**, I want **a `UserDirectory` API and a user search endpoint** so that **members lists, authors and ownership invitations can show and pick users**.

**Acceptance criteria**
- `UserDirectory.findByIds` resolves many users in one query.
- `GET /api/users?query=jdo&limit=10` returns matching active users by login prefix or display name.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E02-S04-T1 | `identity.api` (`UserDirectory`, `UserSummary`, `UserContact`, `PlatformRole`) + `UserDirectoryService` | BE | 0.25 | E02-S01 | [identity.md §5, §9.6](../../03-backend/identity.md) |
| E02-S04-T2 | `UserController`: `GET /api/users?query=&limit=`, `GET /api/users/{id}` | BE | 0.5 | T1 | [identity.md §7](../../03-backend/identity.md) |

**Branch:** `UNIX_CLUB/dev/feat(E02-S04)/user-directory`
