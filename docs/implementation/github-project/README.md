# Backlog → GitHub Projects

Imports the whole UNIX_CLUB backlog (16 epics, 63 stories, 179 tasks) into a **GitHub Project** as **draft items** with custom fields, so the team can assign, filter and track work on a board.

GitHub Projects has no CSV import, so this folder uses the official GitHub CLI (`gh project …`). CSV files are included as well for spreadsheets or other tools.

| File | What it is |
|------|-----------|
| `import_github_project.py` | The importer (Python 3.9+, standard library only, uses `gh`). Idempotent and resumable. |
| `items.json` | Generated import data: every story and task with title, body and field values. |
| `build_items.py` | Regenerates `items.json` and the CSVs from `../backlog/*.md`. Run it after editing the backlog. |
| `backlog-stories.csv` | One row per story (ID, title, epic, priority, milestone, suggested owner, estimate, MVP saving, branch). |
| `backlog-tasks.csv` | One row per task (ID, story, description, layer, estimate, dependencies, suggested owner). |

---

## 1. Why draft items (not issues)

Our branches live in the organisers' repository (D-36), but creating 63+ issues there would flood a repository shared with other teams. **Draft items live only in your project.** If you ever want a real issue, open the item and use **Convert to issue** in a repository you own.

Pull requests can't be linked to draft items automatically. The story ID in the branch name and PR title (`feat(E04-S01): …`) is the link, and there is a **PR** text field for the URL.

## 2. What gets created

**Project:** `UNIX_CLUB · Virtual Clubroom` (or your existing project with `--project-number`).

**Custom fields**

| Field | Type | Values |
|-------|------|--------|
| Backlog ID | Text | `E04-S01`, `E04-S01-T3` |
| Level | Single select | Story · Task |
| Epic | Single select | `E01 Foundation` … `E16 Deploy & submission` |
| Priority | Single select | Must · Should · Could |
| Delivery milestone | Single select | `M0 Skeleton + login` … `M5 Ship` (named so because "Milestone" is a built-in GitHub field) |
| Suggested owner | Single select | A · B · C · A + B · A + C · B + C · A + B + C (the rebalanced split of [backlog §5](../backlog/README.md#5-suggested-assignment)) |
| Estimate (h) | Number | Ideal hours |
| MVP saving (h) | Number | Hours saved by the story's MVP cut (Must stories) |
| Layer | Single select | BE · FE · DB · TEST · OPS · DOC · BE+FE (tasks) |
| Story | Text | Parent story ID (tasks) |
| Depends on | Text | Task dependencies (tasks) |
| PR | Text | Fill in yourselves with the PR URL |

**Items**
- **Stories** (default): title `E04-S01 · Request the creation of a club`. The body has the user story, acceptance criteria, a **task checklist** with layer/estimate/owner/dependencies, the MVP cut, the branch name and design references.
- **Tasks** (`--with-tasks`): title `E04-S01-T3 · …`. The body has the description, dependencies, design reference and parent story.

Story-level items are recommended: one story = one branch = one PR. Add task items only if you want to assign BE and FE halves of a story to different people on the board. The story bodies already carry the task checklist.

## 3. Run the import

```bash
cd docs/implementation/github-project

# 1. once: give gh permission to manage Projects
gh auth refresh -s project

# 2. see what will happen (no GitHub calls)
python3 import_github_project.py --owner @me --dry-run

# 3. import the 63 stories into a new project owned by you
python3 import_github_project.py --owner @me

#    …or into an existing project (number from its URL: github.com/users/<you>/projects/<N>)
python3 import_github_project.py --owner @me --project-number 3

#    …or an organisation project
python3 import_github_project.py --owner <org-login>

# optional: also add the 179 task items to the same project
python3 import_github_project.py --owner @me --project-number <N> --with-tasks
```

| Option | Effect |
|--------|--------|
| `--dry-run` | Print the plan and the number of writes; call nothing |
| `--project-number N` | Use an existing project instead of creating one |
| `--with-tasks` | Also create task items |
| `--limit N` | Only the first N items (trial run). Items are ordered story, its tasks, next story… |
| `--update-existing` | Re-apply field values on items already present (e.g. after adding a missing select option) |
| `--delay S` | Pause after each write (default 0.6 s) |
| `--verbose` | Print every `gh` command |

**Duration and rate limits.** Each item takes ~8 writes (create + fields).
- Stories alone: ≈ 550 writes, roughly 10–15 minutes.
- With tasks: ≈ 2,000 writes.

GitHub throttles bursts of writes ("secondary rate limit"). The script then waits and retries automatically (30 s, 60 s, 120 s…). If it still stops, **run the same command again**: items already present are skipped (matched by the backlog ID at the start of the title).

**Requirements:** GitHub CLI ≥ 2.40, Python ≥ 3.9, a token with the `project` scope. Collaborators must be added to the project (**Settings → Manage access**) to edit items.

## 4. Set up the views (manual, ~5 minutes)

The GitHub API cannot create project views, so set these up once in the web UI.

1. **Status values.** Project **Settings → Fields → Status**: rename the options to `Backlog`, `Ready`, `In progress`, `In review`, `Done` (the workflow of [backlog §6](../backlog/README.md#6-tracking-status)). New items start with no status. To set `Backlog` in bulk, open a Table view, set one cell, copy it, select the rest of the column and paste.
2. **Board** (default view): layout *Board*, column by **Status**, filter `level:Story`, card fields: Priority, Suggested owner, Estimate (h), Assignees.
3. **By owner**: layout *Table*, group by **Suggested owner**, filter `level:Story`, sort by Delivery milestone. Use it to hand out work: assign people, then switch the group-by to **Assignees**.
4. **Must first**: layout *Table*, filter `priority:Must -status:Done`, group by **Delivery milestone**, sum of **Estimate (h)** shown in the group headers (field sum option). It's your burn-down.
5. **My work**: layout *Board*, filter `assignee:@me -status:Done`.
6. *(If tasks imported)* **Tasks**: layout *Table*, filter `level:Task`, group by **Story**.

## 5. Day-to-day

- **Pick work:** move a `Ready` story to `In progress`, assign yourself, create the branch named in the body.
- **Open the PR:** set Status `In review` and paste the URL into **PR**.
- **After the squash merge:** set Status `Done` and tick the task checklist in the body.
- **Backlog changes:** edit the markdown in `../backlog/`, run `python3 build_items.py`, then `python3 import_github_project.py --owner @me --project-number <N>` to add new items. Use `--update-existing` to refresh fields; existing titles and bodies are not overwritten.

## 6. CSV files

- **Google Sheets / Excel:** open `backlog-stories.csv` or `backlog-tasks.csv` (UTF-8 with BOM, comma-separated) to get a sortable, filterable tracker.
- **Other tools** (Jira, Linear, Trello CSV importers): map `Backlog ID` → key/summary prefix, `Title` → summary, `Priority`, `Estimate (h)` → original estimate, `Epic` → epic link.
