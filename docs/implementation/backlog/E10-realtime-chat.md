# E10 — Real-time and chat

| | |
|---|---|
| **Goal** | Live updates over WebSocket (push-only, Redis fan-out across instances) and chat rooms in community spaces (D-03, D-16, D-23, R-03). |
| **Design** | [realtime.md](../../03-backend/realtime.md), [chat.md](../../03-backend/chat.md), [06-messaging-and-realtime §6](../../06-messaging-and-realtime.md) |
| **Primary track** | B (backend), C or B (frontend) |
| **Depends on** | E05 (channel access) |
| **Estimate** | 7.75 h (0 Must · 6.5 Should · 1.25 Could) |

## Stories

### E10-S01 · Real-time infrastructure

**Priority:** Should · **Milestone:** M3 · **Track:** B + C · **Estimate:** 2.25 h

> As a **user with the app open**, I want **new content to appear without refreshing** so that **the clubroom feels alive**, even when the backend runs several instances.

**Acceptance criteria**
- STOMP over `/ws` connects only with a valid session and an allowed `Origin`; client `SEND` frames are rejected.
- Subscribing to an unknown destination, or a channel I can't read, fails; `/user/queue/notifications` always works for myself.
- With 2 backend instances, a push published on instance 1 reaches a browser connected to instance 2 (Redis relay).
- Pushes are sent only after the business transaction commits.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E10-S01-T1 | `WebSocketConfig`, `SubscriptionAuthorizationInterceptor`, `realtime.spi.SubscriptionAuthorizer`, `RealtimeProperties` | BE | 0.5 | E02-S01-T5 | [realtime.md §7](../../03-backend/realtime.md) |
| E10-S01-T2 | `realtime.api.RealtimePublisher` + `RedisRealtimePublisher` (after-commit), `RedisRealtimeRelay`, `RealtimeRedisConfig`, `RealtimeEnvelope` | BE | 0.5 | T1 | [realtime.md §7](../../03-backend/realtime.md) |
| E10-S01-T3 | `RealtimeProvider` + `useTopic` (reconnect → invalidate queries), enabled when logged in | FE | 0.75 | E02-S03-T1 | [08-frontend §7](../../08-frontend.md) |
| E10-S01-T4 | Verify `/ws` through nginx with 2 replicas (`--scale backend=2`) and later through Cloudflare | OPS | 0.5 | T2, E16-S01 | [09-deployment §5, §11.3](../../09-deployment.md) |

**Branch:** `UNIX_CLUB/dev/feat(E10-S01)/realtime`

---

### E10-S02 · Chat rooms

**Priority:** Should · **Milestone:** M3 · **Track:** B + C · **Estimate:** 4.25 h

> As a **club member**, I want **real-time chat rooms in the club's spaces** so that **we can talk casually next to the forum** (team requirement: club chat; history kept forever, D-23).

**Acceptance criteria**
- Sending is a REST call with a `clientNonce`; retries never duplicate a message; other subscribers see it within a second.
- Scrolling up loads older messages (50 per page, keyset by id); `?era=n` shows a previous era read-only.
- Only readers of the space can subscribe; only writers can send (`403` otherwise); archived club → read-only.
- Own messages appear instantly as "sending" and are reconciled when the response or push arrives (no duplicates).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E10-S02-T1 | `chat` migration | DB | 0.25 | E01-S02 | [04-database §4.8](../../04-database.md) |
| E10-S02-T2 | `ChatMessage`, `ChatMessageRepository`, `ChatService.send` (idempotent nonce, media attach, push), history query, `ChatTopicAuthorizer` | BE | 1.0 | T1, E10-S01, E05-S01 | [chat.md §8](../../03-backend/chat.md) |
| E10-S02-T3 | `ChatMessageController` (send, history, edit, delete) | BE | 0.5 | T2 | [chat.md §6](../../03-backend/chat.md) |
| E10-S02-T4 | `ChatRoom`, `MessageList` (infinite scroll up, auto-scroll), `MessageComposer` (optimistic send), `useChatMessages` | FE | 2.5 | T3 (contract), E10-S01-T3 | [08-frontend §7, §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E10-S02)/chat`

---

### E10-S03 · Live forum updates

**Priority:** Could · **Milestone:** M3 · **Track:** B + C · **Estimate:** 1.25 h

> As a **reader of a forum channel**, I want **new posts, comments and reaction counts to appear live** so that **conversations feel immediate**.

**Acceptance criteria**
- `post.created` appears at the top of an open channel feed; `comment.created` and `reactions.changed` update an open post.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E10-S03-T1 | `ForumTopicAuthorizer` + pushes in `PostService`, `CommentService`, `ReactionService` | BE | 0.5 | E10-S01, E09-S03 | [forum.md §6, §9](../../03-backend/forum.md) |
| E10-S03-T2 | `useTopic` subscriptions in `ChannelFeed` and post detail, cache updates | FE | 0.75 | T1 | [08-frontend §7](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E10-S03)/live-forum`
