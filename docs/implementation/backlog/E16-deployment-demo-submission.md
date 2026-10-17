# E16 — Deployment, demo and submission

| | |
|---|---|
| **Goal** | The app runs on `https://42clubroom.ensui.dev`, the demo is rehearsed, and `UNIX_CLUB/` is submitted on time with a README that sells it. |
| **Design** | [09-deployment.md](../../09-deployment.md), [10-delivery-plan.md](../../10-delivery-plan.md), [guide 06](../guide/06-deployment-and-demo.md), [guide 08](../guide/08-submission.md) |
| **Primary track** | A (ops), everyone for the demo |
| **Depends on** | E01 (images early), all features (final) |
| **Estimate** | 12.25 h (7.75 Must · 2 Should · 2.5 Could) |

## Stories

### E16-S01 · Container images and production compose

**Priority:** Must · **Milestone:** M1 · **Track:** A · **Estimate:** 1.5 h

> As a **team**, we want **production images and a prod compose file early** so that **deployment problems surface on day 1, not at the deadline**.

**Acceptance criteria**
- `docker compose -f compose.yaml -f compose.prod.yaml --profile demo up -d --build` serves the SPA, API, WebSocket and media on `http://localhost:8080` with 2 backend replicas.
- nginx forwards `Host` and `X-Forwarded-*` correctly (OAuth redirect, presigned uploads work).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E16-S01-T1 | `backend/Dockerfile` (multi-stage, layered) | OPS | 0.5 | E01-S02 | [09-deployment §3.1](../../09-deployment.md) |
| E16-S01-T2 | `frontend/Dockerfile` + `frontend/nginx/default.conf` (Cloudflare-aware) | OPS | 0.5 | E01-S03 | [09-deployment §3.2, §5](../../09-deployment.md) |
| E16-S01-T3 | `compose.prod.yaml`; local prod-like run; smoke test (login, upload, `/ws`) | OPS | 0.5 | T1, T2 | [09-deployment §4.3, §11.2](../../09-deployment.md) |

**Branch:** `UNIX_CLUB/dev/build(E16-S01)/production-images`

---

### E16-S02 · Publish the demo on `42clubroom.ensui.dev`

**Priority:** Must · **Milestone:** M1 · **Track:** A · **Estimate:** 1.5 h

> As a **team**, we want **the demo reachable at `https://42clubroom.ensui.dev` early and redeployable in one command** so that **we test through Cloudflare and judges can try it**.

**Acceptance criteria**
- `https://42clubroom.ensui.dev` serves the app through the existing Cloudflare Tunnel setup (D-34); Login with 42 works there (redirect URI registered).
- `/ws` stays connected; a ≤ 90 MiB video uploads; `/api/*` responses are not cached by Cloudflare.
- `deploy/deploy.sh` (pull `UNIX_CLUB/main`, build, `up -d`) redeploys in one command.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E16-S02-T1 | Cloudflare: public hostname (option A or B), cache bypass rules, Rocket Loader off; `.env` with `APP_PUBLIC_URL=https://42clubroom.ensui.dev`, `HTTP_BIND` | OPS | 0.5 | E16-S01 | [09-deployment §8](../../09-deployment.md) |
| E16-S02-T2 | Smoke test through Cloudflare: 42 login, `/ws`, upload, `CF-Connecting-IP` in nginx logs | OPS | 0.5 | T1 | [09-deployment §8.3](../../09-deployment.md) |
| E16-S02-T3 | `deploy/deploy.sh` redeploy script | OPS | 0.5 | T1 | [guide 06](../guide/06-deployment-and-demo.md) |

**Branch:** `UNIX_CLUB/dev/chore(E16-S02)/demo-deployment`

---

### E16-S03 · Demo data

**Priority:** Should · **Milestone:** M5 · **Track:** A + B · **Estimate:** 2 h

> As a **presenter**, I want **realistic demo data** (clubs with avatars, posts with media, chat history, events with RSVPs, an archived club with two eras) so that **the demo looks alive from the first second**.

**Acceptance criteria**
- With profile `demo`, an empty database is seeded idempotently; the seeding respects module boundaries (one seeder per module, ordered).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E16-S03-T1 | `@Profile("demo")` seeders per module (users alice/bob/carol/dave, 6 clubs, posts, chat, events, archived club with eras) | BE | 2.0 | features merged | [10-delivery-plan §4](../../10-delivery-plan.md) |

**Branch:** `UNIX_CLUB/dev/feat(E16-S03)/demo-data`

---

### E16-S04 · Scaling demonstration

**Priority:** Could · **Milestone:** M5 · **Track:** A · **Estimate:** 0.5 h

> As a **presenter**, I want to **show 3 backend instances serving one chat room** so that **the scalability criterion is demonstrated, not just claimed**.

**Acceptance criteria**
- With `--scale backend=3`, two browsers on different instances exchange chat messages instantly.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E16-S04-T1 | Scale, restart the proxy, verify with logs; script the demo steps | OPS | 0.5 | E10-S02, E16-S01 | [09-deployment §11.3](../../09-deployment.md) |

**Branch:** `UNIX_CLUB/dev/chore(E16-S04)/scaling-demo`

---

### E16-S05 · README and submission

**Priority:** Must · **Milestone:** M5 · **Track:** All · **Estimate:** 2.25 h

> As the **jury**, we want **a README that shows the site, explains how to run it and the tech stack** so that **we can evaluate the project quickly** (subject: submission requirements).

**Acceptance criteria**
- `UNIX_CLUB/README.md` contains: pitch, screenshots/GIF, live demo URL, feature checklist mapped to the subject, how to run (dev and Docker), tech stack, architecture summary with link to the docs, team.
- The final MR `UNIX_CLUB/main` → `main` contains only `UNIX_CLUB/` and is opened before **2026-10-19 12:00**.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E16-S05-T1 | Write `UNIX_CLUB/README.md` from the template | DOC | 1.5 | features merged | [guide 08](../guide/08-submission.md) |
| E16-S05-T2 | Screenshots and a short GIF of the "join in 3 clicks" flow | DOC | 0.5 | E16-S02 | [guide 08](../guide/08-submission.md) |
| E16-S05-T3 | Final checks (diff only `UNIX_CLUB/`, `.env` absent, build from clean clone) + open the MR | OPS | 0.25 | T1 | [CONTRIBUTING §7](../CONTRIBUTING.md#7-final-submission) |

**Branch:** `UNIX_CLUB/dev/docs(E16-S05)/readme-submission`

---

### E16-S06 · Presentation and demo rehearsal

**Priority:** Must · **Milestone:** M5 · **Track:** All · **Estimate:** 2.5 h

> As the **team**, we want **a rehearsed 5-minute demo and a few slides** so that **the presentation (10%) and the architecture story (25%) land**.

**Acceptance criteria**
- The demo script ([10-delivery-plan §5](../../10-delivery-plan.md)) runs twice without errors on the live URL.
- Slides: problem → solution → live demo → architecture (module diagram generated by Spring Modulith, events/outbox, scaling) → lifecycle features → what's next.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E16-S06-T1 | Rehearse the demo script twice; fix blockers | DOC | 1.0 | E16-S02, E16-S03 | [10-delivery-plan §5](../../10-delivery-plan.md) |
| E16-S06-T2 | Slides (use `target/spring-modulith-docs` diagrams and the decision log) | DOC | 1.5 | — | [02-architecture](../../02-architecture.md) |

**Branch:** `UNIX_CLUB/dev/docs(E16-S06)/presentation`

---

### E16-S07 · End-to-end test of the key flow

**Priority:** Could · **Milestone:** M5 · **Track:** C · **Estimate:** 2 h

> As a **team**, we want **one automated end-to-end test of the main flow** so that **last-minute changes don't break the demo**.

**Acceptance criteria**
- Playwright: local user logs in → joins an OPEN club → posts → sees the post in the feed; runs against the compose stack.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E16-S07-T1 | Playwright setup + "join and post" test | TEST | 2.0 | E09-S01, E07-S02 | [08-frontend §13](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/test(E16-S07)/e2e-join-and-post`
