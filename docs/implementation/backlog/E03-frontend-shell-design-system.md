# E03 — Frontend shell and design system

| | |
|---|---|
| **Goal** | One consistent look and navigation for every page (Presentation 10%, UI/UX 25%). |
| **Design** | [08-frontend.md §4, §9, §10](../../08-frontend.md) |
| **Primary track** | C |
| **Depends on** | E01-S03 |
| **Estimate** | 6.5 h (3.5 Must · 3 Should · 0 Could) |

## Stories

### E03-S01 · App shell and routing

**Priority:** Must · **Milestone:** M0 · **Track:** C · **Estimate:** 1.5 h

> As a **user**, I want **a stable top bar and navigation between Landing, Clubs, Calendar, Notifications and Admin** so that **I always know where I am**.

**Acceptance criteria**
- Every route of [08-frontend §4](../../08-frontend.md) exists (lazy placeholder pages are fine at first).
- Unknown URLs show a friendly 404; runtime errors show an error page with a "back home" link.
- `ClubLayout` and `AdminLayout` placeholders render nested routes.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E03-S01-T1 | `router.tsx` with the full route map (lazy routes), `AppLayout` (top bar, nav, notification bell slot), `NotFoundPage`, `ErrorPage` | FE | 1.0 | E01-S03 | [08-frontend §4](../../08-frontend.md) |
| E03-S01-T2 | `ClubLayout` and `AdminLayout` placeholders with `<Outlet/>`; mount `PostLoginRedirect` | FE | 0.5 | T1 | [08-frontend §9.2](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E03-S01)/app-shell`

---

### E03-S02 · Design system and primitives

**Priority:** Must · **Milestone:** M0 · **Track:** C · **Estimate:** 2 h

> As a **frontend developer**, I want **a shared kit of components and helpers** so that **every feature looks the same without extra effort**.

**Acceptance criteria**
- shadcn components (button, card, dialog, dropdown-menu, tabs, input, textarea, select, switch, badge, avatar, tooltip, toast/sonner, skeleton) are available under `@/shared/ui`.
- `Markdown` renders sanitized content (no raw HTML); links open with `rel="noopener noreferrer nofollow"`.
- Dates render in `Europe/Lisbon`; light/dark toggle persists.

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E03-S02-T1 | `npx shadcn@4 add …` for the component list above | FE | 0.5 | E01-S03-T3 | [08-frontend §10](../../08-frontend.md) |
| E03-S02-T2 | App primitives: `PageHeader`, `EmptyState`, `StatusBadge` (ACTIVE/ARCHIVED/PENDING), `ClubAvatar`, `FullPageSpinner`, `Markdown` (react-markdown + rehype-sanitize) | FE | 1.0 | T1 | [08-frontend §10](../../08-frontend.md), [07-security §7](../../07-security.md) |
| E03-S02-T3 | `shared/lib/dates.ts` (Intl, Europe/Lisbon), theme toggle (Zustand + `.dark` class) | FE | 0.5 | T1 | [08-frontend §5.3, §10](../../08-frontend.md) |

**Branch:** `UNIX_CLUB/dev/feat(E03-S02)/design-system`

---

### E03-S03 · UX polish pass

**Priority:** Should · **Milestone:** M5 · **Track:** C · **Estimate:** 3 h

> As a **judge or new student**, I want **the app to feel finished**: loading states, empty states, mobile layout, accessibility, so that **it is pleasant to use and demo**.

**Acceptance criteria**
- No page shows a blank area while loading (skeletons) or when empty (EmptyState with a call to action).
- The club page and chat are usable at 375 px width.
- Keyboard navigation works for menus and dialogs; chat new messages are announced (`aria-live`).

| Task | Description | Layer | Est (h) | Depends on | Design ref |
|------|-------------|-------|--------:|-----------|------------|
| E03-S03-T1 | Skeletons and empty states on all list pages (directory, feed, chat, calendar, notifications, admin queues) | FE | 1.0 | features merged | [08-frontend §10](../../08-frontend.md) |
| E03-S03-T2 | Responsive pass (club sidebar as drawer on mobile, top bar collapse) | FE | 1.0 | features merged | — |
| E03-S03-T3 | Accessibility pass (focus rings, labels, `aria-live` in chat, contrast check in both themes) | FE | 0.5 | features merged | — |
| E03-S03-T4 | Copy and icon consistency (lucide icons, button wording, status labels) | FE | 0.5 | features merged | — |

**Branch:** `UNIX_CLUB/dev/style(E03-S03)/ux-polish`
