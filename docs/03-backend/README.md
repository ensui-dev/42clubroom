# 03 — Backend (Spring Boot)

This document covers the backend as a whole: stack, repository layout, build, configuration, the shared kernel, the module template, and testing. Each module then has its own document (links at the end).

---

## 1. Tech stack

| Concern | Choice | Version |
|---------|--------|---------|
| Language | Java | 21 (LTS) |
| Framework | Spring Boot | 3.5.16 (last OSS 3.5.x) |
| Build | Maven | 3.9.x |
| Modularity | Spring Modulith (core, JDBC event registry, actuator, test, docs) | 1.4.13 |
| Web | Spring MVC (`spring-boot-starter-web`) on **virtual threads** | Boot-managed |
| Security | Spring Security 6.5, OAuth2 Client, Spring Session Data Redis | Boot-managed |
| Real-time | Spring WebSocket + STOMP, simple broker per instance + Redis pub/sub relay | Boot-managed |
| Persistence | Spring Data JPA (Hibernate 6.6), Flyway 11, PostgreSQL JDBC | Boot-managed |
| Cache / pub-sub | Spring Data Redis (Lettuce) | Boot-managed |
| Object storage | AWS SDK for Java v2 (`s3`) against SeaweedFS | 2.56.0 |
| Email | Spring Mail (`JavaMailSender`) | Boot-managed |
| iCalendar | biweekly | 0.6.8 |
| API docs | springdoc-openapi (webmvc-ui) | 2.8.17 |
| Tests | JUnit 5, Spring Boot Test, Spring Modulith Test, Testcontainers (PostgreSQL, Redis) | Boot-managed |

No Lombok and no MapStruct: records and explicit mappers keep every snippet self-explanatory and avoid annotation-processing surprises during a hackathon.

---

## 2. Application repository layout

```text
UNIX_CLUB/                         # submission directory: Hackathon_SA_2026/UNIX_CLUB
├── README.md                      # showcase, how to run, tech stack (required by the subject)
├── compose.yaml                   # base services (postgres, redis, seaweedfs)
├── compose.dev.yaml               # dev overrides (ports, mailpit)
├── compose.prod.yaml              # prod overrides (backend, proxy)
├── .env.example
├── deploy/
│   └── seaweedfs/s3.json          # S3 identities / bucket permissions
├── backend/
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/
│       ├── main/java/pt/vclubroom/...      # see §2.1
│       ├── main/resources/
│       │   ├── application.yml
│       │   ├── application-dev.yml
│       │   ├── application-prod.yml
│       │   └── db/migration/
│       │       ├── shared/V202610171200__modulith_event_publication.sql
│       │       ├── shared/V202610172111__module_schemas_and_extensions.sql
│       │       ├── identity/V202610170910__identity_init.sql
│       │       ├── club/V202610170920__club_init.sql
│       │       └── ... one folder per module (see 04-database.md)
│       └── test/java/pt/vclubroom/...
├── frontend/
│   ├── Dockerfile
│   ├── nginx/default.conf
│   └── ... (see 08-frontend.md)
└── docs/                          # this documentation
```

### 2.1 Java package tree

```text
pt.vclubroom
├── ClubroomApplication.java
├── shared/                                  OPEN module (shared kernel)
│   ├── package-info.java
│   ├── config/{ClockConfig, OpenApiConfig, EventPublicationMaintenance}.java
│   ├── error/{DomainException, NotFoundException, ForbiddenException, ConflictException,
│   │          BusinessRuleException, InvalidRequestException, GlobalExceptionHandler}.java
│   ├── security/{Actor, AuthenticatedUser}.java
│   └── web/{CursorPage, PageResponse, TimeCursor}.java
├── identity/
│   ├── api/{UserDirectory, UserSummary, UserContact, PlatformRole}.java
│   ├── events/{UserRegistered, UserProfileSynced}.java
│   ├── web/{MeController, AuthController, UserController, AdminUserController}.java + web/dto/*
│   ├── application/{UserProvisioningService, LocalAccountService, UserDirectoryService,
│   │                AdminBootstrap, SessionRevocationService, IdentityProperties, ProvisionedUser}.java
│   ├── domain/{User, AuthProvider, UserStatus, FortyTwoProfile}.java
│   ├── persistence/UserRepository.java
│   └── infrastructure/security/{SecurityConfig, SpaCsrfTokenRequestHandler, FortyTwoOAuth2UserService,
│                                FortyTwoProfileMapper, ClubroomOAuth2User, LocalPrincipal,
│                                LocalUserDetails, LocalUserDetailsService}.java
├── club/
│   ├── api/{ClubCatalog, ClubSnapshot, ClubStatus, JoinPolicy}.java
│   ├── events/{ClubCreationRequested, ClubApproved, ClubRejected, ClubProfileUpdated,
│   │           ClubArchived, ClubRevivalRequested, ClubRevived}.java
│   ├── spi/ClubManagementGuard.java
│   ├── web/{ClubController, ClubAdminController, RevivalController}.java + web/dto/*
│   ├── application/{ClubService, ClubQueryService, ClubCatalogService, RevivalService, ClubDetailsAssembler,
│   │                ClubProperties, CreateClubCommand, UpdateClubCommand, ClubDetails, RevivalRequestView}.java
│   ├── domain/{Club, ClubEra, RevivalRequest, RevivalStatus, Slug}.java
│   └── persistence/{ClubRepository, RevivalRequestRepository}.java
├── membership/
│   ├── api/{ClubAuthorization, ClubPermission}.java
│   ├── events/{MemberJoined, MemberLeft, JoinRequested, JoinRequestDecided,
│   │           OwnershipInvitationSent, OwnerAdded, OwnerSteppedDown, OwnerRemoved, MemberRolesChanged}.java
│   ├── web/{MembershipController, MemberController, JoinRequestController, RoleController,
│   │        OwnershipController, AdminOwnershipController}.java + web/dto/*
│   ├── application/{JoinService, MemberService, RoleService, OwnershipService,
│   │                ClubAuthorizationService, ClubLifecycleListener, InvitationExpiryJob}.java
│   ├── domain/{Membership, MembershipStatus, ClubRole, SystemRole, JoinRequest, JoinRequestStatus,
│   │           OwnershipInvitation, InvitationStatus, ClubOwnership}.java
│   └── persistence/{MembershipRepository, ClubRoleRepository, JoinRequestRepository,
│                    OwnershipInvitationRepository}.java
├── group/        api/ events/ web/ application/ domain/ persistence/   (see group.md)
├── space/        api/ web/ application/ domain/ persistence/            (see space.md)
├── media/        api/ web/ application/ domain/ persistence/ infrastructure/ (see media.md)
├── forum/        events/ web/ application/ domain/ persistence/         (see forum.md)
├── chat/         web/ application/ domain/ persistence/                 (see chat.md)
├── calendar/     api/ events/ web/ application/ domain/ persistence/    (see calendar.md)
├── notification/ web/ application/ domain/ persistence/ infrastructure/ (see notification.md)
├── realtime/     api/ spi/ infrastructure/                              (see realtime.md)
├── discovery/    web/ application/ domain/ persistence/                 (see discovery.md)
└── history/      web/ application/ domain/ persistence/                 (see history.md)
```

---

## 3. Build: `backend/pom.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.5.16</version>
        <relativePath/>
    </parent>

    <groupId>pt.vclubroom</groupId>
    <artifactId>vclubroom-backend</artifactId>
    <version>0.1.0-SNAPSHOT</version>
    <name>vclubroom-backend</name>
    <description>Virtual Clubroom — modular monolith REST API</description>

    <properties>
        <java.version>21</java.version>
        <spring-modulith.version>1.4.13</spring-modulith.version>
        <aws-sdk.version>2.56.0</aws-sdk.version>
        <springdoc.version>2.8.17</springdoc.version>
        <biweekly.version>0.6.8</biweekly.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.springframework.modulith</groupId>
                <artifactId>spring-modulith-bom</artifactId>
                <version>${spring-modulith.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
            <dependency>
                <groupId>software.amazon.awssdk</groupId>
                <artifactId>bom</artifactId>
                <version>${aws-sdk.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <dependencies>
        <!-- Web / API -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-websocket</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springdoc</groupId>
            <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
            <version>${springdoc.version}</version>
        </dependency>

        <!-- Security -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-oauth2-client</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.session</groupId>
            <artifactId>spring-session-data-redis</artifactId>
        </dependency>

        <!-- Persistence -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-core</artifactId>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-database-postgresql</artifactId>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-redis</artifactId>
        </dependency>

        <!-- Modularity + reliable domain events (outbox in PostgreSQL) -->
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-starter-core</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-starter-jdbc</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-actuator</artifactId>
            <scope>runtime</scope>
        </dependency>

        <!-- Integrations -->
        <dependency>
            <groupId>software.amazon.awssdk</groupId>
            <artifactId>s3</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-mail</artifactId>
        </dependency>
        <dependency>
            <groupId>net.sf.biweekly</groupId>
            <artifactId>biweekly</artifactId>
            <version>${biweekly.version}</version>
        </dependency>

        <!-- Operations -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>

        <!-- Tests -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.security</groupId>
            <artifactId>spring-security-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-docs</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-testcontainers</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>postgresql</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>junit-jupiter</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

---

## 4. Configuration

### 4.1 `src/main/resources/application.yml`

```yaml
spring:
  application:
    name: vclubroom
  threads:
    virtual:
      enabled: true                       # Java 21 virtual threads for MVC + @Async listeners
  datasource:
    url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:vclubroom}
    username: ${DB_USER:vclubroom}
    password: ${DB_PASSWORD:vclubroom}
    hikari:
      maximum-pool-size: ${DB_POOL_SIZE:20}
  jpa:
    open-in-view: false
    hibernate:
      ddl-auto: validate                  # Flyway owns the schema
    properties:
      hibernate:
        jdbc:
          time_zone: UTC
          batch_size: 50
        order_inserts: true
        default_batch_fetch_size: 50
  flyway:
    enabled: true
    create-schemas: true
    schemas: identity,club,membership,groups,space,forum,media,chat,calendar,notification,discovery,history
    default-schema: public
    locations: classpath:db/migration
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
  session:
    timeout: 14d
    redis:
      namespace: vclubroom:session
      repository-type: indexed            # allows "invalidate all sessions of user X"
  mvc:
    problemdetails:
      enabled: true
  servlet:
    multipart:
      enabled: false                      # media never goes through the app (presigned uploads)
  modulith:
    events:
      republish-outstanding-events-on-restart: true
      jdbc:
        schema-initialization:
          enabled: false                  # table created by Flyway (V..._create_schemas.sql)
  security:
    oauth2:
      client:
        registration:
          fortytwo:
            provider: fortytwo
            client-id: ${FT_CLIENT_ID}
            client-secret: ${FT_CLIENT_SECRET}
            client-authentication-method: client_secret_post
            authorization-grant-type: authorization_code
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
            scope: public
            client-name: 42 Intra
        provider:
          fortytwo:
            authorization-uri: https://api.intra.42.fr/oauth/authorize
            token-uri: https://api.intra.42.fr/oauth/token
            user-info-uri: https://api.intra.42.fr/v2/me
            user-name-attribute: login
  mail:                                   # any SMTP provider: Mailpit (dev), Resend (demo, D-35), bocal's SMTP later
    host: ${SMTP_HOST:localhost}
    port: ${SMTP_PORT:1025}
    username: ${SMTP_USER:}
    password: ${SMTP_PASSWORD:}
    properties:
      mail.smtp.auth: ${SMTP_AUTH:false}
      mail.smtp.starttls.enable: ${SMTP_STARTTLS:false}     # port 587
      mail.smtp.starttls.required: ${SMTP_STARTTLS:false}
      mail.smtp.ssl.enable: ${SMTP_SSL:false}               # port 465 (implicit TLS)
      mail.smtp.connectiontimeout: 5000                     # never let a slow provider block the email job
      mail.smtp.timeout: 5000
      mail.smtp.writetimeout: 5000

server:
  port: 8080
  shutdown: graceful
  forward-headers-strategy: framework     # trust X-Forwarded-* from nginx (OAuth redirect URIs)
  servlet:
    session:
      cookie:
        http-only: true
        secure: ${COOKIE_SECURE:true}
        same-site: lax

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,modulith
  endpoint:
    health:
      probes:
        enabled: true

springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html

app:
  public-url: ${APP_PUBLIC_URL:http://localhost:5173}
  admin:
    bootstrap-logins: ${APP_ADMIN_BOOTSTRAP_LOGINS:}
    bootstrap-local-username: ${APP_BOOTSTRAP_ADMIN_USERNAME:}
    bootstrap-local-password: ${APP_BOOTSTRAP_ADMIN_PASSWORD:}
  clubs:
    categories: [Tech, Games, Arts, Music, Sports, Culture, Social, Science, Other]
  forum:
    reactions:                             # code -> emoji (fixed platform set, D-26)
      thumbs_up: "👍"
      heart: "❤️"
      laugh: "😂"
      party: "🎉"
      wow: "😮"
      sad: "😢"
  media:
    public-bucket: media-public
    private-bucket: media-private
    upload-url-ttl: 10m
    download-url-ttl: 15m
    orphan-ttl: 24h
    limits:
      IMAGE:
        max-bytes: 10485760
        content-types: [image/jpeg, image/png, image/webp, image/gif]
      AUDIO:
        max-bytes: 52428800
        content-types: [audio/mpeg, audio/ogg, audio/wav, audio/webm]
      VIDEO:
        max-bytes: 94371840                # 90 MiB: Cloudflare rejects request bodies > 100 MB (R-12)
        content-types: [video/mp4, video/webm]
  storage:
    endpoint: ${S3_ENDPOINT:http://localhost:8333}          # used by the backend (inside docker: http://seaweedfs:8333)
    public-endpoint: ${S3_PUBLIC_ENDPOINT:${app.public-url}} # used in presigned URLs (what browsers reach)
    region: us-east-1
    access-key: ${S3_ACCESS_KEY:vclubroom}
    secret-key: ${S3_SECRET_KEY:vclubroom-secret}
  realtime:
    allowed-origins: ${app.public-url}
    redis-channel: vclubroom:rt
  calendar:
    reminder-offsets: [24h, 1h]
    display-zone: Europe/Lisbon
  fortytwo:
    campus-groups-enabled: true
  mail:
    transport: ${MAIL_TRANSPORT:smtp}      # smtp | log (log = print emails instead of sending, for offline dev)
    from: ${MAIL_FROM:Virtual Clubroom <no-reply@localhost>}   # demo: Virtual Clubroom <no-reply@42clubroom.ensui.dev>
    reply-to: ${MAIL_REPLY_TO:}
```

### 4.2 Profiles

| File | Purpose |
|------|---------|
| `application-dev.yml` | `server.servlet.session.cookie.secure: false`, `logging.level.pt.vclubroom: DEBUG`, `springdoc.swagger-ui.enabled: true`. |
| `application-prod.yml` | `logging.structured.format.console: ecs`, `springdoc.swagger-ui.enabled: false`, `springdoc.api-docs.enabled: false`. |

Secrets (`FT_CLIENT_SECRET`, `DB_PASSWORD`, `S3_SECRET_KEY`, `SMTP_PASSWORD`, bootstrap admin password) come **only** from environment variables (`.env`, never committed).

---

## 5. Application entry point and global configuration

```java
package pt.vclubroom;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@ConfigurationPropertiesScan
@EnableAsync        // @ApplicationModuleListener runs asynchronously after commit
@EnableScheduling   // reminders, email outbox, event-publication maintenance jobs
public class ClubroomApplication {

    public static void main(String[] args) {
        SpringApplication.run(ClubroomApplication.class, args);
    }
}
```

```java
package pt.vclubroom.shared.config;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** One injectable clock so time-based rules (events, archival, handover) can be tested deterministically. */
@Configuration
class ClockConfig {

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
```

---

## 6. Shared kernel (`pt.vclubroom.shared`)

The shared kernel is deliberately tiny: identity of the caller, error types and pagination. It is declared **OPEN** so every module can use it without listing named interfaces.

```java
@ApplicationModule(displayName = "Shared kernel", type = ApplicationModule.Type.OPEN)
package pt.vclubroom.shared;

import org.springframework.modulith.ApplicationModule;
```

### 6.1 Caller identity

```java
package pt.vclubroom.shared.security;

import java.util.Objects;
import java.util.UUID;

/**
 * Who performs a use case. Application services receive an Actor, never a Spring Security type,
 * which keeps the application layer free of web/security concerns and trivially testable.
 */
public record Actor(UUID userId, boolean admin) {

    public Actor {
        Objects.requireNonNull(userId, "userId");
    }
}
```

```java
package pt.vclubroom.shared.security;

import java.io.Serializable;
import java.util.UUID;

/**
 * Implemented by every principal the identity module puts in the SecurityContext
 * (42 OAuth2 user and local user). Serializable because sessions are stored in Redis.
 * Controllers obtain it with @AuthenticationPrincipal AuthenticatedUser me.
 */
public interface AuthenticatedUser extends Serializable {

    UUID userId();

    boolean admin();

    default Actor actor() {
        return new Actor(userId(), admin());
    }
}
```

### 6.2 Errors

```java
package pt.vclubroom.shared.error;

/** Base type of every expected business error. The code is stable and documented in 05-api-reference.md. */
public abstract class DomainException extends RuntimeException {

    private final String code;

    protected DomainException(String code, String message) {
        super(message);
        this.code = code;
    }

    public String code() {
        return code;
    }
}
```

```java
package pt.vclubroom.shared.error;

public class NotFoundException extends DomainException {
    public NotFoundException(String code, String message) {
        super(code, message);
    }
}
```

```java
package pt.vclubroom.shared.error;

public class ForbiddenException extends DomainException {
    public ForbiddenException(String code, String message) {
        super(code, message);
    }
}
```

```java
package pt.vclubroom.shared.error;

public class ConflictException extends DomainException {
    public ConflictException(String code, String message) {
        super(code, message);
    }
}
```

```java
package pt.vclubroom.shared.error;

/** A request that is well-formed but violates a business rule (HTTP 422). */
public class BusinessRuleException extends DomainException {
    public BusinessRuleException(String code, String message) {
        super(code, message);
    }
}
```

```java
package pt.vclubroom.shared.error;

/** A malformed request that Bean Validation cannot express, e.g. an undecodable cursor (HTTP 400). */
public class InvalidRequestException extends DomainException {
    public InvalidRequestException(String code, String message) {
        super(code, message);
    }
}
```

```java
package pt.vclubroom.shared.error;

import java.util.List;
import java.util.Map;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * Maps exceptions to RFC 9457 problem details. Extending ResponseEntityExceptionHandler makes
 * Spring Boot's default ProblemDetailsExceptionHandler back off, so all errors share one format.
 */
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    ProblemDetail notFound(NotFoundException ex) {
        return problem(HttpStatus.NOT_FOUND, ex.code(), ex.getMessage());
    }

    @ExceptionHandler(ForbiddenException.class)
    ProblemDetail forbidden(ForbiddenException ex) {
        return problem(HttpStatus.FORBIDDEN, ex.code(), ex.getMessage());
    }

    @ExceptionHandler(ConflictException.class)
    ProblemDetail conflict(ConflictException ex) {
        return problem(HttpStatus.CONFLICT, ex.code(), ex.getMessage());
    }

    @ExceptionHandler(BusinessRuleException.class)
    ProblemDetail businessRule(BusinessRuleException ex) {
        return problem(HttpStatus.UNPROCESSABLE_ENTITY, ex.code(), ex.getMessage());
    }

    @ExceptionHandler(InvalidRequestException.class)
    ProblemDetail invalidRequest(InvalidRequestException ex) {
        return problem(HttpStatus.BAD_REQUEST, ex.code(), ex.getMessage());
    }

    @ExceptionHandler(ObjectOptimisticLockingFailureException.class)
    ProblemDetail concurrentModification(ObjectOptimisticLockingFailureException ex) {
        return problem(HttpStatus.CONFLICT, "CONCURRENT_MODIFICATION",
                "The resource was modified by someone else. Reload and try again.");
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    ProblemDetail integrityViolation(DataIntegrityViolationException ex) {
        // Unique-index races (double join, double reaction) end up here.
        return problem(HttpStatus.CONFLICT, "DUPLICATE", "This action was already performed.");
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
                                                                  HttpHeaders headers,
                                                                  HttpStatusCode status,
                                                                  WebRequest request) {
        ProblemDetail body = ex.getBody();
        body.setProperty("code", "VALIDATION_FAILED");
        List<Map<String, String>> errors = ex.getBindingResult().getFieldErrors().stream()
                .map(fe -> Map.of("field", fe.getField(), "message", String.valueOf(fe.getDefaultMessage())))
                .toList();
        body.setProperty("errors", errors);
        return handleExceptionInternal(ex, body, headers, status, request);
    }

    private static ProblemDetail problem(HttpStatus status, String code, String detail) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(status, detail);
        pd.setTitle(status.getReasonPhrase());
        pd.setProperty("code", code);
        return pd;
    }
}
```

### 6.3 Pagination

```java
package pt.vclubroom.shared.web;

import java.util.List;
import java.util.function.Function;

/** Keyset page: nextCursor is null on the last page. */
public record CursorPage<T>(List<T> items, String nextCursor) {

    public <R> CursorPage<R> map(Function<T, R> mapper) {
        return new CursorPage<>(items.stream().map(mapper).toList(), nextCursor);
    }
}
```

```java
package pt.vclubroom.shared.web;

import java.util.List;

/** Offset page for admin lists and the directory. */
public record PageResponse<T>(List<T> items, int page, int size, long totalElements) {
}
```

```java
package pt.vclubroom.shared.web;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.UUID;
import pt.vclubroom.shared.error.InvalidRequestException;

/**
 * Opaque cursor over (created_at, id), ordered newest first.
 * Timestamps are truncated to microseconds when entities are created (PostgreSQL precision),
 * so cursor comparisons are exact.
 */
public record TimeCursor(Instant createdAt, UUID id) {

    public String encode() {
        String raw = createdAt.toString() + "|" + id;
        return Base64.getUrlEncoder().withoutPadding().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    public static TimeCursor decode(String token) {
        try {
            String raw = new String(Base64.getUrlDecoder().decode(token), StandardCharsets.UTF_8);
            String[] parts = raw.split("\\|", 2);
            return new TimeCursor(Instant.parse(parts[0]), UUID.fromString(parts[1]));
        } catch (RuntimeException e) {
            throw new InvalidRequestException("INVALID_CURSOR", "The pagination cursor is invalid.");
        }
    }
}
```

---

## 7. Module template and conventions

### 7.1 Declaring a module and its public surface

```java
@ApplicationModule(
        displayName = "Membership",
        allowedDependencies = {"shared", "club::api", "club::events", "club::spi", "identity::api"}
)
package pt.vclubroom.membership;

import org.springframework.modulith.ApplicationModule;
```

```java
@NamedInterface("api")
package pt.vclubroom.membership.api;

import org.springframework.modulith.NamedInterface;
```

```java
@NamedInterface("events")
package pt.vclubroom.membership.events;

import org.springframework.modulith.NamedInterface;
```

Every module has the same three kinds of `package-info.java`: one for the module root (allowed dependencies) and one per public package (`api`, `events`, `spi`). Every other package is internal automatically.

### 7.2 Naming

| Kind | Pattern | Example |
|------|---------|---------|
| Controller | `<Resource>Controller`; admin ones `<Resource>AdminController` / `Admin<Resource>Controller` | `ClubController`, `ClubAdminController` |
| Request DTO | `<Verb><Resource>Request` (record, Bean Validation) | `CreateClubRequest` |
| Response DTO | `<Resource>Response` (record) | `ClubResponse` |
| Use-case service | `<Resource>Service` (commands), `<Resource>QueryService` (reads) | `ClubService`, `ClubQueryService` |
| API implementation | `<Api>Service` implementing the `api` interface | `ClubCatalogService implements ClubCatalog` |
| Event | Past tense noun phrase (record) | `ClubApproved` |
| Listener | `<Cause>Listener` / `<Purpose>Projector` | `ClubLifecycleListener`, `ClubCardProjector` |
| Repository | `<Aggregate>Repository` | `ClubRepository` |
| Job | `<Purpose>Job` / `<Purpose>Scheduler` | `OrphanMediaCleanupJob` |
| Properties | `<Module>Properties` (record, `@ConfigurationProperties("app.<module>")`) | `MediaProperties` |

### 7.3 Layer contracts

| Rule | Why |
|------|-----|
| Controllers only translate HTTP ↔ commands and DTOs. No business decisions. | Business logic stays testable without MVC. |
| Every write goes through **one** `@Transactional` application service method. | Clear consistency boundary; the event is stored in the same transaction. |
| Authorization happens at the start of the service method (`ClubAuthorization.require…`, `SpaceAccessPolicy…`). | One place to audit. |
| Entities enforce their own invariants and state transitions (`club.approve(...)` throws if not pending). | Invalid states can't be represented. |
| Entities generate their own UUID and timestamps (truncated to microseconds) in factory methods; `@Version Long version` is `null` until persisted, so Spring Data calls `persist`, not `merge`. | IDs are available for events before flush; optimistic locking for free. |
| Repositories expose only what the module needs: derived queries, `@Query` JPQL, or native SQL for keyset and `SKIP LOCKED`. | |
| Events are records in `events`, carry IDs and minimal facts, and are published with `ApplicationEventPublisher` **inside** the transaction. | The outbox guarantees "state change ⇔ event". |
| Listeners use `@ApplicationModuleListener` (async, after commit, new transaction) and must be **idempotent**. | At-least-once delivery. |

### 7.4 Generic vertical slice (template)

```java
package pt.vclubroom.example.web;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import pt.vclubroom.example.application.ThingService;
import pt.vclubroom.example.application.ThingView;
import pt.vclubroom.shared.security.AuthenticatedUser;

@RestController
@RequestMapping("/api/clubs/{clubId}/things")
class ThingController {

    record CreateThingRequest(@NotBlank String name) { }

    record ThingResponse(UUID id, String name) {
        static ThingResponse from(ThingView view) {
            return new ThingResponse(view.id(), view.name());
        }
    }

    private final ThingService service;

    ThingController(ThingService service) {
        this.service = service;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    ThingResponse create(@AuthenticationPrincipal AuthenticatedUser me,
                         @PathVariable UUID clubId,
                         @Valid @RequestBody CreateThingRequest request) {
        return ThingResponse.from(service.create(me.actor(), clubId, request.name()));
    }
}
```

```java
package pt.vclubroom.example.application;

import java.util.UUID;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import pt.vclubroom.example.domain.Thing;
import pt.vclubroom.example.events.ThingCreated;
import pt.vclubroom.example.persistence.ThingRepository;
import pt.vclubroom.membership.api.ClubAuthorization;
import pt.vclubroom.membership.api.ClubPermission;
import pt.vclubroom.shared.security.Actor;

@Service
public class ThingService {

    private final ThingRepository things;
    private final ClubAuthorization authorization;
    private final ApplicationEventPublisher events;

    public ThingService(ThingRepository things, ClubAuthorization authorization, ApplicationEventPublisher events) {
        this.things = things;
        this.authorization = authorization;
        this.events = events;
    }

    @Transactional
    public ThingView create(Actor actor, UUID clubId, String name) {
        authorization.require(clubId, actor, ClubPermission.CLUB_SETTINGS_MANAGE); // 1. authorize
        Thing thing = Thing.create(clubId, name, actor.userId());                    // 2. domain rules
        things.save(thing);                                                          // 3. persist
        events.publishEvent(new ThingCreated(thing.id(), clubId));                   // 4. announce (outbox)
        return new ThingView(thing.id(), thing.name());                              // 5. return a view
    }
}
```

(`example`, `Thing*` are placeholders that illustrate the template. Real modules follow it exactly; see the club module for a complete, real slice.)

---

## 8. Architecture verification and generated docs

```java
package pt.vclubroom;

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;
import org.springframework.modulith.docs.Documenter;

class ModularityTests {

    private static final ApplicationModules MODULES = ApplicationModules.of(ClubroomApplication.class);

    @Test
    void modulesRespectTheirBoundaries() {
        // Fails on dependency cycles, on access to another module's internal packages,
        // and on dependencies not declared in allowedDependencies.
        MODULES.verify();
    }

    @Test
    void writeArchitectureDocumentation() {
        // Generates PlantUML C4 component diagrams + module canvases into target/spring-modulith-docs
        new Documenter(MODULES)
                .writeModulesAsPlantUml()
                .writeIndividualModulesAsPlantUml()
                .writeModuleCanvases();
    }
}
```

The generated diagrams make a strong slide for the "Scalability / architecture" part of the presentation.

---

## 9. Testing strategy

| Level | Tooling | Scope | Example |
|-------|---------|-------|---------|
| Domain unit tests | JUnit 5, AssertJ | Entities and value objects, no Spring | `Club.approve()` on an archived club throws. |
| Module tests | `@ApplicationModuleTest` + `Scenario` + Testcontainers PostgreSQL | One module bootstrapped alone; other modules' APIs mocked with `@MockitoBean` | Publishing `ClubApproved` creates the founder's owner membership and emits `OwnerAdded`. |
| Web slice tests | `@WebMvcTest` + `spring-security-test` | Controller mapping, validation, status codes | `POST /api/clubs` with blank name → 400 `VALIDATION_FAILED`. |
| Integration tests | `@SpringBootTest` + Testcontainers (PostgreSQL, Redis) | Full flows, migrations, security | Join an `OPEN` club → membership row → `MemberJoined` processed by discovery. |
| Architecture tests | `ModularityTests` | Module boundaries | See §8. |

```java
package pt.vclubroom;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/** Shared containers; @ServiceConnection wires spring.datasource.* and spring.data.redis.* automatically. */
@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

    @Bean
    @ServiceConnection
    PostgreSQLContainer<?> postgres() {
        return new PostgreSQLContainer<>(DockerImageName.parse("postgres:17-alpine"));
    }

    @Bean
    @ServiceConnection(name = "redis")
    GenericContainer<?> redis() {
        return new GenericContainer<>(DockerImageName.parse("redis:8.8-alpine")).withExposedPorts(6379);
    }
}
```

```java
package pt.vclubroom.membership;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.Scenario;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import pt.vclubroom.TestcontainersConfiguration;
import pt.vclubroom.club.api.ClubCatalog;
import pt.vclubroom.club.api.ClubSnapshot;
import pt.vclubroom.club.api.ClubStatus;
import pt.vclubroom.club.api.JoinPolicy;
import pt.vclubroom.club.events.ClubApproved;
import pt.vclubroom.identity.api.UserDirectory;
import pt.vclubroom.membership.events.OwnerAdded;
import pt.vclubroom.membership.persistence.MembershipRepository;

@ApplicationModuleTest
@Import(TestcontainersConfiguration.class)
class ClubLifecycleListenerTests {

    @MockitoBean ClubCatalog clubCatalog;      // from module "club" — mocked, the club module is not started
    @MockitoBean UserDirectory userDirectory;  // from module "identity"

    @Autowired MembershipRepository memberships;

    @Test
    void founderBecomesOwnerWhenClubIsApproved(Scenario scenario) {
        UUID clubId = UUID.randomUUID();
        UUID founderId = UUID.randomUUID();
        given(clubCatalog.findById(clubId)).willReturn(Optional.of(
                new ClubSnapshot(clubId, "chess", "Chess Club", ClubStatus.ACTIVE, JoinPolicy.APPROVAL, 1)));

        scenario.publish(new ClubApproved(clubId, "chess", "Chess Club", founderId, UUID.randomUUID(), 1, Instant.now()))
                .andWaitForEventOfType(OwnerAdded.class)
                .matching(event -> event.clubId().equals(clubId))
                .toArriveAndVerify(event ->
                        assertThat(memberships.findActive(clubId, founderId)).isPresent());
    }
}
```

---

## 10. Module documents

| Module | Document |
|--------|----------|
| identity | [identity.md](identity.md) |
| club | [club.md](club.md) (reference slice with every layer in full) |
| membership | [membership.md](membership.md) |
| group | [group.md](group.md) |
| space | [space.md](space.md) |
| forum | [forum.md](forum.md) |
| media | [media.md](media.md) |
| chat | [chat.md](chat.md) |
| calendar | [calendar.md](calendar.md) |
| notification | [notification.md](notification.md) |
| realtime | [realtime.md](realtime.md) |
| discovery | [discovery.md](discovery.md) |
| history | [history.md](history.md) |

Every module document follows the same structure: **1** Responsibility · **2** Dependencies · **3** Packages · **4** Domain model · **5** Public API · **6** Events · **7** REST endpoints · **8** Request flows · **9** Key implementation · **10** Data · **11** Extension points.
