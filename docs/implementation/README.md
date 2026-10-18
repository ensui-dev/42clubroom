# Implementation collection — UNIX_CLUB

The **how** that goes with the design's **what**: a step-by-step implementation guide, the contribution rules, and the complete backlog of epics, stories and tasks to take Virtual Clubroom to completion and submission (deadline **2026-10-19 12:00**).

---

## Contents

| Document | Use it to… |
|----------|-----------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Know the rules: branches `UNIX_CLUB/dev/<type>(<ID>)/<short-desc>`, Conventional Commits with backlog-ID scope, PRs into `UNIX_CLUB/main`, squash merge, Git hooks, Definition of Done. **Everyone reads this first.** |
| [backlog/README.md](backlog/README.md) | **Divide the work**: epic summary, capacity analysis, critical path, per-person queues, Should priority order, status tracking, index of all stories. |
| [github-project/](github-project/README.md) | **Import the backlog into GitHub Projects** (draft items with Epic, Priority, Milestone, Suggested owner and Estimate fields) using a `gh`-based script; CSV exports for spreadsheets. |
| [backlog/E01…E16](backlog/) | Each epic's stories with user story, acceptance criteria, tasks (layer, estimate, dependencies, design reference), MVP cut and branch name. |
| [guide/00-prerequisites-and-accounts.md](guide/00-prerequisites-and-accounts.md) | Tools, ports, external accounts with waiting times (42 OAuth, Resend DNS, Cloudflare), secrets. |
| [guide/01-repository-bootstrap.md](guide/01-repository-bootstrap.md) | Create `UNIX_CLUB/main`, the team folder, hooks and local infrastructure. |
| [guide/02-backend-foundation.md](guide/02-backend-foundation.md) | Spring Boot skeleton by hand (no Initializr for Boot 3.5), module skeleton script, smoke test, authentication. |
| [guide/02a-authentication.md](guide/02a-authentication.md) | Login with 42 that stores users, local login with a bootstrap admin, logout, URL rules and `/api/me` (E02 backend), every file in full. |
| [guide/03-frontend-foundation.md](guide/03-frontend-foundation.md) | Vite + React + Tailwind v4 + shadcn/ui, feature folders, typed API client, auth UI. |
| [guide/04-module-recipe.md](guide/04-module-recipe.md) | The repeatable recipe for any story (backend and frontend steps), terminal API helper, common pitfalls. |
| [guide/05-build-order.md](guide/05-build-order.md) | First three hours, milestone checkpoints M0–M5 with checklists, hand-offs between people, what to do when behind. |
| [guide/06-deployment-and-demo.md](guide/06-deployment-and-demo.md) | Production images, `42clubroom.ensui.dev` via Cloudflare Tunnel, Resend, redeploy script, scaling demo, troubleshooting. |
| [guide/07-testing-and-quality.md](guide/07-testing-and-quality.md) | Local quality gate, minimum tests per story type, manual acceptance script mapped to every subject requirement. |
| [guide/08-submission.md](guide/08-submission.md) | README template, final checklist, merge request, presentation tips. |

## How to use it (team lead's path)

1. **Hour 0:** everyone reads [CONTRIBUTING.md](CONTRIBUTING.md) and [backlog §3 Capacity](backlog/README.md#3-capacity-read-this-before-planning).
2. **Hour 0–1:** A bootstraps the repo (guide 01), B starts the external accounts (guide 00 §2), C sets up the frontend (guide 03).
3. **Assign** stories from the per-person queues ([backlog §5](backlog/README.md#5-suggested-assignment)) into your tracker; adjust to people's strengths.
4. **Build** each story with the recipe (guide 04); merge behind contracts; meet at the milestone checkpoints (guide 05).
5. **Deploy early** (E16-S01/S02 on Day 1 evening), then continuously with `deploy/deploy.sh` (guide 06).
6. **Freeze at 11:00**, run the acceptance script (guide 07), open the MR (guide 08).

## Key numbers

- **16 epics · 63 stories · 179 tasks.**
- **Must ≈ 85 h** of ideal work (≈ 77 h with all MVP cuts) for **≈ 78 h** of raw team time: the mandatory scope is tight. Should work starts only when your Must queue is empty ([backlog §3](backlog/README.md#3-capacity-read-this-before-planning)).

## Related design documents

[Decision log](../00-decision-log.md) · [Domain model](../01-domain-model.md) · [Architecture](../02-architecture.md) · [Backend](../03-backend/README.md) · [Database](../04-database.md) · [API](../05-api-reference.md) · [Messaging](../06-messaging-and-realtime.md) · [Security](../07-security.md) · [Frontend](../08-frontend.md) · [Deployment](../09-deployment.md) · [Delivery plan](../10-delivery-plan.md)
