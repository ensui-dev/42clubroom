# Guide 02 — Backend foundation

**Goal:** a Spring Boot 3.5 modular monolith that builds, starts against the compose services, exposes health and OpenAPI, and fails the build on module boundary violations. Then Login with 42 and local login.

Backlog: **E01-S02**, then **E02-S01**, **E02-S02**, **E02-S04** (owner A). Time: ~2.75 h + ~5.75 h.

> Spring Initializr no longer offers Spring Boot 3.5 (it lists 4.x only), so the project is created **by hand from the design's `pom.xml`**. That is faster than generating and editing anyway.

---

## 1. Project files

```text
UNIX_CLUB/backend/
├── pom.xml                                   ← copy from 03-backend/README.md §3
├── src/main/java/pt/vclubroom/ClubroomApplication.java
├── src/main/resources/application.yml        ← 03-backend/README.md §4.1
├── src/main/resources/application-dev.yml    ← §4.2
├── src/main/resources/application-prod.yml   ← §4.2
├── src/main/resources/db/migration/shared/V202610171200__modulith_event_publication.sql      ← 04-database.md §3.1
├── src/main/resources/db/migration/shared/V202610172111__module_schemas_and_extensions.sql   ← 04-database.md §3.1
└── src/test/java/pt/vclubroom/...
```

Sources: [03-backend/README.md §3–§5](../../03-backend/README.md), [04-database.md §3.1](../../04-database.md). Migrations live in one folder per module (`db/migration/<module>/`); the cross-cutting ones are in `shared/`.

## 2. Maven wrapper

With a local Maven:

```bash
cd UNIX_CLUB/backend
mvn -N wrapper:wrapper -Dmaven=3.9.16
```

Without Maven (Docker):

```bash
cd UNIX_CLUB/backend
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/w -w /w maven:3.9-eclipse-temurin-21 \
  mvn -N -Dmaven.repo.local=/w/.m2tmp wrapper:wrapper -Dmaven=3.9.16 && rm -rf .m2tmp
```

Commit `mvnw`, `mvnw.cmd` and `.mvn/`.

## 3. Shared kernel

Create the classes of [03-backend/README.md §6](../../03-backend/README.md) under `pt.vclubroom.shared` (`security/`, `error/`, `web/`, `config/`), plus `EventPublicationMaintenance` from [06-messaging §3.2](../../06-messaging-and-realtime.md). `config/` also holds `ClockConfig` (the `Clock` bean, §5) and `OpenApiConfig` (API title and version in Swagger).

## 4. Module skeleton script

Run once from `UNIX_CLUB/backend`. It creates the 13 modules with their allowed dependencies and named interfaces, exactly as declared in the module documents.

```bash
#!/usr/bin/env bash
# UNIX_CLUB/backend/scripts/create-modules.sh: generates package-info.java for every module (bash >= 4).
set -euo pipefail
BASE=src/main/java/pt/vclubroom

declare -A DEPS=(
  [identity]='"shared"'
  [club]='"shared", "media::api"'
  [membership]='"shared", "club::api", "club::events", "club::spi", "identity::api"'
  [group]='"shared", "membership::api", "membership::events", "identity::api", "identity::events"'
  [space]='"shared", "club::api", "club::events", "membership::api", "group::api", "group::events"'
  [media]='"shared"'
  [forum]='"shared", "space::api", "media::api", "identity::api", "realtime::api", "realtime::spi"'
  [chat]='"shared", "space::api", "media::api", "identity::api", "realtime::api", "realtime::spi"'
  [calendar]='"shared", "club::api", "club::events", "space::api", "membership::api", "media::api"'
  [notification]='"shared", "identity::api", "club::events", "membership::api", "membership::events", "space::api", "forum::events", "calendar::api", "calendar::events", "realtime::api"'
  [realtime]='"shared"'
  [discovery]='"shared", "club::api", "club::events", "membership::api", "membership::events", "forum::events", "media::api"'
  [history]='"shared", "club::events", "membership::events", "identity::api"'
)

declare -A NAMED=(
  [identity]="api events"
  [club]="api events spi"
  [membership]="api events"
  [group]="api events"
  [space]="api"
  [media]="api"
  [forum]="events"
  [calendar]="api events"
  [realtime]="api spi"
)

mkdir -p "$BASE/shared"
cat > "$BASE/shared/package-info.java" <<'JAVA'
@ApplicationModule(displayName = "Shared kernel", type = ApplicationModule.Type.OPEN)
package pt.vclubroom.shared;

import org.springframework.modulith.ApplicationModule;
JAVA

for module in "${!DEPS[@]}"; do
  mkdir -p "$BASE/$module"
  cat > "$BASE/$module/package-info.java" <<JAVA
@ApplicationModule(displayName = "${module^}", allowedDependencies = {${DEPS[$module]}})
package pt.vclubroom.$module;

import org.springframework.modulith.ApplicationModule;
JAVA
  for interface in ${NAMED[$module]:-}; do
    mkdir -p "$BASE/$module/$interface"
    cat > "$BASE/$module/$interface/package-info.java" <<JAVA
@NamedInterface("$interface")
package pt.vclubroom.$module.$interface;

import org.springframework.modulith.NamedInterface;
JAVA
  done
done
echo "Modules created under $BASE"
```

```bash
bash scripts/create-modules.sh
```

Then add `ModularityTests` and `TestcontainersConfiguration` from [03-backend/README.md §8–§9](../../03-backend/README.md).

## 5. Smoke test

`src/test/java/pt/vclubroom/ClubroomApplicationTests.java` starts the whole application against the Testcontainers PostgreSQL and Redis (`@SpringBootTest` + `@AutoConfigureMockMvc` + `@Import(TestcontainersConfiguration.class)`) and checks through MockMvc that:

- `/actuator/health` and `/v3/api-docs` are public, and `/api/me` is 401 without a session;
- `GET /api/auth/csrf` issues a readable `XSRF-TOKEN` cookie, and a POST passes the CSRF check only with the cookie value echoed in `X-XSRF-TOKEN`;
- the migrations created the 12 module schemas, `pg_trgm` and `event_publication`.

No test properties are needed: the 42 client id/secret have `not-configured` defaults, and mail health is off in `application.yml`. Later integration tests use the same three annotations so Spring reuses the cached context and containers.

```bash
./mvnw verify          # ModularityTests + application tests (Docker must be running for Testcontainers)
```

## 6. Run locally

`UNIX_CLUB/backend/run-dev.sh`:

```bash
#!/usr/bin/env bash
# Starts the backend for local development against compose services (Mailpit for email, Vite origin).
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../.env; set +a
export APP_PUBLIC_URL=http://localhost:5173 S3_PUBLIC_ENDPOINT=http://localhost:5173 COOKIE_SECURE=false \
       SMTP_HOST=localhost SMTP_PORT=1025 SMTP_AUTH=false SMTP_STARTTLS=false SMTP_SSL=false
exec ./mvnw spring-boot:run -Dspring-boot.run.profiles=dev
```

```bash
chmod +x run-dev.sh && ./run-dev.sh
curl -s localhost:8080/actuator/health          # {"status":"UP",...}
curl -s localhost:8080/v3/api-docs | jq .info   # OpenAPI document
```

Both URLs are public (`SecurityConfig`). The dev profile turns the Swagger UI on at <http://localhost:8080/swagger-ui.html>.

> The tunnel route of the demo hostname points at `localhost:8080` on the demo laptop, so whatever runs there is reachable at `https://42clubroom.ensui.dev`, including this dev backend and its Swagger UI. Disable the route in Cloudflare when you don't need it.

## 7. Authentication (E02)

Step by step in **[guide 02a — Authentication](02a-authentication.md)**: users table, Login with 42 that stores users, `identity.api`, local login with a bootstrap admin, logout, the final URL rules and the full `/api/me`. Every file is given in full, each step ends with a green build, and step 7 has the curl and browser checks.

## 8. Done when

- [ ] `./mvnw verify` green; `ModularityTests` lists 13 modules + shared.
- [ ] `/actuator/health` UP, `/v3/api-docs` served, Swagger UI at `/swagger-ui.html` (dev).
- [ ] Local login works with curl; `/api/me` returns 401 without a session ([guide 02a](02a-authentication.md) step 7).
- [ ] Login with 42 through `http://localhost:5173` creates your user (guide 02a step 7; the login page itself comes with guide 03).
