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
npm i react@^19.3.1 react-dom@^19.3.1 react-router@^7.18.4 \
      @tanstack/react-query@^5.104.3 zustand@^5.0.15 \
      react-hook-form@^7.90.0 zod@^4.6.7 @hookform/resolvers@^5.9.2 \
      @stomp/stompjs@^7.5.0 openapi-fetch@^0.17.0 \
      react-markdown@^10.1.0 rehype-sanitize@^6.0.0 lucide-react@^1.59.0 \
      @fullcalendar/core@6.1.22 @fullcalendar/react@6.1.22 @fullcalendar/daygrid@6.1.22 \
      @fullcalendar/timegrid@6.1.22 @fullcalendar/list@6.1.22 @fullcalendar/interaction@6.1.22

npm i -D tailwindcss@^4.3.3 @tailwindcss/vite@^4.3.3 @types/node@^24.13.3 \
         vitest@^5.0.5 jsdom@^30.1.3 @testing-library/react@^16.3.3 \
         typescript-eslint@^8.71.2 eslint-plugin-react-hooks@^7.1.1 globals@^17.13.0
```

> **TypeScript 6 and the type generator.** `create-vite@9` scaffolds **TypeScript 6.0**; keep it (typescript-eslint supports it). `openapi-typescript` still declares `typescript@^5` as a peer, so installing it as a dev dependency fails with `ERESOLVE`. Don't install it: the `api:types` script runs a pinned version through `npx`, which gets its own TypeScript 5 in an isolated cache:
>
> ```bash
> npm pkg set scripts.test="vitest run --passWithNoTests" scripts.test:watch="vitest" \
>   scripts.api:types="npx --yes openapi-typescript@7.13.0 http://localhost:8080/v3/api-docs -o src/shared/api/schema.d.ts"
> ```
>
> **npm 12 note:** `npm install --dry-run` (and `--package-lock-only`) fails with `EALLOWREMOTE` on `@tailwindcss/oxide-wasm32-wasi`. npm 12 opens packages with bundled dependencies by tarball URL in those modes, and its default `allow-remote=none` blocks the URL. Normal `npm install` / `npm ci` are not affected.

> **Pinned on purpose:** React Router **7** and FullCalendar **6** (their newer majors changed APIs; all design snippets use these). Don't run `npm update` across majors during the hackathon.

The scripts (`api:types`, `test`, `lint`) are listed in [08-frontend §12.1](../../08-frontend.md); the `npm pkg set` command above adds the two missing ones.

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

2. **Path alias in TypeScript:** the Vite template splits configs (`tsconfig.json` → `tsconfig.app.json`, `tsconfig.node.json`). Add to **both** `tsconfig.json` and `tsconfig.app.json`, and **don't add `baseUrl`**: TypeScript 6 deprecates it (`TS5101`, the build fails), and `paths` resolves relative to the tsconfig file without it:

   ```json
   { "compilerOptions": { "paths": { "@/*": ["./src/*"] } } }
   ```

3. **ESLint:** replace `eslint.config.js` with [08-frontend §12.4](../../08-frontend.md) (feature boundaries).

## 4. Tailwind v4 + shadcn/ui + theme

First make Tailwind v4 detectable. shadcn's preflight fails with *"No Tailwind CSS configuration found"* until a CSS file imports Tailwind. Replace the template's demo stylesheet:

```bash
printf '@import "tailwindcss";\n' > src/index.css
```

Then:

```bash
npx shadcn@4 init          # component library: Base UI · preset: Nova (Lucide icons + Geist font)
```

Base UI components use a `render` prop where the Radix flavour uses `asChild`; keep that in mind when copying examples from the web. Then point shadcn at our folders in `components.json`:

```json
{
  "tailwind": { "css": "src/app/theme.css" },
  "aliases": {
    "components": "@/shared/ui",
    "ui": "@/shared/ui",
    "utils": "@/shared/lib/utils",
    "lib": "@/shared/lib",
    "hooks": "@/shared/lib/hooks"
  }
}
```

(Edit only these keys and keep the rest of the generated file. `tailwind.css` must follow the CSS when it moves to `src/app/theme.css`, or later `shadcn add` runs write their CSS variables into a deleted file. Recent shadcn versions add the official `cn` package, a drop-in replacement for clsx + tailwind-merge: `utils.ts` just re-exports it.)

- `init` created files at its default locations (`src/lib/utils.ts`, `src/components/ui/button.tsx`). Move them to match the aliases:

  ```bash
  mkdir -p src/shared/lib src/shared/ui src/app
  mv src/lib/utils.ts src/shared/lib/utils.ts
  mv src/components/ui/*.tsx src/shared/ui/
  mv src/index.css src/app/theme.css
  rmdir src/lib src/components/ui src/components
  ```

- In `src/app/theme.css` (the CSS shadcn generated), **merge** the design tokens from [08-frontend §10](../../08-frontend.md) (keep one `:root` and one `.dark` block). Change the token values (e.g. `--primary`, `--ring`, `--accent`) but keep shadcn's `@import` lines and extra tokens (sidebar, chart). It's imported once in `src/main.tsx` (§6).
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

`npm run api:types` reads the backend's OpenAPI document, so it needs **E01-S02** (backend skeleton) running (guide 02 §6). Until then, create a placeholder so the client compiles, and replace it with the generated file as soon as the backend is up:

```ts
// src/shared/api/schema.d.ts: TEMPORARY placeholder until `npm run api:types` can run (E01-S04-T1)
export interface paths {}
export interface components {
  schemas: Record<string, never>;
}
```

With the backend running:

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

`main.tsx` imports `./app/router`, which §7 (E03-S01) fills in with the full route table. Create a placeholder now so the app builds:

```tsx
// src/app/router.tsx: placeholder, replaced by the full route table in E03-S01
import { createBrowserRouter } from "react-router";

export const router = createBrowserRouter([
  { path: "*", element: <p className="p-8 text-2xl font-semibold">Virtual Clubroom</p> },
]);
```

Then remove the Vite template leftovers and set the page title:

```bash
rm -f src/App.tsx src/App.css src/index.css src/assets/react.svg src/assets/vite.svg src/assets/hero.png public/icons.svg
sed -i 's|<title>frontend</title>|<title>Virtual Clubroom</title>|' index.html
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
npm run lint && npm test && npm run build      # npm test = vitest run --passWithNoTests
```

- Open `http://localhost:5173/login` → **Login with 42** → you come back logged in (the backend must run with `APP_PUBLIC_URL=http://localhost:5173`, which `run-dev.sh` does).
- The local admin login form works too.

## 9. Done when

- [ ] Lint, tests and build pass; importing `@/features/clubs/CreateClubWizard` from another feature fails lint.
- [ ] `schema.d.ts` committed; a typed `api.GET` call works in the browser.
- [ ] Every route renders (placeholders OK); 404 page works; theme toggle works.
- [ ] Login with 42 and local login both work through `localhost:5173`.
