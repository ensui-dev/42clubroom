# Guide 02a — Authentication (E02)

**Goal:** users stored in `identity.users`; Login with 42 that creates the user on first login and refreshes it afterwards; local password login with a bootstrap admin; logout; the final URL rules; and the full `GET /api/me`.

Backlog: **E02-S01** (T2–T7), **E02-S02**, **E02-S04-T1** (owner A). Time: ~4 h. Design: [identity.md](../../03-backend/identity.md), [07-security §3](../../07-security.md), [04-database §4.1](../../04-database.md).

> Every file in this guide was compiled and tested on top of `UNIX_CLUB/main` (`557dc53`, after PR #17): each step ends with a green `./mvnw verify`, the finished code passes 29 tests, and the curl checks of step 7 were run against it. Paths are relative to `UNIX_CLUB/backend/`.

---

## 0. Before you start

```bash
git switch UNIX_CLUB/main && git pull --ff-only
git switch -c 'UNIX_CLUB/dev/feat(E02)/authentication'
```

Commit after each step: every step ends green, and each has a suggested Conventional Commit message (scope = backlog ID).

### Where the classes go

Today's identity classes sit flat in `pt.vclubroom.identity`. The design splits the module into sub-packages (identity.md §3). This guide moves or replaces every flat class:

| Today (flat `identity/`) | After | Step |
|---|---|---|
| `AdminProperties` | `application/IdentityProperties` | 3 |
| `FortyTwoUserService` | `infrastructure/security/FortyTwoOAuth2UserService` + mapper + provisioning service | 3 |
| `SecurityConfig`, `SpaCsrfTokenRequestHandler` | `infrastructure/security/` | 4 |
| `AuthController`, `MeController` | `web/` | 5 |

```text
identity/
├── api/                       PlatformRole, UserSummary, UserContact, UserDirectory      (public to other modules)
├── events/                    UserRegistered, UserProfileSynced                          (public to other modules)
├── domain/                    User, AuthProvider, UserStatus, FortyTwoProfile
├── persistence/               UserRepository
├── application/               UserDirectoryService, UserProvisioningService, IdentityProperties,
│                              ProvisionedUser, AdminBootstrap
├── infrastructure/security/   SecurityConfig, SpaCsrfTokenRequestHandler, FortyTwoProfileMapper,
│                              FortyTwoOAuth2UserService, ClubroomOAuth2User,
│                              LocalPrincipal, LocalUserDetails, LocalUserDetailsService
└── web/                       AuthController, MeController, dto/MeResponse
```

Only `api` and `events` are visible to other modules (`identity::api`, `identity::events`); `ModularityTests` fails the build if another module reaches into the rest.

### Migration file names

Name a migration with the time you create it, never a time copied from a guide:

```bash
date +%Y%m%d%H%M        # e.g. 202610181030 → V202610181030__create_users.sql
```

Flyway refuses to start when it finds a migration whose version is lower than one already applied in that database, so an old timestamp breaks every teammate's local database.

Use **two** underscores between the version and the description (`V202610181030__create_users.sql`). With one underscore Flyway does not recognise the file and skips it without a word; the app then stops at startup with `Schema-validation: missing table`.

---

## Step 1 — Users table, domain model, repository (E02-S01-T2)

The table from 04-database §4.1, the `User` entity and its repository. `PlatformRole` belongs to `api` (other modules need it) but comes now because `User` uses it.

`src/main/resources/db/migration/identity/V<yyyyMMddHHmm>__create_users.sql`

```sql
-- identity.users: 42 users (auto-provisioned at login) and admin-created local users (docs/04-database.md §4.1).
create table identity.users
(
    id            uuid primary key,
    auth_provider varchar(16)  not null check (auth_provider in ('FORTY_TWO', 'LOCAL')),
    ft_id         bigint unique,
    login         varchar(64)  not null,
    email         varchar(320),
    display_name  varchar(128) not null,
    avatar_url    text,
    password_hash varchar(255),
    platform_role varchar(16)  not null default 'USER' check (platform_role in ('USER', 'ADMIN')),
    status        varchar(16)  not null default 'ACTIVE' check (status in ('ACTIVE', 'DISABLED')),
    ft_pool_year  integer,
    ft_pool_month varchar(16),
    ft_alumni     boolean      not null default false,
    ft_staff      boolean      not null default false,
    created_at    timestamptz  not null,
    updated_at    timestamptz  not null,
    last_login_at timestamptz,
    version       bigint       not null default 0,
    constraint ck_users_provider_fields check (
        (auth_provider = 'FORTY_TWO' and ft_id is not null and password_hash is null) or
        (auth_provider = 'LOCAL' and ft_id is null and password_hash is not null))
);
create unique index ux_users_login on identity.users (lower(login));                       -- BR-23
create index ix_users_admins on identity.users (platform_role) where platform_role = 'ADMIN';
create index ix_users_display_name_trgm on identity.users using gin (lower(display_name) gin_trgm_ops);
```

`src/main/java/pt/vclubroom/identity/api/PlatformRole.java`

```java
package pt.vclubroom.identity.api;

public enum PlatformRole {
    USER,
    ADMIN
}
```

`src/main/java/pt/vclubroom/identity/domain/AuthProvider.java`

```java
package pt.vclubroom.identity.domain;

public enum AuthProvider {
    FORTY_TWO,
    LOCAL
}
```

`src/main/java/pt/vclubroom/identity/domain/UserStatus.java`

```java
package pt.vclubroom.identity.domain;

public enum UserStatus {
    ACTIVE,
    DISABLED
}
```

`src/main/java/pt/vclubroom/identity/domain/FortyTwoProfile.java`

```java
package pt.vclubroom.identity.domain;

import java.util.List;

/** Normalised subset of GET https://api.intra.42.fr/v2/me. */
public record FortyTwoProfile(long ftId,
                              String login,
                              String email,
                              String displayName,
                              String avatarUrl,
                              Integer poolYear,
                              String poolMonth,
                              boolean alumni,
                              boolean staff,
                              List<String> campusNames,
                              List<String> cursusSlugs) {
}
```

`src/main/java/pt/vclubroom/identity/domain/User.java`

```java
package pt.vclubroom.identity.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import pt.vclubroom.identity.api.PlatformRole;

@Entity
@Table(name = "users", schema = "identity")
public class User {

    @Id
    private UUID id;

    @Enumerated(EnumType.STRING)
    @Column(name = "auth_provider", nullable = false)
    private AuthProvider provider;

    @Column(name = "ft_id")
    private Long ftId;

    @Column(nullable = false)
    private String login;

    private String email;

    @Column(name = "display_name", nullable = false)
    private String displayName;

    @Column(name = "avatar_url")
    private String avatarUrl;

    @Column(name = "password_hash")
    private String passwordHash;

    @Enumerated(EnumType.STRING)
    @Column(name = "platform_role", nullable = false)
    private PlatformRole platformRole;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private UserStatus status;

    @Column(name = "ft_pool_year")
    private Integer ftPoolYear;

    @Column(name = "ft_pool_month")
    private String ftPoolMonth;

    @Column(name = "ft_alumni", nullable = false)
    private boolean ftAlumni;

    @Column(name = "ft_staff", nullable = false)
    private boolean ftStaff;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    @Version
    private Long version;   // null until the first save, so Spring Data persists (not merges) new users

    protected User() {
        // JPA
    }

    public static User registerFromFortyTwo(FortyTwoProfile p, Instant now, boolean bootstrapAdmin) {
        User u = new User();
        u.id = UUID.randomUUID();
        u.provider = AuthProvider.FORTY_TWO;
        u.ftId = p.ftId();
        u.login = p.login();
        u.platformRole = bootstrapAdmin ? PlatformRole.ADMIN : PlatformRole.USER;
        u.status = UserStatus.ACTIVE;
        u.createdAt = now.truncatedTo(ChronoUnit.MICROS);
        u.syncFromFortyTwo(p, now);
        return u;
    }

    public static User createLocal(String login, String displayName, String email, String passwordHash,
                                   PlatformRole role, Instant now) {
        User u = new User();
        u.id = UUID.randomUUID();
        u.provider = AuthProvider.LOCAL;
        u.login = login;
        u.displayName = displayName;
        u.email = email;
        u.passwordHash = passwordHash;
        u.platformRole = role;
        u.status = UserStatus.ACTIVE;
        u.createdAt = now.truncatedTo(ChronoUnit.MICROS);
        u.updatedAt = u.createdAt;
        return u;
    }

    public void syncFromFortyTwo(FortyTwoProfile p, Instant now) {
        this.email = p.email();
        this.displayName = p.displayName();
        this.avatarUrl = p.avatarUrl();
        this.ftPoolYear = p.poolYear();
        this.ftPoolMonth = p.poolMonth();
        this.ftAlumni = p.alumni();
        this.ftStaff = p.staff();
        this.updatedAt = now.truncatedTo(ChronoUnit.MICROS);
    }

    public void recordLogin(Instant now) {
        this.lastLoginAt = now.truncatedTo(ChronoUnit.MICROS);
    }

    public void changeRole(PlatformRole role, Instant now) {
        this.platformRole = role;
        this.updatedAt = now.truncatedTo(ChronoUnit.MICROS);
    }

    public void disable(Instant now) {
        this.status = UserStatus.DISABLED;
        this.updatedAt = now.truncatedTo(ChronoUnit.MICROS);
    }

    public void enable(Instant now) {
        this.status = UserStatus.ACTIVE;
        this.updatedAt = now.truncatedTo(ChronoUnit.MICROS);
    }

    public void changePasswordHash(String newHash, Instant now) {
        if (provider != AuthProvider.LOCAL) {
            throw new IllegalStateException("Only local accounts have passwords");
        }
        this.passwordHash = newHash;
        this.updatedAt = now.truncatedTo(ChronoUnit.MICROS);
    }

    public boolean isAdmin() { return platformRole == PlatformRole.ADMIN; }
    public boolean isActive() { return status == UserStatus.ACTIVE; }
    public UUID id() { return id; }
    public String login() { return login; }
    public String email() { return email; }
    public String displayName() { return displayName; }
    public String avatarUrl() { return avatarUrl; }
    public String passwordHash() { return passwordHash; }
    public AuthProvider provider() { return provider; }
    public PlatformRole platformRole() { return platformRole; }
    public UserStatus status() { return status; }
}
```

`src/main/java/pt/vclubroom/identity/persistence/UserRepository.java`

```java
package pt.vclubroom.identity.persistence;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Limit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import pt.vclubroom.identity.api.PlatformRole;
import pt.vclubroom.identity.domain.User;

public interface UserRepository extends JpaRepository<User, UUID> {

    Optional<User> findByFtId(Long ftId);

    boolean existsByLoginIgnoreCase(String login);

    @Query("select u from User u where lower(u.login) = lower(:login) and u.provider = pt.vclubroom.identity.domain.AuthProvider.LOCAL")
    Optional<User> findLocalByLogin(@Param("login") String login);

    List<User> findByIdIn(Collection<UUID> ids);

    @Query("select u.id from User u where u.platformRole = :role and u.status = pt.vclubroom.identity.domain.UserStatus.ACTIVE")
    List<UUID> findIdsByRole(@Param("role") PlatformRole role);

    @Query("""
           select u from User u
           where u.status = pt.vclubroom.identity.domain.UserStatus.ACTIVE
             and (lower(u.login) like lower(concat(:q, '%')) or lower(u.displayName) like lower(concat('%', :q, '%')))
           order by u.login
           """)
    List<User> search(@Param("q") String query, Limit limit);
}
```

Notes:

- `ddl-auto: validate` makes Hibernate compare `User` with the table at startup, so `./mvnw verify` already catches a wrong column name or type.
- `version` stays `null` until the first save. Spring Data uses that to `persist` a new user; with a non-null version it would `merge`, because the UUID is assigned in code.
- `ck_users_provider_fields` enforces in the database what the factories guarantee in code: 42 users have an `ft_id` and no password, local users the opposite.

**Check:** `./mvnw verify` is green and the log shows `Successfully applied 3 migrations`.

**Commit:** `feat(E02-S01-T2): add the users table, user entity and repository`

---

## Step 2 — User directory: `identity.api` (E02-S04-T1)

How other modules look up users (authors, members, notification addresses), plus the `MeResponse` that `/api/me` and the login endpoint return.

`src/main/java/pt/vclubroom/identity/api/UserSummary.java`

```java
package pt.vclubroom.identity.api;

import java.util.UUID;

/** Public, non-sensitive view of a user, safe to show to any logged-in user. */
public record UserSummary(UUID id, String login, String displayName, String avatarUrl) {
}
```

`src/main/java/pt/vclubroom/identity/api/UserContact.java`

```java
package pt.vclubroom.identity.api;

import java.util.UUID;

/** Contact data for notifications. Only the notification module should need it. */
public record UserContact(UUID id, String email, String displayName, boolean active) {
}
```

`src/main/java/pt/vclubroom/identity/api/UserDirectory.java`

```java
package pt.vclubroom.identity.api;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** How other modules look up users. Implemented by identity.application.UserDirectoryService. */
public interface UserDirectory {

    Optional<UserSummary> findById(UUID userId);

    /** Batch lookup used to decorate lists (authors, members). Missing IDs are simply absent. */
    Map<UUID, UserSummary> findByIds(Collection<UUID> userIds);

    Optional<UserContact> contactOf(UUID userId);

    List<UUID> adminIds();
}
```

`src/main/java/pt/vclubroom/identity/web/dto/MeResponse.java`

```java
package pt.vclubroom.identity.web.dto;

import java.util.UUID;

/** Body of GET /api/me and POST /api/auth/login. */
public record MeResponse(UUID id, String login, String displayName, String email,
                         String avatarUrl, String provider, boolean admin) {
}
```

`src/main/java/pt/vclubroom/identity/application/UserDirectoryService.java`

```java
package pt.vclubroom.identity.application;

import java.time.Clock;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import pt.vclubroom.identity.api.PlatformRole;
import pt.vclubroom.identity.api.UserContact;
import pt.vclubroom.identity.api.UserDirectory;
import pt.vclubroom.identity.api.UserSummary;
import pt.vclubroom.identity.domain.User;
import pt.vclubroom.identity.persistence.UserRepository;
import pt.vclubroom.identity.web.dto.MeResponse;
import pt.vclubroom.shared.error.NotFoundException;

/**
 * Other modules use it through the UserDirectory interface (identity.api). The MeResponse methods
 * serve only identity's own controllers; other modules never see MeResponse.
 */
@Service
@Transactional(readOnly = true)
public class UserDirectoryService implements UserDirectory {

    private final UserRepository users;
    private final Clock clock;

    public UserDirectoryService(UserRepository users, Clock clock) {
        this.users = users;
        this.clock = clock;
    }

    @Override
    public Optional<UserSummary> findById(UUID userId) {
        return users.findById(userId).map(UserDirectoryService::summary);
    }

    @Override
    public Map<UUID, UserSummary> findByIds(Collection<UUID> userIds) {
        if (userIds.isEmpty()) {
            return Map.of();
        }
        return users.findByIdIn(userIds).stream()
            .map(UserDirectoryService::summary)
            .collect(Collectors.toMap(UserSummary::id, Function.identity()));
    }

    @Override
    public Optional<UserContact> contactOf(UUID userId) {
        return users.findById(userId).map(u -> new UserContact(u.id(), u.email(), u.displayName(), u.isActive()));
    }

    @Override
    public List<UUID> adminIds() {
        return users.findIdsByRole(PlatformRole.ADMIN);
    }

    public MeResponse requireMe(UUID userId) {
        return users.findById(userId).map(UserDirectoryService::me)
            .orElseThrow(() -> new NotFoundException("USER_NOT_FOUND", "User not found"));
    }

    public MeResponse requireMeByLogin(String login) {
        return users.findLocalByLogin(login).map(UserDirectoryService::me)
            .orElseThrow(() -> new NotFoundException("USER_NOT_FOUND", "User not found"));
    }

    @Transactional
    public void recordLogin(UUID userId) {
        users.findById(userId).ifPresent(u -> u.recordLogin(clock.instant()));
    }

    private static UserSummary summary(User u) {
        return new UserSummary(u.id(), u.login(), u.displayName(), u.avatarUrl());
    }

    private static MeResponse me(User u) {
        return new MeResponse(u.id(), u.login(), u.displayName(), u.email(), u.avatarUrl(),
            u.provider().name(), u.isAdmin());
    }
}
```

**Check:** `./mvnw verify` is green.

**Commit:** `feat(E02-S04-T1): add the user directory api`

---

## Step 3 — Store users at Login with 42 (E02-S01-T3, E02-S01-T4)

Today `FortyTwoUserService` keeps the 42 profile in the session only. From now on, every Login with 42 goes through `UserProvisioningService`, which creates the user at the first login and refreshes the 42 snapshot afterwards.

Delete the two classes this step replaces:

```bash
git rm src/main/java/pt/vclubroom/identity/AdminProperties.java \
       src/main/java/pt/vclubroom/identity/FortyTwoUserService.java
```

`src/main/java/pt/vclubroom/identity/events/UserRegistered.java`

```java
package pt.vclubroom.identity.events;

import java.time.Instant;
import java.util.UUID;

public record UserRegistered(UUID userId, String login, String provider, Instant occurredAt) {
}
```

`src/main/java/pt/vclubroom/identity/events/UserProfileSynced.java`

```java
package pt.vclubroom.identity.events;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** Published at every 42 login with the facts the group module needs to sync campus groups. */
public record UserProfileSynced(UUID userId,
                                String login,
                                Integer poolYear,
                                String poolMonth,
                                List<String> campusNames,
                                List<String> cursusSlugs,
                                boolean alumni,
                                Instant occurredAt) {
}
```

`src/main/java/pt/vclubroom/identity/application/IdentityProperties.java`

```java
package pt.vclubroom.identity.application;

import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** app.admin.* in application.yml (values from APP_ADMIN_BOOTSTRAP_LOGINS and APP_BOOTSTRAP_ADMIN_*). */
@ConfigurationProperties("app.admin")
public record IdentityProperties(String bootstrapLogins,
                                 String bootstrapLocalUsername,
                                 String bootstrapLocalPassword) {

    /** 42 logins that become ADMIN at their first login (R-09), lower-cased. */
    public Set<String> bootstrapLoginSet() {
        if (bootstrapLogins == null || bootstrapLogins.isBlank()) {
            return Set.of();
        }
        return Arrays.stream(bootstrapLogins.split(","))
            .map(String::trim).map(String::toLowerCase).filter(s -> !s.isEmpty())
            .collect(Collectors.toUnmodifiableSet());
    }
}
```

`src/main/java/pt/vclubroom/identity/application/ProvisionedUser.java`

```java
package pt.vclubroom.identity.application;

import java.util.UUID;

public record ProvisionedUser(UUID id, String login, boolean admin, boolean active) {
}
```

`src/main/java/pt/vclubroom/identity/application/UserProvisioningService.java`

```java
package pt.vclubroom.identity.application;

import java.time.Clock;
import java.time.Instant;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import pt.vclubroom.identity.domain.FortyTwoProfile;
import pt.vclubroom.identity.domain.User;
import pt.vclubroom.identity.events.UserProfileSynced;
import pt.vclubroom.identity.events.UserRegistered;
import pt.vclubroom.identity.persistence.UserRepository;
import pt.vclubroom.shared.error.ConflictException;

/** Creates the user at the first Login with 42 and refreshes the 42 snapshot at every later login. */
@Service
public class UserProvisioningService {

    private final UserRepository users;
    private final ApplicationEventPublisher events;
    private final IdentityProperties properties;
    private final Clock clock;

    public UserProvisioningService(UserRepository users, ApplicationEventPublisher events,
                                   IdentityProperties properties, Clock clock) {
        this.users = users;
        this.events = events;
        this.properties = properties;
        this.clock = clock;
    }

    @Transactional
    public ProvisionedUser provisionFromFortyTwo(FortyTwoProfile profile) {
        Instant now = clock.instant();
        User user = users.findByFtId(profile.ftId()).orElse(null);

        if (user == null) {
            if (users.existsByLoginIgnoreCase(profile.login())) {           // BR-23
                throw new ConflictException("LOGIN_TAKEN",
                    "A local account already uses the login " + profile.login() + ". Contact an admin.");
            }
            boolean bootstrapAdmin = properties.bootstrapLoginSet().contains(profile.login().toLowerCase());
            user = User.registerFromFortyTwo(profile, now, bootstrapAdmin);
            events.publishEvent(new UserRegistered(user.id(), user.login(), user.provider().name(), now));
        } else {
            user.syncFromFortyTwo(profile, now);
        }
        user.recordLogin(now);
        users.save(user);

        events.publishEvent(new UserProfileSynced(user.id(), profile.login(), profile.poolYear(),
            profile.poolMonth(), profile.campusNames(), profile.cursusSlugs(), profile.alumni(), now));

        return new ProvisionedUser(user.id(), user.login(), user.isAdmin(), user.isActive());
    }
}
```

`src/main/java/pt/vclubroom/identity/infrastructure/security/FortyTwoProfileMapper.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;
import pt.vclubroom.identity.domain.FortyTwoProfile;

/**
 * Translates the raw /v2/me attribute map into our FortyTwoProfile.
 * Anti-corruption layer: 42's JSON shape never leaks past this class.
 */
@Component
class FortyTwoProfileMapper {

    FortyTwoProfile map(Map<String, Object> a) {
        long ftId = ((Number) a.get("id")).longValue();
        String login = (String) a.get("login");
        String displayName = a.get("displayname") instanceof String s && !s.isBlank() ? s : login;
        return new FortyTwoProfile(
            ftId,
            login,
            (String) a.get("email"),
            displayName,
            avatar(a.get("image")),
            parseInt(a.get("pool_year")),
            (String) a.get("pool_month"),
            Boolean.TRUE.equals(a.get("alumni?")),
            Boolean.TRUE.equals(a.get("staff?")),
            campusNames(a.get("campus")),
            cursusSlugs(a.get("cursus_users")));
    }

    private static String avatar(Object image) {
        if (image instanceof Map<?, ?> img) {
            if (img.get("versions") instanceof Map<?, ?> versions && versions.get("medium") instanceof String medium) {
                return medium;
            }
            if (img.get("link") instanceof String link) {
                return link;
            }
        }
        return null;
    }

    private static Integer parseInt(Object value) {
        if (value instanceof Number n) {
            return n.intValue();
        }
        if (value instanceof String s && !s.isBlank()) {
            return Integer.valueOf(s.trim());
        }
        return null;
    }

    private static List<String> campusNames(Object campus) {
        if (!(campus instanceof Collection<?> list)) {
            return List.of();
        }
        return list.stream()
            .filter(Map.class::isInstance)
            .map(m -> ((Map<?, ?>) m).get("name"))
            .filter(String.class::isInstance)
            .map(String.class::cast)
            .toList();
    }

    private static List<String> cursusSlugs(Object cursusUsers) {
        if (!(cursusUsers instanceof Collection<?> list)) {
            return List.of();
        }
        return list.stream()
            .filter(Map.class::isInstance)
            .map(cu -> ((Map<?, ?>) cu).get("cursus"))
            .filter(Map.class::isInstance)
            .map(c -> ((Map<?, ?>) c).get("slug"))
            .filter(String.class::isInstance)
            .map(String.class::cast)
            .toList();
    }
}
```

`src/main/java/pt/vclubroom/identity/infrastructure/security/ClubroomOAuth2User.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.user.OAuth2User;
import pt.vclubroom.shared.security.AuthenticatedUser;

/**
 * The principal stored in the session after Login with 42.
 * getName() returns our internal UUID, so Spring Session's principal index and STOMP user
 * destinations are keyed by user id. Only minimal attributes are kept (the session lives in Redis).
 */
public final class ClubroomOAuth2User implements OAuth2User, AuthenticatedUser {

    private static final long serialVersionUID = 1L;

    private final UUID userId;
    private final String login;
    private final boolean admin;

    public ClubroomOAuth2User(UUID userId, String login, boolean admin) {
        this.userId = userId;
        this.login = login;
        this.admin = admin;
    }

    @Override
    public UUID userId() { return userId; }

    @Override
    public boolean admin() { return admin; }

    @Override
    public String getName() { return userId.toString(); }

    @Override
    public Map<String, Object> getAttributes() {
        return Map.of("userId", userId.toString(), "login", login);
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return admin
            ? List.of(new SimpleGrantedAuthority("ROLE_USER"), new SimpleGrantedAuthority("ROLE_ADMIN"))
            : List.of(new SimpleGrantedAuthority("ROLE_USER"));
    }
}
```

`src/main/java/pt/vclubroom/identity/infrastructure/security/FortyTwoOAuth2UserService.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import org.springframework.security.oauth2.client.userinfo.DefaultOAuth2UserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserRequest;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserService;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Component;
import pt.vclubroom.identity.application.ProvisionedUser;
import pt.vclubroom.identity.application.UserProvisioningService;
import pt.vclubroom.identity.domain.FortyTwoProfile;
import pt.vclubroom.shared.error.ConflictException;

/**
 * Plugged into oauth2Login().userInfoEndpoint().userService(...) in SecurityConfig.
 * Calls 42's /v2/me (through the default service), then provisions our own user.
 */
@Component
public class FortyTwoOAuth2UserService implements OAuth2UserService<OAuth2UserRequest, OAuth2User> {

    private final DefaultOAuth2UserService delegate = new DefaultOAuth2UserService();
    private final FortyTwoProfileMapper mapper;
    private final UserProvisioningService provisioning;

    public FortyTwoOAuth2UserService(FortyTwoProfileMapper mapper, UserProvisioningService provisioning) {
        this.mapper = mapper;
        this.provisioning = provisioning;
    }

    @Override
    public OAuth2User loadUser(OAuth2UserRequest request) throws OAuth2AuthenticationException {
        OAuth2User raw = delegate.loadUser(request);
        FortyTwoProfile profile = mapper.map(raw.getAttributes());
        ProvisionedUser user;
        try {
            user = provisioning.provisionFromFortyTwo(profile);
        } catch (ConflictException e) {
            throw new OAuth2AuthenticationException(new OAuth2Error("login_conflict"), e.getMessage());
        }
        if (!user.active()) {
            throw new OAuth2AuthenticationException(new OAuth2Error("account_disabled"), "This account is disabled.");
        }
        return new ClubroomOAuth2User(user.id(), user.login(), user.admin());
    }
}
```

Unit test for the mapper (part of E02-S01-T7), with a trimmed real `/v2/me` response:

`src/test/java/pt/vclubroom/identity/infrastructure/security/FortyTwoProfileMapperTests.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.junit.jupiter.api.Test;
import pt.vclubroom.identity.domain.FortyTwoProfile;

class FortyTwoProfileMapperTests {

    /** Trimmed GET https://api.intra.42.fr/v2/me response: real field names and types (pool_year is a string). */
    private static final String ME_JSON = """
        {
          "id": 123456,
          "login": "jdoe",
          "email": "jdoe@student.42lisboa.com",
          "displayname": "John Doe",
          "image": {
            "link": "https://cdn.intra.42.fr/users/abc/jdoe.jpg",
            "versions": {"large": "https://cdn.intra.42.fr/users/abc/large_jdoe.jpg",
                         "medium": "https://cdn.intra.42.fr/users/abc/medium_jdoe.jpg"}
          },
          "pool_month": "september",
          "pool_year": "2023",
          "staff?": false,
          "alumni?": true,
          "campus": [{"id": 38, "name": "Lisboa"}],
          "cursus_users": [{"cursus": {"id": 9, "slug": "c-piscine"}}, {"cursus": {"id": 21, "slug": "42cursus"}}]
        }
        """;

    private final FortyTwoProfileMapper mapper = new FortyTwoProfileMapper();

    @Test
    void mapsTheV2MeResponse() throws Exception {
        FortyTwoProfile p = mapper.map(new ObjectMapper().readValue(ME_JSON, new TypeReference<Map<String, Object>>() { }));

        assertThat(p.ftId()).isEqualTo(123456L);
        assertThat(p.login()).isEqualTo("jdoe");
        assertThat(p.email()).isEqualTo("jdoe@student.42lisboa.com");
        assertThat(p.displayName()).isEqualTo("John Doe");
        assertThat(p.avatarUrl()).isEqualTo("https://cdn.intra.42.fr/users/abc/medium_jdoe.jpg");
        assertThat(p.poolYear()).isEqualTo(2023);
        assertThat(p.poolMonth()).isEqualTo("september");
        assertThat(p.alumni()).isTrue();
        assertThat(p.staff()).isFalse();
        assertThat(p.campusNames()).containsExactly("Lisboa");
        assertThat(p.cursusSlugs()).containsExactly("c-piscine", "42cursus");
    }

    @Test
    void toleratesMissingOptionalFields() {
        FortyTwoProfile p = mapper.map(Map.of("id", 7, "login", "minimal", "displayname", " "));

        assertThat(p.displayName()).isEqualTo("minimal");   // blank display name falls back to the login
        assertThat(p.avatarUrl()).isNull();
        assertThat(p.poolYear()).isNull();
        assertThat(p.campusNames()).isEmpty();
        assertThat(p.cursusSlugs()).isEmpty();
    }
}
```

What changes in behaviour:

- **The session principal is now the internal user UUID**, no longer the 42 login. Spring Session's per-user index and, later, WebSocket user destinations rely on that.
- **Bootstrap 42 admins** (`APP_ADMIN_BOOTSTRAP_LOGINS`) become `ADMIN` at their **first** login only; the old code re-checked at every login. Put your login there before you first log in with 42 against a database.
- **Login clash (BR-23):** a 42 login that equals an existing local account's login is refused (`login_conflict`) instead of silently sharing it.
- The old `SecurityConfig` keeps working in the meantime: it injects "the" `OAuth2UserService` bean, which is now `FortyTwoOAuth2UserService`.

**Check:** `./mvnw verify` is green, including the 2 mapper tests.

**Commit:** `feat(E02-S01): store users at login with 42`

---

## Step 4 — Security configuration and local login classes (E02-S01-T5, E02-S02-T1)

The final URL rules, logout, the password encoder and a dedicated `AuthenticationManager` for local logins. `SecurityConfig` and the CSRF handler move to `infrastructure/security`.

Move the CSRF handler unchanged (only its `package` line changes) and delete the old configuration:

```bash
cd src/main/java/pt/vclubroom/identity
git mv SpaCsrfTokenRequestHandler.java infrastructure/security/
sed -i 's/^package pt.vclubroom.identity;/package pt.vclubroom.identity.infrastructure.security;/' \
    infrastructure/security/SpaCsrfTokenRequestHandler.java          # macOS: sed -i ''
git rm SecurityConfig.java
cd -
```

`src/main/java/pt/vclubroom/identity/infrastructure/security/SecurityConfig.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.logout.HttpStatusReturningLogoutSuccessHandler;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.util.matcher.RequestMatcher;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
class SecurityConfig {

    /** API and WebSocket calls get a 401 instead of a redirect to the 42 login page. */
    private static final RequestMatcher API_OR_WS = request -> {
        String uri = request.getRequestURI();
        return uri.startsWith("/api/") || uri.equals("/ws") || uri.startsWith("/ws/");
    };

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http,
                                            FortyTwoOAuth2UserService fortyTwoUserService,
                                            SecurityContextRepository securityContextRepository) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**", "/api/auth/login", "/api/auth/csrf").permitAll()
                .requestMatchers("/oauth2/**", "/login/oauth2/**").permitAll()
                .requestMatchers("/ical/**").permitAll()                         // token is the credential
                .requestMatchers("/error", "/actuator/health/**", "/actuator/info").permitAll()
                .requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll() // disabled in prod
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/**", "/ws", "/ws/**").authenticated()
                .anyRequest().denyAll())
            .securityContext(ctx -> ctx.securityContextRepository(securityContextRepository))
            // SPA-friendly CSRF: the XSRF-TOKEN cookie is readable by the frontend and echoed in X-XSRF-TOKEN.
            .csrf(csrf -> csrf
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
                .csrfTokenRequestHandler(new SpaCsrfTokenRequestHandler()))
            .oauth2Login(oauth -> oauth
                .userInfoEndpoint(userInfo -> userInfo.userService(fortyTwoUserService))
                .defaultSuccessUrl("/", true)
                .failureUrl("/login?error"))
            .logout(logout -> logout
                .logoutUrl("/api/auth/logout")                                   // POST + CSRF
                .logoutSuccessHandler(new HttpStatusReturningLogoutSuccessHandler(HttpStatus.NO_CONTENT))
                .deleteCookies("SESSION"))
            .exceptionHandling(ex -> ex
                .defaultAuthenticationEntryPointFor(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED), API_OR_WS))
            .formLogin(AbstractHttpConfigurer::disable)
            .httpBasic(AbstractHttpConfigurer::disable);
        return http.build();
    }

    @Bean
    SecurityContextRepository securityContextRepository() {
        return new HttpSessionSecurityContextRepository();     // backed by Spring Session → Redis
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();   // {bcrypt} by default
    }

    /** Checks local username/password logins (AuthController). 42 logins go through oauth2Login above. */
    @Bean
    AuthenticationManager localAuthenticationManager(LocalUserDetailsService userDetailsService,
                                                     PasswordEncoder passwordEncoder) {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider(userDetailsService);
        provider.setPasswordEncoder(passwordEncoder);
        return new ProviderManager(provider);
    }
}
```

`src/main/java/pt/vclubroom/identity/infrastructure/security/LocalPrincipal.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import java.util.UUID;
import org.springframework.security.core.AuthenticatedPrincipal;
import pt.vclubroom.shared.security.AuthenticatedUser;

/** Principal stored in the session after a local login. getName() = internal UUID. */
public record LocalPrincipal(UUID userId, String login, boolean admin)
    implements AuthenticatedPrincipal, AuthenticatedUser {

    private static final long serialVersionUID = 1L;

    @Override
    public String getName() {
        return userId.toString();
    }
}
```

`src/main/java/pt/vclubroom/identity/infrastructure/security/LocalUserDetails.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

/** Only used during authentication (password check); replaced by LocalPrincipal afterwards. */
record LocalUserDetails(UUID userId, String login, String passwordHash, boolean admin, boolean active)
    implements UserDetails {

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return admin
            ? List.of(new SimpleGrantedAuthority("ROLE_USER"), new SimpleGrantedAuthority("ROLE_ADMIN"))
            : List.of(new SimpleGrantedAuthority("ROLE_USER"));
    }

    @Override public String getPassword() { return passwordHash; }
    @Override public String getUsername() { return login; }
    @Override public boolean isEnabled() { return active; }   // DISABLED accounts cannot log in (BR-24)
}
```

`src/main/java/pt/vclubroom/identity/infrastructure/security/LocalUserDetailsService.java`

```java
package pt.vclubroom.identity.infrastructure.security;

import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Component;
import pt.vclubroom.identity.persistence.UserRepository;

/** Loads LOCAL accounts only: a 42 user can never log in with a password. */
@Component
class LocalUserDetailsService implements UserDetailsService {

    private final UserRepository users;

    LocalUserDetailsService(UserRepository users) {
        this.users = users;
    }

    @Override
    public UserDetails loadUserByUsername(String username) {
        return users.findLocalByLogin(username)
            .map(u -> new LocalUserDetails(u.id(), u.login(), u.passwordHash(), u.isAdmin(), u.isActive()))
            .orElseThrow(() -> new UsernameNotFoundException("Unknown local user"));
    }
}
```

The URL rules, in the order Spring evaluates them (first match wins):

| Pattern | Rule | Why |
|---|---|---|
| `/api/public/**`, `/api/auth/login`, `/api/auth/csrf` | everyone | Landing page data and the login itself |
| `/oauth2/**`, `/login/oauth2/**` | everyone | Login with 42 start and callback |
| `/ical/**` | everyone | The token in the URL is the credential (calendar feeds) |
| `/error`, `/actuator/health/**`, `/actuator/info` | everyone | Error rendering and health checks |
| `/v3/api-docs/**`, Swagger UI | everyone | Turned off in the prod profile |
| `/api/admin/**` | `ROLE_ADMIN` | Admin console |
| `/api/**`, `/ws`, `/ws/**` | logged in | Everything else of the API (401 instead of a redirect) |
| anything else | **denied** | Nothing unplanned is reachable |

Three differences from the 07-security §3 snippet, all deliberate:

1. `new DaoAuthenticationProvider(userDetailsService)` + `setPasswordEncoder(...)`: the constructor taking a `PasswordEncoder` and `setUserDetailsService` are deprecated in Spring Security 6.5.
2. `/error` is permitted (kept from the current configuration): with `denyAll` as the default, Spring Boot's error rendering would otherwise turn every error into a 403.
3. `@EnableMethodSecurity` is kept from the current configuration.

The application class no longer needs to exclude `UserDetailsServiceAutoConfiguration`: Spring Boot backs off by itself now that `LocalUserDetailsService` and an `AuthenticationManager` exist. Replace the file with:

`src/main/java/pt/vclubroom/ClubroomApplication.java`

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

**Check:** `./mvnw verify` is green. The existing tests now run against the new rules: `/api/me` without a session is 401, health and API docs are public, the CSRF cookie and header checks pass.

**Commit:** `feat(E02-S01-T5): add the final security rules, logout and local authentication`

---

## Step 5 — Login endpoint, full `/api/me`, bootstrap admin (E02-S01-T6, E02-S02-T2, E02-S02-T3)

Delete the two flat controllers; their replacements live in `web/`:

```bash
git rm src/main/java/pt/vclubroom/identity/AuthController.java \
       src/main/java/pt/vclubroom/identity/MeController.java
```

`src/main/java/pt/vclubroom/identity/web/AuthController.java`

```java
package pt.vclubroom.identity.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.context.SecurityContextHolderStrategy;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.web.authentication.session.ChangeSessionIdAuthenticationStrategy;
import org.springframework.security.web.authentication.session.SessionAuthenticationStrategy;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import pt.vclubroom.identity.application.UserDirectoryService;
import pt.vclubroom.identity.infrastructure.security.LocalPrincipal;
import pt.vclubroom.identity.web.dto.MeResponse;

@RestController
@RequestMapping("/api/auth")
class AuthController {

    record LoginRequest(@NotBlank String username, @NotBlank String password) { }

    private final AuthenticationManager localAuthenticationManager;
    private final SecurityContextRepository securityContextRepository;
    private final UserDirectoryService userDirectory;
    private final SessionAuthenticationStrategy sessionStrategy = new ChangeSessionIdAuthenticationStrategy();
    private final SecurityContextHolderStrategy contextHolder = SecurityContextHolder.getContextHolderStrategy();

    AuthController(@Qualifier("localAuthenticationManager") AuthenticationManager localAuthenticationManager,
                   SecurityContextRepository securityContextRepository,
                   UserDirectoryService userDirectory) {
        this.localAuthenticationManager = localAuthenticationManager;
        this.securityContextRepository = securityContextRepository;
        this.userDirectory = userDirectory;
    }

    /** Called once by the SPA at startup; the CSRF handler writes the XSRF-TOKEN cookie on the response. */
    @GetMapping("/csrf")
    ResponseEntity<Void> csrf() {
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/login")
    MeResponse login(@Valid @RequestBody LoginRequest body, HttpServletRequest request, HttpServletResponse response) {
        Authentication checked = localAuthenticationManager.authenticate(
            UsernamePasswordAuthenticationToken.unauthenticated(body.username(), body.password()));

        UserDetails details = (UserDetails) checked.getPrincipal();
        MeResponse me = userDirectory.requireMeByLogin(details.getUsername());
        LocalPrincipal principal = new LocalPrincipal(me.id(), me.login(), me.admin());
        Authentication authenticated =
            UsernamePasswordAuthenticationToken.authenticated(principal, null, checked.getAuthorities());

        sessionStrategy.onAuthentication(authenticated, request, response);   // session fixation protection
        SecurityContext context = contextHolder.createEmptyContext();
        context.setAuthentication(authenticated);
        contextHolder.setContext(context);
        securityContextRepository.saveContext(context, request, response);   // persisted to the Redis session
        userDirectory.recordLogin(me.id());
        return me;
    }

    /** Same answer for unknown user, wrong password and disabled account: no account enumeration. */
    @ExceptionHandler(AuthenticationException.class)
    ProblemDetail badCredentials(AuthenticationException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.UNAUTHORIZED, "Invalid username or password.");
        pd.setProperty("code", "INVALID_CREDENTIALS");
        return pd;
    }
}
```

`src/main/java/pt/vclubroom/identity/web/MeController.java`

```java
package pt.vclubroom.identity.web;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import pt.vclubroom.identity.application.UserDirectoryService;
import pt.vclubroom.identity.web.dto.MeResponse;
import pt.vclubroom.shared.security.AuthenticatedUser;

@RestController
@RequestMapping("/api/me")
class MeController {

    private final UserDirectoryService userDirectory;

    MeController(UserDirectoryService userDirectory) {
        this.userDirectory = userDirectory;
    }

    /** Both principals (42 and local) implement AuthenticatedUser, so this works for every login type. */
    @GetMapping
    MeResponse me(@AuthenticationPrincipal AuthenticatedUser me) {
        return userDirectory.requireMe(me.userId());
    }
}
```

`src/main/java/pt/vclubroom/identity/application/AdminBootstrap.java`

```java
package pt.vclubroom.identity.application;

import java.time.Clock;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import pt.vclubroom.identity.api.PlatformRole;
import pt.vclubroom.identity.domain.User;
import pt.vclubroom.identity.persistence.UserRepository;

/** Creates the bootstrap local admin once, if APP_BOOTSTRAP_ADMIN_USERNAME/PASSWORD are set (R-09). */
@Component
class AdminBootstrap implements ApplicationRunner {

    private final UserRepository users;
    private final PasswordEncoder passwordEncoder;
    private final IdentityProperties properties;
    private final Clock clock;

    AdminBootstrap(UserRepository users, PasswordEncoder passwordEncoder, IdentityProperties properties, Clock clock) {
        this.users = users;
        this.passwordEncoder = passwordEncoder;
        this.properties = properties;
        this.clock = clock;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        String username = properties.bootstrapLocalUsername();
        String password = properties.bootstrapLocalPassword();
        if (username == null || username.isBlank() || password == null || password.isBlank()) {
            return;
        }
        if (users.existsByLoginIgnoreCase(username)) {
            return;   // created on an earlier start; changing the env var later does not reset the password
        }
        users.save(User.createLocal(username, "Administrator", null,
            passwordEncoder.encode(password), PlatformRole.ADMIN, clock.instant()));
    }
}
```

`ClubroomApplicationTests.currentUserExposesLoginAndRoles` asserts the old `{login, roles}` body, so delete that test method and the imports only it used (step 6 replaces it with real login tests):

```java
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.oauth2Login;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import java.util.Map;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.user.DefaultOAuth2User;
import org.springframework.security.oauth2.core.user.OAuth2User;
```

Notes:

- The login endpoint answers **the same 401 `INVALID_CREDENTIALS`** for an unknown user, a wrong password and a disabled account, so nobody can probe which accounts exist.
- `ChangeSessionIdAuthenticationStrategy` gives the session a new id at login (session fixation protection); the context is then saved explicitly, because Spring Security 6 no longer saves it automatically for hand-written login endpoints.
- `AdminBootstrap` creates the local admin **once**. Changing `APP_BOOTSTRAP_ADMIN_PASSWORD` later does not change an existing admin's password, so set the real password before the first start of a database that matters (the demo).

**Check:** `./mvnw verify` is green.

**Commit:** `feat(E02-S02): add the local login endpoint, full /api/me and bootstrap admin`

---

## Step 6 — Tests (E02-S02-T4, E02-S01-T7)

Both classes use the same three annotations as `ClubroomApplicationTests`, so Spring reuses its cached context and containers (about 2 s extra in total).

`src/test/java/pt/vclubroom/identity/IdentityIntegrationTests.java`

```java
package pt.vclubroom.identity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.oauth2Login;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import jakarta.servlet.http.Cookie;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import pt.vclubroom.TestcontainersConfiguration;
import pt.vclubroom.identity.api.PlatformRole;
import pt.vclubroom.identity.application.ProvisionedUser;
import pt.vclubroom.identity.application.UserProvisioningService;
import pt.vclubroom.identity.domain.FortyTwoProfile;
import pt.vclubroom.identity.domain.User;
import pt.vclubroom.identity.infrastructure.security.ClubroomOAuth2User;
import pt.vclubroom.identity.persistence.UserRepository;
import pt.vclubroom.shared.error.ConflictException;

/**
 * Same annotations as ClubroomApplicationTests, so Spring reuses its cached context and containers.
 * Every test creates its own users with unique logins because the database is shared across tests.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class IdentityIntegrationTests {

    private static final String PASSWORD = "correct horse battery staple";

    @Autowired
    MockMvc mvc;

    @Autowired
    UserRepository users;

    @Autowired
    PasswordEncoder passwordEncoder;

    @Autowired
    UserProvisioningService provisioning;

    @Test
    void localLoginStartsASessionThatMeAndLogoutUse() throws Exception {
        User admin = localUser("admin", PlatformRole.ADMIN);

        Cookie session = login(admin.login(), PASSWORD)
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(admin.id().toString()))
            .andExpect(jsonPath("$.provider").value("LOCAL"))
            .andExpect(jsonPath("$.admin").value(true))
            .andReturn().getResponse().getCookie("SESSION");
        assertThat(session).isNotNull();

        mvc.perform(get("/api/me").cookie(session))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.login").value(admin.login()))
            .andExpect(jsonPath("$.displayName").value("Test admin"));

        String xsrf = xsrfToken();
        mvc.perform(post("/api/auth/logout").cookie(session, new Cookie("XSRF-TOKEN", xsrf)).header("X-XSRF-TOKEN", xsrf))
            .andExpect(status().isNoContent());

        mvc.perform(get("/api/me").cookie(session))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void wrongPasswordUnknownUserAndDisabledAccountAllGetTheSame401() throws Exception {
        User active = localUser("active", PlatformRole.USER);
        User disabled = localUser("disabled", PlatformRole.USER);
        disabled.disable(Instant.now());
        users.save(disabled);

        for (String[] attempt : new String[][] {
            {active.login(), "wrong password"}, {"nobody-" + suffix(), PASSWORD}, {disabled.login(), PASSWORD}}) {
            login(attempt[0], attempt[1])
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
        }
    }

    @Test
    void adminUrlsNeedTheAdminRole() throws Exception {
        Cookie member = sessionOf(localUser("member", PlatformRole.USER));
        Cookie admin = sessionOf(localUser("boss", PlatformRole.ADMIN));

        mvc.perform(get("/api/admin/users").cookie(member)).andExpect(status().isForbidden());
        // The admin passes the URL rule; 404 only because no admin endpoint exists yet.
        mvc.perform(get("/api/admin/users").cookie(admin)).andExpect(status().isNotFound());
    }

    @Test
    void loginWith42ProvisionsTheUserOnceAndMeReturnsIt() throws Exception {
        long ftId = ThreadLocalRandom.current().nextLong(1, Long.MAX_VALUE);
        String login = "ft-" + suffix();

        ProvisionedUser first = provisioning.provisionFromFortyTwo(profile(ftId, login, "First Name"));
        ProvisionedUser again = provisioning.provisionFromFortyTwo(profile(ftId, login, "Renamed At 42"));
        assertThat(again.id()).isEqualTo(first.id());   // same row, profile refreshed

        mvc.perform(get("/api/me").with(oauth2Login().oauth2User(new ClubroomOAuth2User(first.id(), login, false))))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.provider").value("FORTY_TWO"))
            .andExpect(jsonPath("$.displayName").value("Renamed At 42"))
            .andExpect(jsonPath("$.admin").value(false));
    }

    @Test
    void a42LoginCannotTakeTheLoginOfALocalAccount() {
        User local = localUser("taken", PlatformRole.USER);
        FortyTwoProfile clash = profile(ThreadLocalRandom.current().nextLong(1, Long.MAX_VALUE),
            local.login().toUpperCase(), "Clash");   // BR-23 compares logins case-insensitively

        assertThatThrownBy(() -> provisioning.provisionFromFortyTwo(clash))
            .isInstanceOfSatisfying(ConflictException.class, e -> assertThat(e.code()).isEqualTo("LOGIN_TAKEN"));
    }

    @Test
    void loginWith42RedirectsToThe42AuthorizeEndpointWithOurCallback() throws Exception {
        mvc.perform(get("/oauth2/authorization/fortytwo"))
            .andExpect(status().is3xxRedirection())
            .andExpect(header().string("Location", startsWith("https://api.intra.42.fr/oauth/authorize?")))
            // app.public-url defaults to the Vite dev server, which proxies the callback to the backend
            .andExpect(header().string("Location",
                containsString("redirect_uri=http://localhost:5173/login/oauth2/code/fortytwo")));
    }

    private User localUser(String prefix, PlatformRole role) {
        String login = prefix + "-" + suffix();
        return users.save(User.createLocal(login, "Test " + prefix, login + "@example.test",
            passwordEncoder.encode(PASSWORD), role, Instant.now()));
    }

    private static FortyTwoProfile profile(long ftId, String login, String displayName) {
        return new FortyTwoProfile(ftId, login, login + "@student.42lisboa.com", displayName, null,
            2023, "september", false, false, List.of("Lisboa"), List.of("42cursus"));
    }

    /** What the SPA does: GET /api/auth/csrf, then send the cookie back with its value in X-XSRF-TOKEN. */
    private ResultActions login(String username, String password) throws Exception {
        String xsrf = xsrfToken();
        return mvc.perform(post("/api/auth/login")
            .cookie(new Cookie("XSRF-TOKEN", xsrf))
            .header("X-XSRF-TOKEN", xsrf)
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"username\":\"%s\",\"password\":\"%s\"}".formatted(username, password)));
    }

    private Cookie sessionOf(User user) throws Exception {
        return login(user.login(), PASSWORD).andExpect(status().isOk()).andReturn().getResponse().getCookie("SESSION");
    }

    private String xsrfToken() throws Exception {
        return mvc.perform(get("/api/auth/csrf")).andReturn().getResponse().getCookie("XSRF-TOKEN").getValue();
    }

    private static String suffix() {
        return UUID.randomUUID().toString().substring(0, 8);
    }
}
```

`src/test/java/pt/vclubroom/identity/application/AdminBootstrapTests.java`

```java
package pt.vclubroom.identity.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.security.crypto.password.PasswordEncoder;
import pt.vclubroom.TestcontainersConfiguration;
import pt.vclubroom.identity.domain.User;
import pt.vclubroom.identity.persistence.UserRepository;

/** Same annotations as ClubroomApplicationTests, so Spring reuses its cached context and containers. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class AdminBootstrapTests {

    @Autowired
    UserRepository users;

    @Autowired
    PasswordEncoder passwordEncoder;

    @Autowired
    Clock clock;

    @Test
    void createsTheLocalAdminOnceAndNeverResetsItsPassword() {
        String login = "bootstrap-" + UUID.randomUUID().toString().substring(0, 8);

        bootstrap(login, "first-password");
        User admin = users.findLocalByLogin(login).orElseThrow();
        assertThat(admin.isAdmin()).isTrue();
        assertThat(passwordEncoder.matches("first-password", admin.passwordHash())).isTrue();

        bootstrap(login, "changed-in-env-later");   // next start with another password in .env
        assertThat(passwordEncoder.matches("first-password",
            users.findLocalByLogin(login).orElseThrow().passwordHash())).isTrue();
    }

    @Test
    void doesNothingWithoutCredentials() {
        long before = users.count();
        bootstrap("", "");
        assertThat(users.count()).isEqualTo(before);
    }

    private void bootstrap(String username, String password) {
        new AdminBootstrap(users, passwordEncoder, new IdentityProperties(null, username, password), clock).run(null);
    }
}
```

| Test | Proves |
|---|---|
| `localLoginStartsASessionThatMeAndLogoutUse` | CSRF cookie → login → `SESSION` cookie → `/api/me` → logout → session gone (401) |
| `wrongPasswordUnknownUserAndDisabledAccountAllGetTheSame401` | No account enumeration; disabled accounts cannot log in (BR-24) |
| `adminUrlsNeedTheAdminRole` | `/api/admin/**`: 403 for a member, rule passed for an admin |
| `loginWith42ProvisionsTheUserOnceAndMeReturnsIt` | First login creates, second login refreshes the same row; `/api/me` for a 42 principal |
| `a42LoginCannotTakeTheLoginOfALocalAccount` | BR-23 (case-insensitive) |
| `loginWith42RedirectsToThe42AuthorizeEndpointWithOurCallback` | Registration id `fortytwo`, 42 authorize URL, callback on `app.public-url` |
| `AdminBootstrapTests` | Admin created once, password never reset, nothing without credentials |

**Check:** `./mvnw verify` reports **29 tests, 0 failures**: ClubroomApplicationTests 5, IdentityIntegrationTests 6, AdminBootstrapTests 2, FortyTwoProfileMapperTests 2, GlobalExceptionHandlerTests 7, TimeCursorTests 5, ModularityTests 2.

**Commit:** `test(E02-S02-T4): cover local login, logout, the admin rule and 42 provisioning`

---

## Step 7 — Manual checks ("Done when")

1. **Clear the old dev sessions.** Sessions created before step 3 hold the old principal type, and `/api/me` fails with a 500 for them:

   ```bash
   cd UNIX_CLUB && docker compose -f compose.yaml -f compose.dev.yaml exec redis redis-cli FLUSHALL
   ```

2. **Start the backend** with `./run-dev.sh`. On the first start Flyway applies your users migration and `AdminBootstrap` creates the local admin from `APP_BOOTSTRAP_ADMIN_USERNAME` / `APP_BOOTSTRAP_ADMIN_PASSWORD` in `.env`.

3. **Local login with curl** (replace the password with yours):

   ```bash
   B=localhost:8080; JAR=$(mktemp)
   curl -s -c "$JAR" -b "$JAR" -o /dev/null $B/api/auth/csrf                      # sets XSRF-TOKEN
   XSRF=$(awk '$6=="XSRF-TOKEN"{print $7}' "$JAR")
   curl -s -c "$JAR" -b "$JAR" -H "X-XSRF-TOKEN: $XSRF" -H 'Content-Type: application/json' \
        -d '{"username":"admin","password":"change-me-admin"}' $B/api/auth/login | jq   # provider LOCAL, admin true
   curl -s -b "$JAR" $B/api/me | jq                                                 # same user
   curl -s -o /dev/null -w '%{http_code}\n' $B/api/me                                # 401 without the session
   XSRF=$(awk '$6=="XSRF-TOKEN"{print $7}' "$JAR")
   curl -s -c "$JAR" -b "$JAR" -X POST -H "X-XSRF-TOKEN: $XSRF" -o /dev/null -w '%{http_code}\n' $B/api/auth/logout   # 204
   curl -s -b "$JAR" -o /dev/null -w '%{http_code}\n' $B/api/me                      # 401 again
   ```

4. **Login with 42 through the Vite dev server**, before the login page exists (E02-S03). Requirements: `npm run dev` running in `UNIX_CLUB/frontend`, real `FT_CLIENT_ID` / `FT_CLIENT_SECRET` in `.env`, and `http://localhost:5173/login/oauth2/code/fortytwo` registered on the 42 app.
   1. Open <http://localhost:5173/oauth2/authorization/fortytwo> and log in at 42.
   2. You land on `http://localhost:5173/`.
   3. Open <http://localhost:5173/api/me>: your user, `"provider": "FORTY_TWO"`.

   If it fails: "The redirect uri included is not valid" at 42 means the callback URL is not registered. Landing on `/login?error` means the backend refused the login; its log says why (`login_conflict`: a local account has the same login; `account_disabled`).

5. **Frontend types:** `/api/me` has a new body, so regenerate the client types with `npm run api:types` in `UNIX_CLUB/frontend` (backend running) and commit `schema.d.ts`.

---

## Done when

- [ ] `./mvnw verify` green with 29 tests.
- [ ] Local login, `/api/me` and logout work with curl; `/api/me` is 401 without a session.
- [ ] Login with 42 through `http://localhost:5173` creates your user; `/api/me` shows `FORTY_TWO`.
- [ ] `schema.d.ts` regenerated.

Next: **E02-S03** (login page, `useMe`, route guards, user menu; guide 03 §7) and **E02-S04-T2** (`GET /api/users` search). Admin user management (`LocalAccountService`, `SessionRevocationService`, identity.md §9.7) comes with the admin console stories.
