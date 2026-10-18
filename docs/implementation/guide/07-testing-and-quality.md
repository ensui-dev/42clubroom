# Guide 07 — Testing and quality

**Goal:** enough automated checks to merge with confidence, plus a manual acceptance script that maps every subject requirement to something you can click.

---

## 1. Commands (run before every PR)

```bash
# backend (Docker must run: Testcontainers)
cd UNIX_CLUB/backend && ./mvnw verify

# frontend
cd UNIX_CLUB/frontend && npm run lint && npm test && npm run build
```

There is no CI on the organisers' repository, so **these local checks are the gate** (PR checklist, [CONTRIBUTING §4.2](../CONTRIBUTING.md#42-pr-description-template-copy-paste)).

## 2. What to test (minimum per story type)

| Story type | Minimum tests |
|------------|---------------|
| Domain-heavy (club lifecycle, ownership, access rules) | Unit tests for every state transition and business rule touched (BR-xx) |
| Event-driven (approval → owner, archive → cancellations) | One `@ApplicationModuleTest` with `Scenario` per listener chain |
| Endpoint with permissions | One test per role boundary (allowed vs `403`), via integration test or `@WebMvcTest` |
| Frontend component with logic (join button, chat cache merge, reactions) | Vitest + Testing Library for the logic paths |
| Everything | `ModularityTests` (already in `verify`) |

Priority tests that protect the demo:

1. `SpaceAccessEvaluator` access matrix (E05-S01-T3).
2. Founder becomes owner on approval (E07-S01-T6).
3. Archived club is read-only (E14-S01-T3).
4. Ownership step-down keeps ≥ 1 owner (part of E13-S01-T1).
5. *(Could)* Playwright "join and post" (E16-S07).

## 3. Manual acceptance script (M5 sign-off)

Run on `https://42clubroom.ensui.dev` with: a 42 student account (S1), a second user (S2, local account), and the admin (AD).

| # | Subject requirement | Steps | Expected |
|---|--------------------|-------|----------|
| 1 | Main landing page | Open the site logged out | Hero, stats, active/new clubs, categories |
| 2 | Authentication (42) | S1 → Login with 42 | Back on the site logged in, avatar shown |
| 3 | Authentication (password) | AD → local login | Logged in; Admin menu visible |
| 4 | Create a new club | S1 → Start a club → submit | "Waiting for approval" |
| 5 | Roles: Admin | AD → Admin › Approvals → approve | Club ACTIVE; S1 is Owner |
| 6 | Create pages for clubs | Open the club page | Banner, description, General space (Posts, Lounge) |
| 7 | Join clubs | S2 → directory → club → Join (OPEN) / Request (APPROVAL) → S1 approves | S2 is Member |
| 8 | Roles: Owner / Member / Non-member | S2 sees no settings; a logged-in non-member sees PUBLIC posts, no composer | Correct UI per role |
| 9 | Post image / video / audio | S2 posts each media type | Players render and play |
| 10 | Comment / react | S1 comments, S2 replies, both react | Thread and counts correct |
| 11 | Event calendar | S1 creates an event; S2 sees it on the campus calendar and RSVPs | Event visible, counts update |
| 12 | Ownership transfer | S1 → Transfer ownership → S2 accepts | S2 Owner, S1 Member |
| 13 | Club archival | AD archives the club | Banner "Archived"; posting disabled; content readable |
| 14 | Club history | Open History tab | Eras, timeline (founded, owner changed, archived), old posts |
| 15 | *(Should)* Rebuild | S1 requests revival → AD approves | Era 2; S1 Owner; era 1 posts read-only |
| 16 | *(Should)* Chat + notifications | S1 and S2 chat in Lounge; S2 gets a notification on a new post | Instant delivery; badge increments |

## 4. Bug flow

1. Note the bug with steps to reproduce in the tracker; link the story ID it belongs to (or `E16` if cross-cutting).
2. Branch `UNIX_CLUB/dev/fix(<ID>)/<short-desc>`, commit `fix(<ID>): …`, PR, squash merge.
3. After the 11:00 freeze, fix only demo-blocking bugs, by agreement.
