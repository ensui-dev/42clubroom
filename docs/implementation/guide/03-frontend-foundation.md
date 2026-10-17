# Guide 03 — Frontend foundation

**Goal:** a React + TypeScript SPA with Tailwind v4, shadcn/ui, feature folders, lint/test tooling and a typed API client talking to the backend through the Vite proxy (same origin as production).

Backlog: **E01-S03**, **E01-S04**, **E03-S01**, **E03-S02**, **E02-S03** (owner C). Time: ~9 h.

---

## 1. Create the project

```bash
cd UNIX_CLUB
npm create vite@9 frontend -- --template react-ts
cd frontend
npm install
```

## 2. Dependencies (versions from the design, R-14)

```bash
npm i react@^19.3.1 react-dom@^19.3.1 react-router@^7.20.5 \
      @tanstack/react-query@^5.104.3 zustand@^5.0.15 \
      react-hook-form@^7.90.0 zod@^4.6.7 @hookform/resolvers@^5.9.2 \
      @stomp/stompjs@^7.5.0 openapi-fetch@^0.17.0 \
      react-markdown@^10.1.0 rehype-sanitize@^6.0.0 lucide-react@^1.59.0 \
      @fullcalendar/core@6.1.22 @fullcalendar/react@6.1.22 @fullcalendar/daygrid@6.1.22 \
      @fullcalendar/timegrid@6.1.22 @fullcalendar/list@6.1.22 @fullcalendar/interaction@6.1.22

npm i -D tailwindcss@^4.3.3 @tailwindcss/vite@^4.3.3 openapi-typescript@^7.13.0 \
         vitest@^5.0.5 jsdom@^30.1.3 @testing-library/react@^16.3.3 \
         typescript-eslint@^8.71.2 eslint-plugin-react-hooks@^7.1.1 globals@^17.13.0
```

> **Pinned on purpose:** React Router **7** and FullCalendar **6** (their newer majors changed APIs; all design snippets use these). Don't run `npm update` across majors during the hackathon.

Add the scripts from [08-frontend §12.1](../../08-frontend.md) (`api:types`, `test`, `lint`).

## 3. Configuration

1. **`vite.config.ts`**: the design version ([08-frontend §12.2](../../08-frontend.md)) plus the Vitest settings:

   ```ts
   /// <reference types="vitest/config" />
   import tailwindcss from "@tailwindcss/vite";
   import react from "@vitejs/plugin-react";
   import { fileURLToPath, URL } from "node:url";
   import { defineConfig } from "vite";

   const backend = "http://localhost:8080";
   const storage = "http://localhost:8333";

   export default defineConfig({
     plugins: [react(), tailwindcss()],
     resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
     server: {
       port: 5173,
       proxy: {
         "/api": { target: backend },
         "/oauth2": { target: backend },
         "/login/oauth2": { target: backend },
         "/ical": { target: backend },
         "/ws": { target: backend, ws: true },
         "/media-public": { target: storage },
         "/media-private": { target: storage },
       },
     },
     test: { environment: "jsdom" },
   });
   ```

2. **Path alias in TypeScript:** the Vite template splits configs (`tsconfig.json` → `tsconfig.app.json`, `tsconfig.node.json`). Add to **both** `tsconfig.json` and `tsconfig.app.json`:

   ```json
   { "compilerOptions": { "baseUrl": ".", "paths": { "@/*": ["./src/*"] } } }
   ```

3. **ESLint:** replace `eslint.config.js` with [08-frontend §12.4](../../08-frontend.md) (feature boundaries).

## 4. Tailwind v4 + shadcn/ui + theme

```bash
npx shadcn@4 init          # detects Vite + Tailwind v4; base colour "neutral"
```

Then point shadcn at our folders in `components.json`:

```json
{
  "aliases": {
    "components": "@/shared/ui",
    "ui": "@/shared/ui",
    "utils": "@/shared/lib/utils",
    "lib": "@/shared/lib",
    "hooks": "@/shared/lib/hooks"
  }
}
```

- Move the CSS that shadcn generated to `src/app/theme.css` and **merge** the design tokens from [08-frontend §10](../../08-frontend.md) (keep one `:root` and one `.dark` block). Import it once in `src/main.tsx`; delete the template's `index.css` and `App.css`.
- Add the components used everywhere (E03-S02-T1):

```bash
npx shadcn@4 add button card dialog dropdown-menu tabs input textarea select switch badge avatar tooltip sonner skeleton label form
```

## 5. Folder skeleton

```bash
mkdir -p src/app/layouts src/shared/{api,realtime,ui,lib}
for f in auth discovery clubs membership groups spaces forum chat media calendar notifications history admin; do
  mkdir -p "src/features/$f"
  [ -f "src/features/$f/index.ts" ] || echo "export {};" > "src/features/$f/index.ts"
done
```

Structure and rules: [08-frontend §2–§3](../../08-frontend.md). Inside a feature use relative imports; across features only `@/features/<name>`.

## 6. API pipeline (E01-S04)

With the backend running (guide 02 §6):

```bash
npm run api:types                     # → src/shared/api/schema.d.ts (commit it)
```

Create `src/shared/api/errors.ts`, `src/shared/api/client.ts`, `src/app/queryClient.ts` from [08-frontend §6](../../08-frontend.md), and `src/app/providers.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Toaster } from "@/shared/ui/sonner";
import { queryClient } from "./queryClient";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster richColors />
    </QueryClientProvider>
  );
}
```

`src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import "./app/theme.css";
import { Providers } from "./app/providers";
import { router } from "./app/router";
import { bootstrapCsrf } from "./shared/api/client";

void bootstrapCsrf();   // ensures the XSRF-TOKEN cookie exists before the first POST

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  </StrictMode>,
);
```

(`RealtimeProvider` is added inside `Providers` in E10-S01, enabled only when `useMe()` returns a user.)

## 7. Shell, design system, auth UI

In this order, following the backlog stories:

1. **E03-S01**: `router.tsx` with the full route table of [08-frontend §4](../../08-frontend.md) (lazy pages), `AppLayout`, `NotFoundPage`, `ErrorPage`, layout placeholders.
2. **E03-S02**: primitives (`PageHeader`, `EmptyState`, `StatusBadge`, `ClubAvatar`, `FullPageSpinner`, `Markdown`), `dates.ts`, theme toggle.
3. **E02-S03**: `useMe`, `RequireAuth`, `RequireAdmin`, `safeReturnTo`, `PostLoginRedirect`, `LoginPage`, user menu ([08-frontend §8](../../08-frontend.md)).

## 8. Check

```bash
npm run dev                     # http://localhost:5173
npm run lint && npm test && npm run build
```

- Open `http://localhost:5173/login` → **Login with 42** → you come back logged in (the backend must run with `APP_PUBLIC_URL=http://localhost:5173`, which `run-dev.sh` does).
- The local admin login form works too.

## 9. Done when

- [ ] Lint, tests and build pass; importing `@/features/clubs/CreateClubWizard` from another feature fails lint.
- [ ] `schema.d.ts` committed; a typed `api.GET` call works in the browser.
- [ ] Every route renders (placeholders OK); 404 page works; theme toggle works.
- [ ] Login with 42 and local login both work through `localhost:5173`.
