# Guide 02 — Backend foundation

**Goal:** a Spring Boot 3.5 modular monolith that builds, starts against the compose services, exposes health and OpenAPI, and fails the build on module boundary violations. Then Login with 42 and local login.

Backlog: **E01-S02**, then **E02-S01**, **E02-S02**, **E02-S04** (owner A). Time: ~2.75 h + ~5.75 h.

> Spring Initializr no longer offers Spring Boot 3.5 (it lists 4.x only), so the project is created **by hand from the design's `pom.xml`**. That is faster than generating and editing anyway.

---

## 1. Project files

```text
UNIX_CLUB/backend/
├── pom.xml                                   ← copy from 03-backend/README.md §3
├── src/main/java/pt/vclubroom/VclubroomApplication.java
├── src/main/resources/application.yml        ← 03-backend/README.md §4.1
├── src/main/resources/application-dev.yml    ← §4.2
├── src/main/resources/application-prod.yml   ← §4.2
├── src/main/resources/db/migration/V202610170900__schemas_extensions_outbox.sql   ← 04-database.md §3.1
└── src/test/java/pt/vclubroom/...
```

Sources: [03-backend/README.md §3–§5](../../03-backend/README.md), [04-database.md §3.1](../../04-database.md).

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

Create the classes of [03-backend/README.md §6](../../03-backend/README.md) under `pt.vclubroom.shared` (`security/`, `error/`, `web/`, `config/`), plus `EventPublicationMaintenance` from [06-messaging §3.2](../../06-messaging-and-realtime.md).

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

```java
package pt.vclubroom;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.actuate.health.HealthEndpoint;
import org.springframework.boot.actuate.health.Status;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

/** Calls the health endpoint bean directly, so it works before SecurityConfig exists (E02-S01-T5). */
@SpringBootTest(properties = {
        "spring.security.oauth2.client.registration.fortytwo.client-id=test",
        "spring.security.oauth2.client.registration.fortytwo.client-secret=test",
        "app.storage.init-buckets=false",        // no SeaweedFS in tests (BucketInitializer)
        "management.health.mail.enabled=false"   // no SMTP server in tests
})
@Import(TestcontainersConfiguration.class)
class ApplicationSmokeTests {

    @Autowired
    HealthEndpoint healthEndpoint;

    @Test
    void applicationStartsAndIsHealthy() {
        assertThat(healthEndpoint.health().getStatus()).isEqualTo(Status.UP);
    }
}
```

```bash
./mvnw verify          # ModularityTests + smoke test (Docker must be running for Testcontainers)
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

> Until `SecurityConfig` exists (E02-S01-T5), Spring Boot's default security protects every URL, so these two `curl` calls return 401/302. The smoke test above covers M0's health check in the meantime. Once E02 is merged, both URLs are public as configured.

## 7. Authentication (E02)

Follow [identity.md §9](../../03-backend/identity.md) and [07-security §3](../../07-security.md) in this order:

1. `identity` migration ([04-database §4.1](../../04-database.md)) → `User`, enums, `UserRepository`.
2. `identity.api` records/interfaces → `UserDirectoryService`.
3. `FortyTwoProfileMapper`, `FortyTwoOAuth2UserService`, `ClubroomOAuth2User`, `UserProvisioningService`, `IdentityProperties`.
4. `SecurityConfig`, `SpaCsrfTokenRequestHandler`, local login classes, `AuthController`, `MeController`, `AdminBootstrap`.

**Check from the terminal** (local admin from `.env`):

```bash
JAR=$(mktemp)
curl -s -c "$JAR" -b "$JAR" localhost:8080/api/auth/csrf -o /dev/null
XSRF=$(awk '$6=="XSRF-TOKEN"{print $7}' "$JAR")
curl -s -c "$JAR" -b "$JAR" -H "X-XSRF-TOKEN: $XSRF" -H 'Content-Type: application/json' \
     -d '{"username":"admin","password":"change-me-admin"}' localhost:8080/api/auth/login | jq
curl -s -b "$JAR" localhost:8080/api/me | jq          # → your user, admin: true
```

**Login with 42** is tested through the frontend dev server (`http://localhost:5173`, guide 03) because the redirect URI is registered for that origin.

## 8. Done when

- [ ] `./mvnw verify` green; `ModularityTests` lists 13 modules + shared.
- [ ] `/actuator/health` UP, `/v3/api-docs` served, Swagger UI at `/swagger-ui.html` (dev).
- [ ] Local login works with curl; `/api/me` returns 401 without a session.
- [ ] Login with 42 lands back on the SPA logged in (after guide 03).
