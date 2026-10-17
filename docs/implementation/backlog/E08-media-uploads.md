# E08 — Media uploads

| | |
|---|---|
| **Goal** | Images, video and audio go straight from the browser to SeaweedFS with presigned URLs and are attached safely to posts, chat, clubs and events. |
| **Design** | [media.md](../../03-backend/media.md), [09-deployment §5–§6](../../09-deployment.md) |
| **Primary track** | B (backend), C (frontend) |
| **Depends on** | E01 |
| **Estimate** | 5 h (4.5 Must · 0 Should · 0.5 Could) |

## Stories

### E08-S01 · Object storage integration

**Priority:** Must · **Milestone:** M2 · **Track:** B · **Estimate:** 1.5 h

> As a **developer**, I want **the backend wired to SeaweedFS over the S3 API, with buckets created automatically** so that **media features can be built on a tested foundation**.

**Acceptance criteria**
- On start-up, `media-public` and `media-private` exist (idempotent, safe with N instances).
- A presigned PUT followed by a presigned GET works **through the Vite proxy and through nginx**: same origin, signature valid (Host preserved).
- Anonymous GET works on `media-public` and is denied on `media-private`.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E08-S01-T1 | `media` migration | DB | 0.25 | E01-S02 | [04-database §4.6](../../04-database.md) |
| E08-S01-T2 | `StorageProperties`, `S3Config` (path-style, checksum `WHEN_REQUIRED`, public-endpoint presigner), `ObjectStorage` port + `S3ObjectStorage`, `BucketInitializer` | BE | 0.75 | E01-S02 | [media.md §9.1–§9.2](../../03-backend/media.md) |
| E08-S01-T3 | **De-risking spike:** presign a PUT from a test endpoint, upload with `curl` via `:5173` and via nginx `:8080`, then GET it | OPS | 0.5 | T2 | [media.md §9.1](../../03-backend/media.md) |

**Branch:** `UNIX_CLUB/dev/feat(E08-S01)/object-storage`

---

### E08-S02 · Upload and attach media

**Priority:** Must · **Milestone:** M2 · **Track:** B + C · **Estimate:** 3 h

> As a **member writing a post**, I want to **attach images, videos and audio clips with a progress bar** so that **the club can share rich content** (subject: "ability to post (image, video, audio)").

**Acceptance criteria**
- `POST /api/media/uploads` validates purpose, content type and size (images ≤ 10 MB, audio ≤ 50 MB, video ≤ 90 MiB, R-12) and returns a presigned PUT.
- `POST /api/media/{id}/complete` verifies the stored object (size and type) and deletes it on mismatch (`422 MEDIA_REJECTED`).
- `MediaCatalog.attach` accepts only the uploader's `READY` objects for the right purpose (BR-19); `resolve` returns public URLs or 15-minute presigned GET URLs.
- `MediaPicker` shows per-file progress; `MediaView` renders `<img>`, `<video controls>`, `<audio controls>`.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E08-S02-T1 | `MediaObject`, `MediaProperties`, `MediaUploadService` (slot, complete), `MediaController` | BE | 0.75 | E08-S01 | [media.md §9.3–§9.5](../../03-backend/media.md) |
| E08-S02-T2 | `media.api` (`MediaCatalog`, `MediaView`, `MediaPurpose`, `MediaKind`) + `MediaCatalogService` | BE | 0.5 | T1 | [media.md §5, §9.4](../../03-backend/media.md) |
| E08-S02-T3 | `uploadMedia` (XHR progress), `MediaPicker`, `MediaView` players | FE | 1.75 | T1 (contract) | [08-frontend §11.2](../../08-frontend.md) |

**MVP cut (saves ~0.75 h):** single-file picker without drag & drop; one global progress bar.

**Branch:** `UNIX_CLUB/dev/feat(E08-S02)/media-upload`

---

### E08-S03 · Orphan media cleanup

**Priority:** Could · **Milestone:** M5 · **Track:** B · **Estimate:** 0.5 h

> As an **operator**, I want **abandoned uploads deleted automatically** so that **storage doesn't fill up with orphans**.

**Acceptance criteria**
- `PENDING`/`READY` objects older than 24 h are deleted from storage and marked `DELETED`, by one instance at a time (`SKIP LOCKED`).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E08-S03-T1 | `OrphanMediaCleanupJob` (`claimOrphans` + delete) | BE | 0.5 | E08-S02 | [media.md §8.3](../../03-backend/media.md) |

**Branch:** `UNIX_CLUB/dev/feat(E08-S03)/orphan-cleanup`
