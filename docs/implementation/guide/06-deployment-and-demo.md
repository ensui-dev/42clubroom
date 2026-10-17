# Guide 06 — Deployment and demo

**Goal:** the app runs on `https://42clubroom.ensui.dev` through Cloudflare Tunnel, emails go out via Resend, redeploying is one command, and the demo (including scaling) is rehearsed.

Backlog: **E16-S01**, **E16-S02**, **E16-S03**, **E16-S04**, **E12-S03-T1**. Reference: [09-deployment.md](../../09-deployment.md).

---

## 1. Production images (E16-S01, Day 1 evening)

1. Create `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx/default.conf`, `compose.prod.yaml` from [09-deployment §3–§5](../../09-deployment.md).
2. Local prod-like run (no tunnel, Mailpit):

```bash
cd UNIX_CLUB
# in .env for this test: APP_PUBLIC_URL=http://localhost:8080, COOKIE_SECURE=false, SMTP_HOST=mailpit, SMTP_PORT=1025, SMTP_AUTH=false, SMTP_STARTTLS=false
docker compose -f compose.yaml -f compose.prod.yaml --profile demo up -d --build
docker compose -f compose.yaml -f compose.prod.yaml ps
```

3. Smoke test on `http://localhost:8080`: Login with 42, upload an image, open a chat (once it exists). `docker compose … logs -f backend` should show both replicas serving requests.

## 2. Publish `42clubroom.ensui.dev` (E16-S02)

1. On the demo host: clone the repo, `git switch UNIX_CLUB/main`, create `UNIX_CLUB/.env` with demo values:
   - `APP_PUBLIC_URL=https://42clubroom.ensui.dev`
   - `COOKIE_SECURE=true`
   - `HTTP_BIND=127.0.0.1` (connector on the same host) or the host's LAN IP (connector elsewhere)
   - Resend SMTP values and `MAIL_FROM` (§3)
2. Cloudflare:
   - **Option A** (existing connector): add the public hostname `42clubroom.ensui.dev` → `http://<HTTP_BIND>:8080` ([09-deployment §8.1](../../09-deployment.md)).
   - **Option B** (dedicated connector): new tunnel, hostname → `http://proxy:80`, token in `CLOUDFLARE_TUNNEL_TOKEN`, start with `COMPOSE_PROFILES=tunnel` ([§8.2](../../09-deployment.md)).
   - Cache bypass rules for `/api/*`, `/ws*`, `/ical/*`, `/media-private/*`; Rocket Loader off; WebSockets on ([§8.3](../../09-deployment.md)).
3. Redeploy script `UNIX_CLUB/deploy/deploy.sh`:

```bash
#!/usr/bin/env bash
# Redeploys the demo from the latest UNIX_CLUB/main. Run on the demo host.
# Option B (dedicated connector): COMPOSE_PROFILES=tunnel ./deploy/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."                       # → UNIX_CLUB/
git fetch origin
git switch UNIX_CLUB/main
git pull --ff-only origin UNIX_CLUB/main
docker compose -f compose.yaml -f compose.prod.yaml up -d --build --remove-orphans
docker compose -f compose.yaml -f compose.prod.yaml restart proxy   # re-resolve backend replicas
docker compose -f compose.yaml -f compose.prod.yaml ps
```

4. **Smoke test through Cloudflare** (not only on localhost):

| Check | How |
|-------|-----|
| HTTPS and SPA | Open `https://42clubroom.ensui.dev` |
| Login with 42 | Redirects back to `https://42clubroom.ensui.dev/` logged in (not `http://`) |
| WebSocket | Browser devtools → Network → WS `/ws` stays open > 2 min |
| Upload | Post a short video (< 90 MiB) and play it |
| Real client IP | `docker compose … logs proxy` shows visitor IPs, not the connector's |
| No edge caching of API | Response headers on `/api/me` show `cf-cache-status: DYNAMIC` or `BYPASS` |

## 3. Email via Resend (E12-S03)

1. Domain verified in Resend (started in guide 00).
2. `.env` on the demo host:

```dotenv
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=re_xxxxxxxxxxxxxxxxx
SMTP_AUTH=true
SMTP_STARTTLS=true
SMTP_SSL=false
MAIL_FROM="Virtual Clubroom <no-reply@42clubroom.ensui.dev>"
```

3. Trigger an email-by-default notification (e.g. invite a co-owner) → check Resend's **Emails** log, or:

```bash
docker compose -f compose.yaml -f compose.prod.yaml exec -T postgres \
  psql -U vclubroom -d vclubroom -c "select type, email_sent_at, email_attempts, email_last_error from notification.notifications order by created_at desc limit 5;"
```

Remember the free tier: **100 emails/day**. Don't send bulk test emails to real students.

## 4. Demo data (E16-S03)

Start once with the `demo` Spring profile on an empty database:

```bash
# in compose.prod.yaml → backend.environment: SPRING_PROFILES_ACTIVE: prod,demo   (only for the seeding run)
./deploy/deploy.sh
```

Seeders are idempotent: they skip if data exists. Switch back to `prod` afterwards.

## 5. Scaling demo (E16-S04)

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --scale backend=3
docker compose -f compose.yaml -f compose.prod.yaml restart proxy
docker compose -f compose.yaml -f compose.prod.yaml logs -f backend | grep -i "websocket\|stomp"
```

Two browsers (one in private mode, two different users) in the same Lounge chat: messages appear instantly in both, even though their WebSocket sessions live on different instances.

## 6. Rollback

```bash
git log --oneline origin/UNIX_CLUB/main | head          # find the last good squash commit
git switch --detach <sha>
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
# when fixed: git switch UNIX_CLUB/main && ./deploy/deploy.sh
```

Flyway migrations are forward-only. Rolling back code past a migration is fine as long as the newer migration only *added* things (the rule during the hackathon).

## 7. Troubleshooting

| Symptom | Likely cause → fix |
|---------|--------------------|
| 42 says "redirect URI invalid" | Redirect URI not registered, or built as `http://`. Check `APP_PUBLIC_URL`, the 42 app URIs, and that nginx forwards `X-Forwarded-Proto` ([09 §5](../../09-deployment.md)). |
| Login loops back to `/login` | `COOKIE_SECURE=true` over plain http (local test) → set `false` locally; or Redis down (sessions). |
| Upload `403 SignatureDoesNotMatch` | Presigned host ≠ request host: `S3_PUBLIC_ENDPOINT` must equal `APP_PUBLIC_URL`; nginx must pass `Host $http_host`; Vite proxy must keep `changeOrigin: false`. |
| Upload `413` | File > 100 MB (Cloudflare) or > nginx `client_max_body_size`. Respect the 90 MiB video limit. |
| WebSocket closes immediately | WebSockets disabled in Cloudflare, or nginx missing Upgrade headers; check `/ws` 101 in devtools. |
| Pushes arrive on one instance only | Redis relay not running (`RealtimeRedisConfig`), or different Redis per instance. |
| Emails stuck | `email_last_error` (wrong API key, unverified domain, `MAIL_FROM` not on the verified domain, daily cap). |
| Listener effects missing | `select listener_id, count(*) from public.event_publication where completion_date is null group by 1;` and check the backend logs. |
