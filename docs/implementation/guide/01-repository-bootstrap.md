# Guide 01 — Repository bootstrap

**Goal:** `UNIX_CLUB/main` exists in the official repository with the team folder, conventions, hooks and local infrastructure running.

Backlog: **E01-S01** (owner A). Time: ~2 h.

---

## 1. Create the integration branch

```bash
git clone git@github.com:megyant/Hackathon_SA_2026.git
cd Hackathon_SA_2026
git switch -c UNIX_CLUB/main origin/main
mkdir -p UNIX_CLUB/{backend,frontend,deploy/seaweedfs,.githooks,docs}
```

## 2. Base files

`UNIX_CLUB/.gitignore`

```gitignore
# Secrets
.env

# Java / Maven
backend/target/
*.class
*.log

# Node / Vite
frontend/node_modules/
frontend/dist/
frontend/coverage/

# IDE / OS
.idea/
*.iml
.vscode/*
!.vscode/extensions.json
.DS_Store
```

`UNIX_CLUB/.editorconfig`

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4
trim_trailing_whitespace = true

[*.{ts,tsx,js,json,css,yml,yaml,md}]
indent_size = 2
```

## 3. Conventions and hooks

1. Copy [CONTRIBUTING.md](../CONTRIBUTING.md) to `UNIX_CLUB/CONTRIBUTING.md`.
2. Create the three hooks from [CONTRIBUTING §5](../CONTRIBUTING.md#5-local-git-hooks-r-30) in `UNIX_CLUB/.githooks/` (`commit-msg`, `pre-commit`, `pre-push`), then:

```bash
chmod +x UNIX_CLUB/.githooks/*
git config core.hooksPath UNIX_CLUB/.githooks
```

## 4. Local infrastructure files

Copy them verbatim from the design:

| File | Source |
|------|--------|
| `UNIX_CLUB/compose.yaml` | [09-deployment §4.1](../../09-deployment.md) |
| `UNIX_CLUB/compose.dev.yaml` | [09-deployment §4.2](../../09-deployment.md) |
| `UNIX_CLUB/deploy/seaweedfs/s3.json` | [09-deployment §6](../../09-deployment.md) |
| `UNIX_CLUB/.env.example` | [09-deployment §7](../../09-deployment.md) |

(`compose.prod.yaml`, the Dockerfiles and nginx come in E16-S01.)

## 5. First run

```bash
cd UNIX_CLUB
cp .env.example .env          # set DB_PASSWORD, S3 keys (matching s3.json); FT_* when available
docker compose -f compose.yaml -f compose.dev.yaml up -d
docker compose -f compose.yaml -f compose.dev.yaml ps     # postgres, redis, seaweedfs → healthy; mailpit → running
```

Mailpit UI: <http://localhost:8025>.

## 6. Commit and publish the integration branch

```bash
cd ..                                            # repository root
git add UNIX_CLUB
git commit -m "chore(E01-S01): bootstrap UNIX_CLUB workspace"
ALLOW_INTEGRATION_PUSH=1 git push -u origin UNIX_CLUB/main
```

Then tell the team. Every developer:

```bash
git fetch origin && git switch UNIX_CLUB/main
git config core.hooksPath UNIX_CLUB/.githooks
cp UNIX_CLUB/.env.example UNIX_CLUB/.env      # fill in the shared secrets
```

## 7. Done when

- [ ] `origin/UNIX_CLUB/main` exists and contains only `UNIX_CLUB/`.
- [ ] `git commit -m "update"` is rejected by the hook; `chore(E01-S01): …` passes.
- [ ] Compose services are healthy on every machine.
