# Guide 00 — Prerequisites and accounts

**Goal:** every developer's machine can build and run the project, and the external accounts with waiting times (42 OAuth, DNS for email, Cloudflare hostname) are requested **in the first hour**.

Backlog items: E01-S01-T4, E02-S01-T1, E12-S03-T1, E16-S02-T1.

---

## 1. Tools (every developer)

| Tool | Version | Check |
|------|---------|-------|
| Git | ≥ 2.40 | `git --version` |
| JDK | **21** (Eclipse Temurin recommended) | `java -version` → `21.x` |
| Maven | not required: the project ships a Maven wrapper (`./mvnw`, Maven 3.9.16). Only the person creating the wrapper needs Maven or Docker | `./mvnw -v` |
| Node.js + npm | **24 LTS** | `node -v` → `v24.x` |
| Docker Engine + Compose v2 | recent | `docker compose version` |
| bash | ≥ 4 (the skeleton script uses associative arrays; macOS users: `brew install bash`) | `bash --version` |
| curl, jq | any | `curl --version`, `jq --version` |

**IDE suggestions:** IntelliJ IDEA (Spring and JPA support, run configurations) for the backend; VS Code with ESLint, Tailwind CSS IntelliSense and Prettier for the frontend.

**Local ports used:** 5173 (Vite), 8080 (backend in dev, proxy in local prod), 5432 (Postgres), 6379 (Redis), 8333 (SeaweedFS S3), 1025/8025 (Mailpit SMTP/UI). Free them before starting.

---

## 2. External accounts (first hour, suggested owner: B)

These have waiting times or DNS propagation, so start them before writing code.

### 2.1 42 OAuth application (E02-S01-T1)

1. `https://profile.intra.42.fr/oauth/applications` → **Register a new app**.
2. Redirect URIs (one per line):
   ```text
   http://localhost:5173/login/oauth2/code/fortytwo
   http://localhost:8080/login/oauth2/code/fortytwo
   https://42clubroom.ensui.dev/login/oauth2/code/fortytwo
   ```
3. Scope `public`. Copy UID → `FT_CLIENT_ID` and Secret → `FT_CLIENT_SECRET`.

### 2.2 Resend sending domain (E12-S03-T1)

1. Create a Resend account → **Domains → Add** `42clubroom.ensui.dev` (R-25).
2. Add the shown DNS records (DKIM TXT, SPF MX + TXT on `send.…`, optional DMARC) in **Cloudflare DNS** for `ensui.dev` (DNS only, grey cloud).
3. When verified: **API Keys → Create** (sending access, restricted to this domain) → `SMTP_PASSWORD`.

Details: [09-deployment §10](../../09-deployment.md).

### 2.3 Cloudflare hostname (E16-S02-T1, preparation)

Decide **option A** (route from an existing `cloudflared` connector to the demo host) or **option B** (dedicated connector container with a tunnel token). Prepare the public hostname `42clubroom.ensui.dev`. It only needs to point to a running stack from M1 on. Details: [09-deployment §8](../../09-deployment.md).

---

## 3. Secrets

- Agree on **one private channel** (password manager or private chat) for: `FT_CLIENT_SECRET`, `SMTP_PASSWORD` (Resend key), `DB_PASSWORD`, `S3_SECRET_KEY`, bootstrap admin password, `CLOUDFLARE_TUNNEL_TOKEN` (option B).
- `.env` is **never committed**; the `pre-commit` hook refuses it ([CONTRIBUTING §5](../CONTRIBUTING.md#5-local-git-hooks-r-30)).
- Each developer keeps their own `UNIX_CLUB/.env` copied from `.env.example`.

---

## 4. Done when

- [ ] All tools above report the expected versions on every machine.
- [ ] 42 app registered; credentials shared privately.
- [ ] Resend domain added (verification may still be pending).
- [ ] Cloudflare option chosen; hostname prepared.
