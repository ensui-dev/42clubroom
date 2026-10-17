# E01 — Project foundation

| | |
|---|---|
| **Goal** | A repository, local infrastructure, backend and frontend skeletons where three people can work in parallel from hour one. |
| **Design** | [03-backend/README.md](../../03-backend/README.md), [08-frontend.md](../../08-frontend.md), [09-deployment.md](../../09-deployment.md), [CONTRIBUTING.md](../CONTRIBUTING.md) |
| **Primary track** | A (backend + ops), C (frontend) |
| **Depends on** | — |
| **Estimate** | 8.25 h (8.25 Must · 0 Should · 0 Could) |

## Stories

### E01-S01 · Repository bootstrap

**Priority:** Must · **Milestone:** M0 · **Track:** A · **Estimate:** 2 h

> As a **team**, we want **a shared repository structure, conventions and local infrastructure** so that **everyone can start coding in parallel without stepping on each other**.

**Acceptance criteria**
- **Given** a fresh clone, **when** a developer runs `docker compose -f compose.yaml -f compose.dev.yaml up -d`, **then** postgres, redis, seaweedfs and mailpit report healthy.
- **Given** the hooks are enabled, **when** someone commits `update stuff` or a file outside `UNIX_CLUB/`, **then** the commit is rejected.
- The branch `UNIX_CLUB/main` exists on the official repo and contains the skeleton.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E01-S01-T1 | Create `UNIX_CLUB/main` from `main`; add `UNIX_CLUB/` with `backend/`, `frontend/`, `deploy/`, `.gitignore` (Java, Node, `.env`), `.editorconfig`, stub `README.md` | OPS | 0.5 | — | [guide 01](../guide/01-repository-bootstrap.md) |
| E01-S01-T2 | Add `CONTRIBUTING.md` and the 3 Git hooks (`commit-msg`, `pre-commit`, `pre-push`) in `UNIX_CLUB/.githooks/` | DOC | 0.5 | T1 | [CONTRIBUTING §5](../CONTRIBUTING.md#5-local-git-hooks-r-30) |
| E01-S01-T3 | Add `compose.yaml`, `compose.dev.yaml`, `deploy/seaweedfs/s3.json`, `.env.example` | OPS | 0.75 | T1 | [09-deployment §4, §6, §7](../../09-deployment.md) |
| E01-S01-T4 | Every developer: enable hooks, copy `.env`, start compose, confirm health; agree on the secret-sharing channel | OPS | 0.25 | T2, T3 | [guide 00](../guide/00-prerequisites-and-accounts.md) |

**Branch:** `UNIX_CLUB/dev/chore(E01-S01)/repository-bootstrap` (bootstrap push with `ALLOW_INTEGRATION_PUSH=1`)

---

### E01-S02 · Backend skeleton

**Priority:** Must · **Milestone:** M0 · **Track:** A · **Estimate:** 2.75 h

> As a **backend developer**, I want **a running Spring Boot modular monolith with the shared kernel and module skeletons** so that **each module can be implemented independently and boundary violations fail the build**.

**Acceptance criteria**
- `./mvnw verify` is green, including `ModularityTests`.
- The app starts against the compose services and `ApplicationSmokeTests` sees health `UP`. (`/actuator/health` and `/v3/api-docs` become publicly reachable once E02-S01-T5 adds `SecurityConfig`.)
- All 13 modules exist as packages with their `package-info.java` and `allowedDependencies`.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E01-S02-T1 | `pom.xml` (Boot 3.5.16, Modulith 1.4.13 BOM, AWS SDK BOM), Maven wrapper 3.9.16, `VclubroomApplication`, `application.yml`, `application-dev.yml`, `application-prod.yml` | BE | 0.75 | E01-S01 | [03-backend §3–§5](../../03-backend/README.md) |
| E01-S02-T2 | Shared kernel: `Actor`, `AuthenticatedUser`, error types + `GlobalExceptionHandler`, `CursorPage`, `PageResponse`, `TimeCursor`, `TimeConfig`, `EventPublicationMaintenance` | BE | 0.5 | T1 | [03-backend §6](../../03-backend/README.md), [06 §3.2](../../06-messaging-and-realtime.md) |
| E01-S02-T3 | Base Flyway migration (schemas, `pg_trgm`, `event_publication`) | DB | 0.25 | T1 | [04-database §3.1](../../04-database.md) |
| E01-S02-T4 | Run the module skeleton script (13 modules + named interfaces); add `ModularityTests` | BE | 0.5 | T1 | [guide 02 §4](../guide/02-backend-foundation.md) |
| E01-S02-T5 | `TestcontainersConfiguration` + `ApplicationSmokeTests` (context loads, health UP) | TEST | 0.5 | T3 | [guide 02 §5](../guide/02-backend-foundation.md) |
| E01-S02-T6 | Verify springdoc (`/v3/api-docs`, Swagger in dev) and actuator exposure | BE | 0.25 | T1 | [03-backend §4.1](../../03-backend/README.md) |

**Branch:** `UNIX_CLUB/dev/build(E01-S02)/backend-skeleton`

---

### E01-S03 · Frontend skeleton

**Priority:** Must · **Milestone:** M0 · **Track:** C · **Estimate:** 2.25 h

> As a **frontend developer**, I want **a Vite + React + TypeScript project with Tailwind, shadcn/ui, lint and test tooling and the feature folders** so that **features can be built consistently from the start**.

**Acceptance criteria**
- `npm run dev` serves the app at `http://localhost:5173` and proxies `/api` to the backend.
- `npm run lint`, `npm test` and `npm run build` pass.
- Importing another feature's internal file triggers the ESLint boundary error.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E01-S03-T1 | `npm create vite@9` (react-ts); pin dependencies to the versions in the design (`react-router` 7, FullCalendar 6, …) | FE | 0.5 | E01-S01 | [08-frontend §12.1](../../08-frontend.md) |
| E01-S03-T2 | `@/` alias (tsconfig + Vite), Vite dev proxy (`changeOrigin: false`) | FE | 0.5 | T1 | [08-frontend §12.2–§12.3](../../08-frontend.md) |
| E01-S03-T3 | Tailwind v4 (`@tailwindcss/vite`), `shadcn init`, `theme.css` tokens (light/dark) | FE | 0.75 | T2 | [08-frontend §10](../../08-frontend.md) |
| E01-S03-T4 | ESLint flat config with feature boundaries, Vitest + jsdom, feature folder skeleton with an `index.ts` per feature | FE | 0.5 | T1 | [08-frontend §3, §12.4](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/build(E01-S03)/frontend-skeleton`

---

### E01-S04 · API contract pipeline

**Priority:** Must · **Milestone:** M0 · **Track:** A + C · **Estimate:** 1.25 h

> As a **team**, we want **TypeScript types generated from the backend's OpenAPI document and a typed API client** so that **backend/frontend contract changes break the build instead of production**.

**Acceptance criteria**
- `npm run api:types` regenerates `src/shared/api/schema.d.ts` from a running backend.
- A typed call (`api.GET("/api/public/categories")`) compiles and returns data in the browser.
- Unsafe requests carry `X-XSRF-TOKEN`; error responses surface as `ApiError` with `code`.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E01-S04-T1 | `api:types` script; commit the first `schema.d.ts` | FE | 0.25 | E01-S02-T6, E01-S03 | [08-frontend §6](../../08-frontend.md) |
| E01-S04-T2 | `client.ts` (CSRF + error middleware), `errors.ts`, `bootstrapCsrf()` | FE | 0.5 | T1 | [08-frontend §6](../../08-frontend.md) |
| E01-S04-T3 | `queryClient.ts` + `providers.tsx` (QueryClientProvider; slot for RealtimeProvider) | FE | 0.25 | T2 | [08-frontend §6](../../08-frontend.md) |
| E01-S04-T4 | Stub `GET /api/public/categories` in `discovery` (reads `app.clubs.categories`) to prove the pipeline | BE | 0.25 | E01-S02 | [discovery.md §6](../../03-backend/discovery.md) |

**Branch:** `UNIX_CLUB/dev/feat(E01-S04)/api-contract-pipeline`
