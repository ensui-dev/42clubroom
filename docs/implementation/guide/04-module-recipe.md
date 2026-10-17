# Guide 04 — Implementing a story: the module recipe

Every feature story follows the same recipe, so anyone can pick up any module. The **club module** ([club.md](../../03-backend/club.md)) is the worked example with every layer written out.

---

## 1. Before you start (Definition of Ready)

- [ ] The story is assigned to you in the tracker and its dependencies are merged (or stubbed).
- [ ] You have read the module document sections: **1 Responsibility**, **5 API**, **6 Events**, **7 Endpoints**, **8 Flows**.
- [ ] Branch created from the latest integration branch:
  ```bash
  git fetch origin
  git switch -c 'UNIX_CLUB/dev/feat(E04-S01)/club-creation-request' origin/UNIX_CLUB/main
  ```

## 2. Backend steps

| # | Step | Where | Rules |
|---|------|-------|-------|
| 1 | **Migration** | `db/migration/<module>/V<yyyyMMddHHmm>__<module>_<what>.sql` | Copy the DDL from [04-database §4](../../04-database.md). Timestamp version; never edit a merged migration. |
| 2 | **Domain** | `<module>/domain` | Entities with factory methods, guarded state transitions, `@Version`, Java-generated UUIDs, `Instant` truncated to micros. Unit-test the invariants (BR-xx). |
| 3 | **Repositories** | `<module>/persistence` | Spring Data interfaces; JPQL for simple queries, native SQL for keyset / `ON CONFLICT` / `SKIP LOCKED`. |
| 4 | **Public surface** | `<module>/api`, `<module>/events`, `<module>/spi` | Records and interfaces only. Keep them small: they are the contract other modules compile against. |
| 5 | **Application services** | `<module>/application` | One `@Transactional` method per use case: **authorize first** (`ClubAuthorization` / `SpaceAccessPolicy`), then domain call, save, `publishEvent`, return a view. |
| 6 | **Listeners** | `<module>/application` | `@ApplicationModuleListener`, **idempotent** (existence checks, upserts, dedup keys), writing only to the own schema. |
| 7 | **Web** | `<module>/web` | Controllers translate HTTP ↔ commands/views; Bean Validation on request records; return `web` DTOs; `@AuthenticationPrincipal AuthenticatedUser me` → `me.actor()`. |
| 8 | **Security** | `SecurityConfig` | Only if you add a new URL prefix (most endpoints live under `/api/**`, already authenticated). |
| 9 | **Tests** | `src/test/java/pt/vclubroom/<module>` | Domain unit tests; one `@ApplicationModuleTest` with `Scenario` for event flows; a web slice or integration test for the main endpoint. |
| 10 | **Verify** | — | `./mvnw verify` (includes `ModularityTests`). Fix boundary errors by using the other module's `api`/`events`, never its internals. |
| 11 | **Try it** | Swagger (`/swagger-ui.html`) or the curl helper (§4) | Walk through the story's acceptance criteria. |

**Contract-first shortcut:** if the frontend is waiting, merge steps 4 + 7 first with stubbed responses (`feat(<ID>): add <endpoint> contract`), then the real implementation.

## 3. Frontend steps

| # | Step | Where | Rules |
|---|------|-------|-------|
| 1 | **Types** | `src/shared/api/schema.d.ts` | `npm run api:types` against a backend that has the endpoint. |
| 2 | **Data hooks** | `src/features/<feature>/api.ts` | TanStack Query hooks; query keys per [08-frontend §5.1](../../08-frontend.md); mutations invalidate related keys. |
| 3 | **Components and pages** | `src/features/<feature>/` | Use `@/shared/ui` components and primitives only; loading (skeleton), empty (`EmptyState`) and error states. |
| 4 | **Permissions in the UI** | `useMyMembership().can("EVENT_MANAGE")` | Hide what the user can't do; the backend enforces anyway. |
| 5 | **Routing** | `src/app/router.tsx` | Replace the placeholder with the lazy page. |
| 6 | **Public API** | `src/features/<feature>/index.ts` | Export only what other features need. |
| 7 | **Check** | — | `npm run lint && npm test && npm run build`; click through the acceptance criteria. |

Template for a feature's `api.ts`:

```ts
// src/features/clubs/api.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import type { components } from "@/shared/api/schema";

export type Club = components["schemas"]["ClubResponse"];
export type CreateClubInput = components["schemas"]["CreateClubRequest"];

export const clubKeys = {
  detail: (slugOrId: string) => ["club", slugOrId] as const,
  myRequests: () => ["me", "club-requests"] as const,
};

export function useClub(slugOrId: string) {
  return useQuery({
    queryKey: clubKeys.detail(slugOrId),
    queryFn: async () => {
      const { data } = await api.GET("/api/clubs/{idOrSlug}", { params: { path: { idOrSlug: slugOrId } } });
      return data as Club;
    },
  });
}

export function useRequestClub() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateClubInput) => {
      const { data } = await api.POST("/api/clubs", { body });
      return data as Club;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clubKeys.myRequests() }),
  });
}
```

## 4. Testing endpoints from the terminal

`UNIX_CLUB/backend/scripts/api.sh`: logs in with a local account once, then calls any endpoint with the session and CSRF header.

```bash
#!/usr/bin/env bash
# Usage: scripts/api.sh login <user> <password> | scripts/api.sh <METHOD> <path> [json-body]
set -euo pipefail
BASE="${BASE:-http://localhost:8080}"
JAR="${JAR:-/tmp/vclubroom-cookies.txt}"
xsrf() { awk '$6=="XSRF-TOKEN"{print $7}' "$JAR" | tail -1; }

if [[ "${1:-}" == "login" ]]; then
  rm -f "$JAR"
  curl -s -c "$JAR" -b "$JAR" "$BASE/api/auth/csrf" -o /dev/null
  curl -s -c "$JAR" -b "$JAR" -H "X-XSRF-TOKEN: $(xsrf)" -H 'Content-Type: application/json' \
       -d "{\"username\":\"$2\",\"password\":\"$3\"}" "$BASE/api/auth/login" | jq
  exit 0
fi

method="$1"; path="$2"; body="${3:-}"
args=(-s -c "$JAR" -b "$JAR" -X "$method" -H "X-XSRF-TOKEN: $(xsrf)")
[[ -n "$body" ]] && args+=(-H 'Content-Type: application/json' -d "$body")
curl "${args[@]}" "$BASE$path" | jq
```

```bash
scripts/api.sh login admin change-me-admin
scripts/api.sh POST /api/clubs '{"name":"Chess Club","category":"Games","tags":["chess"]}'
scripts/api.sh GET '/api/admin/clubs?status=PENDING_APPROVAL'
```

## 5. Finish (Definition of Done)

- [ ] Acceptance criteria met and listed in the PR "How to test".
- [ ] `./mvnw verify` and `npm run lint && npm test && npm run build` green.
- [ ] Commit messages follow `type(ID): description`; PR title = `feat(E04-S01): request club creation`.
- [ ] PR into `UNIX_CLUB/main`, 1 approval, **squash merge**, branch deleted, tracker updated.
- [ ] If DTOs changed: announce it; whoever merges regenerates `schema.d.ts`.

## 6. Common pitfalls

| Symptom | Cause / fix |
|---------|-------------|
| `ModularityTests` fails: "depends on non-exposed type" | You imported another module's internal package. Use its `api`/`events`, or add a method to its API (ask the owner). |
| `Violations: cycle detected` | Two modules depend on each other. Use an SPI (dependency inversion), as `club.spi.ClubManagementGuard` does. |
| Listener didn't run | It runs **after commit** and **asynchronously**: check the triggering transaction committed, `@EnableAsync` is present, and look at `event_publication`. |
| Listener ran twice | Expected (at-least-once). Make it idempotent. |
| `ddl-auto=validate` fails at start-up | Entity and migration disagree (column name or type). Fix the migration (if not merged) or add a new one. |
| `403` on POST from the SPA | Missing CSRF header: use the `api` client, call `bootstrapCsrf()` once. |
| Frontend type errors after pulling | Regenerate `schema.d.ts` from the current backend. |
