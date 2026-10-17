# E12 — Notifications and email

| | |
|---|---|
| **Goal** | Domain events become in-app notifications (live badge) and, by preference, emails via Resend (D-03, D-30, D-35). |
| **Design** | [notification.md](../../03-backend/notification.md), [09-deployment §10](../../09-deployment.md) |
| **Primary track** | B (backend), C (frontend) |
| **Depends on** | E04, E07, E09, E11 (event sources), E10-S01 (live push) |
| **Estimate** | 7.75 h (0 Must · 7.75 Should · 0 Could) |

## Stories

### E12-S01 · In-app notifications

**Priority:** Should · **Milestone:** M3 · **Track:** B + C · **Estimate:** 4.75 h

> As a **user**, I want **a bell with unread notifications** (club approved, join request received or decided, ownership invitation, new post, new comment or reply, event scheduled or cancelled) so that **I never miss what concerns me**.

**Acceptance criteria**
- Each source event produces notifications for the recipients in [notification.md §4](../../03-backend/notification.md); re-delivery creates no duplicates (`dedup_key`).
- The badge increments live via `/user/queue/notifications`; the inbox paginates; mark one or all as read.
- Clicking a notification navigates to its target (`/posts/:id` redirects to the right channel).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E12-S01-T1 | `notification` migration (incl. email outbox columns) | DB | 0.25 | E01-S02 | [04-database §4.10](../../04-database.md) |
| E12-S01-T2 | `NotificationType`, `Notification`, `NotificationPreference` entities; `PreferenceService.effective`; `NotificationDispatcher` (batch insert, dedup, after-commit push) | BE | 0.75 | T1, E10-S01-T2 | [notification.md §8](../../03-backend/notification.md) |
| E12-S01-T3 | Listeners: `ClubNotificationListener`, `MembershipNotificationListener`, `ForumNotificationListener`, `CalendarNotificationListener` | BE | 1.25 | T2 + source events | [notification.md §4, §8](../../03-backend/notification.md) |
| E12-S01-T4 | `NotificationController` (inbox, unread count, read, read-all) | BE | 0.5 | T2 | [notification.md §6](../../03-backend/notification.md) |
| E12-S01-T5 | `NotificationBell` (live count), dropdown, `NotificationsPage`, `PostRedirectPage` | FE | 2.0 | T4 (contract), E10-S01-T3 | [08-frontend §9.3](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E12-S01)/in-app-notifications`

---

### E12-S02 · Notification preferences

**Priority:** Should · **Milestone:** M4 · **Track:** B + C · **Estimate:** 1.5 h

> As a **user**, I want to **choose per notification type whether I get it in-app and/or by email** so that **I'm informed without spam**.

**Acceptance criteria**
- Preferences page lists every type with in-app and email toggles, showing the defaults (R-15); only overrides are stored.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E12-S02-T1 | `PreferenceService.allFor/save` + `PreferenceController` | BE | 0.5 | E12-S01-T2 | [notification.md §6](../../03-backend/notification.md) |
| E12-S02-T2 | `PreferencesForm` (type × in-app/email matrix) in `/settings` | FE | 1.0 | T1 | — |

**Branch:** `UNIX_CLUB/dev/feat(E12-S02)/notification-preferences`

---

### E12-S03 · Email notifications via Resend

**Priority:** Should · **Milestone:** M4 · **Track:** B · **Estimate:** 1.5 h

> As a **user**, I want **important notifications by email** (ownership invitation, club approved or archived, join decision, event cancelled or reminder) so that **I'm reached even when I'm not on the site**.

**Acceptance criteria**
- In the demo, emails are delivered by Resend from `no-reply@42clubroom.ensui.dev`; in dev they land in Mailpit; `MAIL_TRANSPORT=log` prints them.
- An SMTP failure never breaks event processing; retries back off (1, 2, 4, 8, 16 min, max 5) and the last error is stored (R-27).
- Switching provider requires only `SMTP_*` / `MAIL_FROM` changes.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E12-S03-T1 | **Start on day 1:** Resend account, add domain `42clubroom.ensui.dev`, DNS records in Cloudflare, API key, `.env` values | OPS | 0.5 | — | [09-deployment §10](../../09-deployment.md) |
| E12-S03-T2 | `EmailSender` port, `OutgoingEmail`, `EmailDeliveryException`, `SmtpEmailSender`, `LoggingEmailSender`, `AppMailProperties` | BE | 0.5 | E01-S02 | [notification.md §8.1](../../03-backend/notification.md) |
| E12-S03-T3 | `EmailDispatchJob` (claim with backoff, send, record outcome) | BE | 0.5 | T2, E12-S01-T2 | [notification.md §8.2](../../03-backend/notification.md) |

**Branch:** `UNIX_CLUB/dev/feat(E12-S03)/email-resend`
