# 00 — Decision Log

This file records every decision behind the design, where it came from, and what is still open.

- **Confirmed (D-xx)**: decided by the team during the design session on 2026-10-17. Treat these as requirements.
- **Design choices to review (R-xx)**: decisions the designer made to complete the design. They are flagged so the team can veto them. Each one is isolated in a single place in the code, so changing it is cheap.
- **Open items (O-xx)**: information that is still missing. Nothing in the design blocks on them.

---

## Confirmed decisions

| ID | Topic | Decision | Notes / consequences |
|----|-------|----------|----------------------|
| D-01 | Frontend | **React + TypeScript (Vite)** single-page app consuming the REST API. | See [08-frontend.md](08-frontend.md). |
| D-02 | Architecture | **Modular monolith** (one Spring Boot app, strict feature modules enforced by Spring Modulith). Modules communicate through **in-process domain events persisted in PostgreSQL** (event publication registry = transactional outbox). | **No Kafka for now.** The design is Kafka-ready: events can be externalized without changing module code. See [06-messaging-and-realtime.md](06-messaging-and-realtime.md). |
| D-03 | Communication scope | In-app notifications, real-time updates (WebSocket), email notifications **and** club chat. | Team priority: **scalability and maintainability first**. |
| D-04 | Community spaces | Every club has **spaces** (community spaces). A space is the **unit of access control**. Whoever has access to a space has access to all of its forums and chat rooms. Spaces can be public, private to the club, or private to predefined groups. | Core structural concept. See [space module](03-backend/space.md). |
| D-05 | Content model | **Unified**: a post (text + image/video/audio) *is* a forum thread; comments are replies; reactions work on both. The club feed is the posts from the spaces the viewer can read. | One content system instead of two. See [forum module](03-backend/forum.md). |
| D-06 | Groups | **Both** club-defined groups (subset of a club's members) **and** campus-wide groups. | See [group module](03-backend/group.md). |
| D-07 | Access levels | Each space has **separate read and write levels**, each one of `PUBLIC` (any logged-in user), `CLUB_MEMBERS`, `GROUPS` (one or more groups). | |
| D-08 | Authentication | **Login with 42 (OAuth2)** + **local password accounts**. | See [07-security.md](07-security.md). |
| D-09 | Local accounts | Local (password) accounts are **created by admins only**. There is no public self-registration. | Intended for staff and external partners. |
| D-10 | Join policy | **Per-club setting**: `OPEN` (instant join) or `APPROVAL` (request + approval). **Default is `APPROVAL`.** | |
| D-11 | Club creation | **Admin approval required.** The club starts as `PENDING_APPROVAL`. | |
| D-12 | Club ownership | **Multiple co-owners.** | Refined by D-17 and D-21. |
| D-13 | Archival trigger | **Manual by admin only.** | No automatic archival. |
| D-14 | Revival ("rebuild") | **A student requests revival, an admin approves.** The requester becomes owner. Old history stays visible and read-only under a "previous era" marker. | Membership details in R-05. |
| D-15 | Media storage | **S3-compatible object storage.** | The server choice is D-27. |
| D-16 | WebSocket scaling | **Redis pub/sub fan-out** between backend instances. | |
| D-17 | Calendar | **Per-club calendar, campus-wide calendar, RSVP / attendance, iCal export.** | |
| D-18 | Club management | **Per-club custom roles** built from a **platform-defined permission catalogue**. Built-in `Owner` and `Member` roles always exist. A member can hold several roles. | Follows from the team's directive that "club dynamics and management structure are defined per club, keep a flexible structure". |
| D-19 | Groups vs roles | **Separate concepts.** Roles = bundles of permissions. Groups = membership lists used for space access. | |
| D-20 | Stack versions | **Java 21 + Spring Boot 3.5 (3.5.16) + Maven.** | Spring Boot 3.5 open-source support ended on 2026-06-30. Upgrading to Boot 4 later is a self-contained task. |
| D-21 | Campus groups source | **Both** admin-managed groups **and** groups auto-synced from 42 API data (pool, cursus, campus) on login. | |
| D-22 | Co-owner governance | An owner **invites** a member to co-own and the member must **accept**. Owners can **step down** if at least one owner remains. **Only admins** can forcibly remove an owner. | Ownership *transfer* = invite + accept + step down. |
| D-23 | Chat history | **Kept forever and part of club history.** It becomes read-only when the club is archived. | |
| D-24 | Anonymous visitors | **The landing page and the club directory are public.** Spaces, posts, chat and calendar require login. | |
| D-25 | Event creation | **Permission-based** (`EVENT_MANAGE`). Each club decides which of its roles get it. | Follows from D-18. |
| D-26 | Reactions / comments | **Fixed emoji set** (configurable platform-wide) + **one level of replies** under comments. | |
| D-27 | Object storage server | **SeaweedFS** (Apache-2.0), single container with its S3 gateway. | MinIO Community Edition is source-only and its repository was archived in April 2026, so it was replaced. The backend only speaks the S3 API, so the server stays swappable. |
| D-28 | Space layout | A space holds **N channels** of type `FORUM` or `CHAT`. All channels inherit the space's read and write levels. | |
| D-29 | Access override | A **`SPACE_ACCESS_ALL`** permission (the Owner role has it by default) lets a role see and moderate restricted spaces. **Admins always can.** | |
| D-30 | Email notifications | **Per-user, per-type preferences** (in-app and email toggles) with sensible defaults. | Defaults in R-15. |
| D-31 | Docs location | `/home/ensui/vclubroom/docs/`, outside the submission repo. | |
| D-32 | Team name | **UNIX_CLUB**. The submission directory is `Hackathon_SA_2026/UNIX_CLUB/`. | Resolves O-03. |
| D-33 | Demo domain | **Single origin `https://42clubroom.ensui.dev`**: SPA at `/`, API at `/api`, WebSocket at `/ws`, login at `/oauth2` + `/login/oauth2`, media at `/media-*`. | A subdomain split (`api.`, `login.`) was considered and declined for the demo: it would need CORS with credentials, shared cookie domains and more certificates. The API base stays configurable, so a split later is a config change. Production will later move to 42's infrastructure with bocal. |
| D-34 | Demo hosting | **Cloudflare Tunnel**, integrated into the team's existing Cloudflare Tunnel setup. Cloudflare terminates TLS; no inbound ports are opened. | `.dev` is HSTS-preloaded, so HTTPS is mandatory. Consequences: R-12 (100 MB upload cap) and R-26 (real client IP / scheme from Cloudflare headers). |
| D-35 | Email | **Resend over SMTP** (`smtp.resend.com`), behind an `EmailSender` port in the notification module. | Free tier ≈ 3,000/month, 100/day, 1 verified domain. Changing provider (Brevo, SES, bocal's SMTP…) = changing environment variables only. Mailpit stays the dev SMTP. Resolves O-01 for the demo. |

---

## Design choices to review

Each item names the single place in the design where it lives, so reverting it stays cheap.

| ID | Choice | Why | Lives in |
|----|--------|-----|----------|
| R-01 | Base Java package `pt.vclubroom`; artifact `vclubroom-backend`; frontend `vclubroom-frontend`. | Neutral, short. | Everywhere (rename = IDE refactor). |
| R-02 | **Server-side sessions** (HttpOnly `SESSION` cookie, Spring Session stored in Redis) instead of JWT. | Tokens never reach JavaScript (XSS-safe). Sessions can be revoked immediately (disable user, role change). The WebSocket handshake reuses the cookie. Instances stay stateless because sessions live in Redis. | [07-security.md](07-security.md) |
| R-03 | **Commands over REST, WebSocket is push-only** (server → browser via STOMP). | One validation, CSRF and error path for every write. The load balancer spreads writes evenly. WebSocket code stays tiny. | [06-messaging-and-realtime.md](06-messaging-and-realtime.md) |
| R-04 | **One PostgreSQL database, one schema per module, no cross-schema foreign keys.** References across modules are by UUID. | Data ownership mirrors module ownership, and any module can be extracted later. Integrity across modules is handled by events. | [04-database.md](04-database.md) |
| R-05 | **Revival membership policy:** the requester becomes `Owner`; previous owners are demoted to `Member` (they keep history access); other members are untouched; posts from previous eras become read-only. | No data migration and no access lost. Avoids "ghost owners" from the previous generation. | `membership.application.ClubLifecycleListener` |
| R-06 | **Calendar events belong to a space** and inherit its read access (a public space means a public event). | Access rules stay in one place (D-04). No second visibility model. | [calendar module](03-backend/calendar.md) |
| R-07 | **Default space on approval:** "General" (read `PUBLIC`, write `CLUB_MEMBERS`) with a forum channel "Posts" and a chat channel "Lounge". | A new club is usable immediately. Owners can change everything. | `space.application.DefaultSpaceProvisioner` |
| R-08 | **Admins pass every club permission check** (break-glass for moderation and rescue). They **cannot write to archived clubs** (archived = read-only for everyone). Admin actions are recorded in the club timeline. | Admins must be able to rescue a club whose owners are gone. | `membership.application.ClubAuthorizationService` |
| R-09 | **Admin bootstrap** via `APP_ADMIN_BOOTSTRAP_LOGINS` (42 logins that become admin on first login) plus an optional bootstrap local admin. 42 `staff?` is stored but **not** auto-mapped to admin. | Someone must be the first admin. | `identity.application.UserProvisioningService` |
| R-10 | **On archival:** pending join requests and ownership invitations are cancelled; future events are cancelled. | An archived club cannot act on them. | Listeners in membership and calendar |
| R-11 | **Ownership invitations expire after 7 days.** A "Transfer ownership" action is an invitation with `stepDownOnAccept = true`. | One-click transfer UX on top of the D-22 rules. | `membership.domain.OwnershipInvitation` |
| R-12 | **Media limits** (configurable): images ≤ 10 MB (jpeg/png/webp/gif), audio ≤ 50 MB (mpeg/ogg/wav/webm), **video ≤ 90 MiB** (mp4/webm). No server-side transcoding. | Keeps a 2-day scope while staying safe. The video limit was lowered from 200 MB because Cloudflare (D-34) rejects request bodies over 100 MB on Free/Pro plans. S3 multipart uploads (parts < 100 MB) would lift it later; outside Cloudflare it can go back up. | `app.media.*` properties |
| R-13 | **Two buckets:** `media-public` (club avatars, banners, event covers; anonymous read, needed for the public directory) and `media-private` (post and chat attachments; 15-minute presigned GET URLs). | The directory works for anonymous visitors without leaking private content. | [media module](03-backend/media.md) |
| R-14 | **Frontend libraries:** Tailwind CSS v4 + shadcn/ui, TanStack Query, React Hook Form + Zod, `@stomp/stompjs`. **React Router pinned to 7.x and FullCalendar pinned to 6.x**, because newer majors (8.x / 7.x) shipped recently with changed APIs. | One consistent theme (Presentation criterion) and well-documented APIs. | [08-frontend.md](08-frontend.md) |
| R-15 | **Default notification preferences:** in-app on for every type. Email on only for: club approved/rejected, club archived/revived, ownership invitation, join request decided, event reminder, event cancelled. | Avoids email spam out of the box. | `notification.domain.NotificationType` |
| R-16 | **Personal iCal feed via secret token URL** (`/ical/feeds/{token}.ics`). The user can rotate the token. | Calendar apps cannot log in with 42. | [calendar module](03-backend/calendar.md) |
| R-17 | **Soft delete for all user content.** Moderator deletions leave a tombstone ("removed by a moderator"). | "Club history (all previous posts and comments)" must never silently lose data. | forum, chat |
| R-18 | **Rejected club requests are final.** The founder can submit a new request. | Simplest review workflow. | `club.domain.Club` |
| R-19 | **Post, comment and chat bodies are Markdown**, rendered sanitized in the browser. | Rich text without an editor dependency. | Frontend `react-markdown` + `rehype-sanitize` |
| R-20 | **Club category** from a configurable fixed list (`Tech, Games, Arts, Music, Sports, Culture, Social, Science, Other`) **plus free-form tags**. | Clean directory filters plus flexibility. | `app.clubs.categories` |
| R-21 | **Archived clubs are listed in the directory** (badge + filter, hidden by default). | Makes history browsable and revival discoverable. | [discovery module](03-backend/discovery.md) |
| R-22 | **Club groups contain only club members.** Leaving a club removes the user from that club's groups. Campus groups are unaffected. | Keeps the "private to the club or a group" semantics coherent. | `group.application.MembershipEndedListener` |
| R-23 | **Effective write = read rule AND write rule** (writing always requires reading). A write rule broader than the read rule is normalised to the read rule (e.g. read `CLUB_MEMBERS` + write `PUBLIC` is stored as write `CLUB_MEMBERS`). A `GROUPS` rule with no groups fails closed: only `SPACE_ACCESS_ALL` holders and admins pass. | Prevents nonsensical "can post but can't read" spaces. Campus groups are not subsets of club members, so a simple ordering of levels would not work. | `space.domain.Space` |
| R-24 | **A club's public profile** (name, tagline, description, category, tags, member count, status) **is part of the public directory.** Its spaces, members list and calendar require login. | Lets a new student read about a club before logging in ("join in a few clicks"). | `discovery` endpoints |
| R-25 | **Sender address `Virtual Clubroom <no-reply@42clubroom.ensui.dev>`**, with `42clubroom.ensui.dev` as the Resend verified domain (DNS records in Cloudflare). | Keeps `ensui.dev`'s own mail reputation and records untouched. Note: the Resend free plan allows only one verified domain; if you already use Resend for `ensui.dev`, reuse that domain instead. | `MAIL_FROM` env var + Resend dashboard |
| R-26 | **Behind the tunnel, nginx trusts Cloudflare headers**: `X-Forwarded-Proto` (so Spring builds `https://` OAuth redirects) and `CF-Connecting-IP` (so rate limits apply per real client, not per tunnel connector). The proxy port is bound to a private interface only. | Without this, OAuth redirect URIs would be built as `http://` and every visitor would share one login rate-limit bucket. | `frontend/nginx/default.conf`, `compose.prod.yaml` |
| R-27 | **Email retries back off exponentially** (1, 2, 4, 8, 16 min; max 5 attempts) using an `email_next_attempt_at` column. | A provider limit (e.g. Resend's 100/day) or an outage won't burn all retries within a few minutes. | `notification.application.EmailDispatchJob` |

---

## Open items (non-blocking)

| ID | Item | Needed for |
|----|------|------------|
| O-01 | ~~Demo email~~ → Resend (D-35). Still open: the **production** SMTP provider once the app moves to 42's infrastructure (bocal). Only env vars change. | Production email. |
| O-02 | ~~Demo domain/hosting~~ → `42clubroom.ensui.dev` via Cloudflare Tunnel (D-33, D-34). Still open: the **production** domain and hosting with bocal, and who owns the 42 OAuth application there (its redirect URI must match the production domain). | Production deployment. |
| ~~O-03~~ | ~~Team name~~ → resolved by D-32 (UNIX_CLUB). | — |

