# Module `history`

## 1. Responsibility

- The **club timeline**: a chronological, human-readable record of a club's lifecycle facts. Creation requested, founded (era 1), owners added, stepped down or removed, archived (era *n* ended), revived (era *n+1*).
- Read model built from domain events, idempotent and rebuildable.

### How "Club history (all previous posts and comments)" is satisfied

The lifecycle requirement is met by several modules working together. This module adds only the timeline.

| Part of history | Where it lives |
|-----------------|----------------|
| All posts and comments ever written | `forum`: nothing is hard-deleted (BR-16); every post carries its `era`; `GET /api/channels/{id}/posts?era=n` |
| All chat messages | `chat`: kept forever (D-23), era-stamped, `?era=n` |
| Archived clubs remain readable | `space` access policy: archived = read-only, never hidden |
| Eras (who ran the club when) | `club`: `GET /api/clubs/{id}/eras` |
| Lifecycle story | **`history`**: `GET /api/clubs/{id}/timeline` |

In the UI, the **History tab** of a club combines an era selector (club), the timeline (history) and the feed filtered by era (forum). See [08-frontend.md](../08-frontend.md#9-key-ux-flows).

## 2. Dependencies

| Direction | Modules |
|-----------|---------|
| Depends on | `shared`, `club::events`, `membership::events`, `identity::api` |
| Used by | — |

```java
@ApplicationModule(
        displayName = "History",
        allowedDependencies = {"shared", "club::events", "membership::events", "identity::api"}
)
package pt.vclubroom.history;

import org.springframework.modulith.ApplicationModule;
```

## 3. Packages

```text
history/
├── web/            TimelineController (+ dto/)
├── application/    TimelineProjector, TimelineQueryService
├── domain/         TimelineEntry, TimelineEntryType
└── persistence/    TimelineEntryRepository
```

## 4. Read model

| Column | Notes |
|--------|-------|
| `id` | UUID |
| `club_id`, `era` | Era at the time of the fact (0 while pending) |
| `type` | `CREATION_REQUESTED`, `FOUNDED`, `OWNER_ADDED`, `OWNER_STEPPED_DOWN`, `OWNER_REMOVED`, `ARCHIVED`, `REVIVED` |
| `actor_id`, `subject_id` | Who did it / who it concerns (resolved to names at read time via `UserDirectory`) |
| `data` | `jsonb` (e.g. archival reason, revival request ID) |
| `occurred_at` | From the event |
| `dedup_key` | Unique per club, built from the event identity, so redelivery is a no-op |

Calendar events are **not** part of the timeline, because they can be restricted to private spaces (see [02-architecture.md](../02-architecture.md#41-modules)).

## 5. REST endpoints

| Method | Path | Authorization | Description |
|--------|------|---------------|-------------|
| `GET` | `/api/clubs/{clubId}/timeline?cursor=&limit=30` | user | Newest first, keyset pagination, actor/subject resolved to `UserSummary` |

## 6. Key implementation

```java
package pt.vclubroom.history.domain;

public enum TimelineEntryType {
    CREATION_REQUESTED,
    FOUNDED,
    OWNER_ADDED,
    OWNER_STEPPED_DOWN,
    OWNER_REMOVED,
    ARCHIVED,
    REVIVED
}
```

```java
package pt.vclubroom.history.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.springframework.modulith.events.ApplicationModuleListener;
import org.springframework.stereotype.Component;
import pt.vclubroom.club.events.ClubApproved;
import pt.vclubroom.club.events.ClubArchived;
import pt.vclubroom.club.events.ClubCreationRequested;
import pt.vclubroom.club.events.ClubRevived;
import pt.vclubroom.history.domain.TimelineEntryType;
import pt.vclubroom.history.persistence.TimelineEntryRepository;
import pt.vclubroom.membership.events.OwnerAdded;
import pt.vclubroom.membership.events.OwnerRemoved;
import pt.vclubroom.membership.events.OwnerSteppedDown;

@Component
class TimelineProjector {

    private final TimelineEntryRepository entries;
    private final ObjectMapper objectMapper;

    TimelineProjector(TimelineEntryRepository entries, ObjectMapper objectMapper) {
        this.entries = entries;
        this.objectMapper = objectMapper;
    }

    @ApplicationModuleListener
    void on(ClubCreationRequested e) {
        record(e.clubId(), 0, TimelineEntryType.CREATION_REQUESTED, e.founderId(), e.founderId(), Map.of(),
                e.occurredAt(), "CREATION_REQUESTED:" + e.clubId());
    }

    @ApplicationModuleListener
    void on(ClubApproved e) {
        record(e.clubId(), e.era(), TimelineEntryType.FOUNDED, e.approvedBy(), e.founderId(), Map.of(),
                e.occurredAt(), "FOUNDED:" + e.clubId());
    }

    @ApplicationModuleListener
    void on(ClubArchived e) {
        record(e.clubId(), e.endedEra(), TimelineEntryType.ARCHIVED, e.archivedBy(), null,
                Map.of("reason", e.reason() == null ? "" : e.reason()), e.occurredAt(),
                "ARCHIVED:" + e.clubId() + ":" + e.endedEra());
    }

    @ApplicationModuleListener
    void on(ClubRevived e) {
        record(e.clubId(), e.newEra(), TimelineEntryType.REVIVED, e.approvedBy(), e.newOwnerId(),
                Map.of("requestId", e.requestId().toString()), e.occurredAt(), "REVIVED:" + e.clubId() + ":" + e.newEra());
    }

    @ApplicationModuleListener
    void on(OwnerAdded e) {
        record(e.clubId(), null, TimelineEntryType.OWNER_ADDED, e.by(), e.userId(), Map.of("reason", e.reason()),
                e.occurredAt(), "OWNER_ADDED:" + e.clubId() + ":" + e.userId() + ":" + e.occurredAt());
    }

    @ApplicationModuleListener
    void on(OwnerSteppedDown e) {
        record(e.clubId(), null, TimelineEntryType.OWNER_STEPPED_DOWN, e.userId(), e.userId(), Map.of(),
                e.occurredAt(), "OWNER_STEPPED_DOWN:" + e.clubId() + ":" + e.userId() + ":" + e.occurredAt());
    }

    @ApplicationModuleListener
    void on(OwnerRemoved e) {
        record(e.clubId(), null, TimelineEntryType.OWNER_REMOVED, e.by(), e.userId(), Map.of("reason", e.reason()),
                e.occurredAt(), "OWNER_REMOVED:" + e.clubId() + ":" + e.userId() + ":" + e.occurredAt());
    }

    /** era == null → the repository stamps the club's latest known era from previous entries. */
    private void record(UUID clubId, Integer era, TimelineEntryType type, UUID actorId, UUID subjectId,
                        Map<String, Object> data, Instant occurredAt, String dedupKey) {
        entries.insertIfAbsent(UUID.randomUUID(), clubId, era, type.name(), actorId, subjectId, json(data),
                occurredAt, dedupKey);
    }

    private String json(Map<String, Object> data) {
        try {
            return objectMapper.writeValueAsString(data);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException(ex);
        }
    }
}
```

```java
package pt.vclubroom.history.persistence;

import java.time.Instant;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import pt.vclubroom.history.domain.TimelineEntry;

public interface TimelineEntryRepository extends JpaRepository<TimelineEntry, UUID> {

    @Modifying
    @Query(value = """
           insert into history.timeline_entries (id, club_id, era, type, actor_id, subject_id, data, occurred_at, dedup_key)
           values (:id, :clubId,
                   coalesce(:era, (select max(t.era) from history.timeline_entries t where t.club_id = :clubId), 0),
                   :type, :actorId, :subjectId, cast(:data as jsonb), :occurredAt, :dedupKey)
           on conflict (club_id, dedup_key) do nothing
           """, nativeQuery = true)
    void insertIfAbsent(@Param("id") UUID id, @Param("clubId") UUID clubId, @Param("era") Integer era,
                        @Param("type") String type, @Param("actorId") UUID actorId, @Param("subjectId") UUID subjectId,
                        @Param("data") String data, @Param("occurredAt") Instant occurredAt,
                        @Param("dedupKey") String dedupKey);
}
```

## 7. Data

Schema `history`: `timeline_entries`. See [04-database.md § history](../04-database.md#412-history).

## 8. Extension points

- **Milestones** ("100th member", "1st anniversary"): new entry types computed by a job or a listener on `MemberJoined`.
- **Public "Hall of fame"** of archived clubs with their eras and founders, for presentations and recruiting.
