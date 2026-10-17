# E09 — Forum: posts, comments and reactions

| | |
|---|---|
| **Goal** | Members publish posts (text + image/video/audio) in forum channels, comment with one level of replies and react with emojis (D-05, D-26). |
| **Design** | [forum.md](../../03-backend/forum.md) |
| **Primary track** | B (backend), C (frontend) |
| **Depends on** | E05 (channel access), E08 (media) |
| **Estimate** | 11.5 h (8.75 Must · 2.75 Should · 0 Could) |

## Stories

### E09-S01 · Publish and read posts with media

**Priority:** Must · **Milestone:** M2 · **Track:** B + C · **Estimate:** 5 h

> As a **club member**, I want to **publish posts with text and media in a forum channel and scroll through them** so that **the club has a living space to share and create** (subject: "ability to post (image, video, audio)").

**Acceptance criteria**
- **Given** I can write in the channel, **when** I publish text and/or media, **then** the post appears at the top with author, time and players. `PostPublished` is emitted.
- **Given** I can only read (e.g. non-member in a `PUBLIC` space), **then** I see the posts but no composer; a write attempt → `403 CHANNEL_WRITE_DENIED`.
- Infinite scroll (keyset pagination, 20 per page); `?era=n` shows a previous era (read-only banner).
- Empty post (no text, no media) → `400 EMPTY_POST`.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E09-S01-T1 | `forum` migration (posts, post_media, comments, reactions) | DB | 0.25 | E01-S02 | [04-database §4.7](../../04-database.md) |
| E09-S01-T2 | `Post` domain + `PostRepository` (keyset queries, pinned) | BE | 0.5 | T1 | [forum.md §9](../../03-backend/forum.md) |
| E09-S01-T3 | `PostService.createPost` (access check, media attach, era stamp, `PostPublished`) + `PostController` (create, list) | BE | 0.75 | T2, E05-S01, E08-S02 | [forum.md §8.1, §9](../../03-backend/forum.md) |
| E09-S01-T4 | `PostQueryService.list` (era filter, keyset cursor, batch decoration: authors, media, reaction counts, my reactions, `readOnly`) + pinned endpoint | BE | 1.0 | T3 | [forum.md §8.2](../../03-backend/forum.md) |
| E09-S01-T5 | `ChannelFeed` (infinite query), `PostCard` (Markdown + `MediaView`), `PostComposer` (Markdown textarea + `MediaPicker`), read-only/era banner | FE | 2.5 | T3 (contract), E08-S02-T3, E05-S02-T2 | [08-frontend §9.2–§9.3](../../08-frontend.md) |

**MVP cut (saves ~0.75 h):** no pinned posts and no era banner (era filter only via the History tab, E14-S03).

**Branch:** `UNIX_CLUB/dev/feat(E09-S01)/posts`

---

### E09-S02 · Comments with one level of replies

**Priority:** Must · **Milestone:** M2 · **Track:** B + C · **Estimate:** 2.25 h

> As a **reader**, I want to **comment on posts and reply to comments** so that **discussions happen next to the content** (subject: "ability to comment on posts").

**Acceptance criteria**
- Comments list oldest-first; replies are shown under their parent; replying to a reply → `422 INVALID_PARENT` (BR-17).
- Commenting on a post from a previous era → `422 HISTORY_READ_ONLY` (BR-15).
- `CommentAdded` carries the post author and the parent author (for notifications).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E09-S02-T1 | `Comment` domain, `CommentRepository`, `CommentService` (create/list), `CommentController`, `CommentAdded`; increment `comment_count` | BE | 0.75 | E09-S01-T3 | [forum.md §9](../../03-backend/forum.md) |
| E09-S02-T2 | `Comments` component (thread with replies, reply box, counts) | FE | 1.5 | T1 (contract), E09-S01-T5 | [08-frontend §9.3](../../08-frontend.md) |

**MVP cut (saves ~0.5 h):** flat comments in the UI (API still supports replies).

**Branch:** `UNIX_CLUB/dev/feat(E09-S02)/comments`

---

### E09-S03 · Emoji reactions

**Priority:** Must · **Milestone:** M2 · **Track:** B + C · **Estimate:** 1.5 h

> As a **reader**, I want to **react to posts and comments with emojis** so that **I can respond quickly** (subject: "react on posts").

**Acceptance criteria**
- `PUT/DELETE /api/posts/{id}/reactions/{code}` are idempotent; unknown codes → `400 UNKNOWN_REACTION`; one reaction per user per emoji (BR-18).
- The UI toggles optimistically and rolls back on error; counts and "mine" state are correct after refresh.
- `GET /api/reactions` returns the configured set (👍 ❤️ 😂 🎉 😮 😢).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E09-S03-T1 | `Reaction` entity, `ReactionRepository` (counts, mine, upsert, remove), `ReactionService`, `ReactionController` (posts and comments), `GET /api/reactions` | BE | 0.5 | E09-S01-T2 | [forum.md §9](../../03-backend/forum.md) |
| E09-S03-T2 | `Reactions` bar (optimistic toggle, picker from `/api/reactions`) on posts and comments | FE | 1.0 | T1 (contract), E09-S01-T5 | [08-frontend §5.2](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E09-S03)/reactions`

---

### E09-S04 · Edit, delete, pin and moderate

**Priority:** Should · **Milestone:** M4 · **Track:** B + C · **Estimate:** 1.75 h

> As an **author**, I want to **edit or delete my posts and comments**, and as a **moderator** (`CONTENT_MODERATE`) to **remove or pin content**, so that **the space stays healthy**.

**Acceptance criteria**
- Authors edit/delete their own content in the current era; moderators delete others' content and pin/unpin posts.
- Deleted items stay as tombstones ("removed by a moderator" / "deleted"), never hard-deleted (BR-16).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E09-S04-T1 | Edit/delete post and comment, pin/unpin endpoints with author/moderator rules | BE | 0.75 | E09-S02 | [forum.md §7, §9](../../03-backend/forum.md) |
| E09-S04-T2 | Post and comment action menus, edit dialog, tombstone rendering | FE | 1.0 | T1 | — |

**Branch:** `UNIX_CLUB/dev/feat(E09-S04)/forum-moderation`

---

### E09-S05 · Club feed

**Priority:** Should · **Milestone:** M3 · **Track:** B + C · **Estimate:** 1 h

> As a **student on a club home page**, I want **the latest posts from all forum channels I can read** so that **I see what's new at a glance**.

**Acceptance criteria**
- `GET /api/clubs/{id}/feed` returns posts from readable forum channels only (`readableForumChannels`), newest first.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E09-S05-T1 | `FeedController` + `PostRepository.findFeedPage` | BE | 0.5 | E09-S01-T4 | [forum.md §7](../../03-backend/forum.md) |
| E09-S05-T2 | Feed section on `ClubHome` (reuses `PostCard`) | FE | 0.5 | T1, E04-S03-T2 | — |

**Branch:** `UNIX_CLUB/dev/feat(E09-S05)/club-feed`
