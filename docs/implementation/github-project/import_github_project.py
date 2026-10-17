#!/usr/bin/env python3
"""
Imports the UNIX_CLUB backlog into a GitHub Project (Projects v2) as draft items, using the GitHub CLI.

    gh auth refresh -s project                                        # once: give gh the 'project' scope
    python3 import_github_project.py --owner @me                      # new project, 63 stories
    python3 import_github_project.py --owner @me --with-tasks         # + 179 task items
    python3 import_github_project.py --owner @me --project-number 3   # into an existing project
    python3 import_github_project.py --owner @me --dry-run            # show the plan, call nothing

Idempotent and resumable: items whose title already starts with their backlog ID are skipped, so an
interrupted run (rate limit, network) can simply be started again. Standard library only (Python >= 3.9).
Requires GitHub CLI >= 2.40 (node-ID mode of `gh project item-edit`).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ID_IN_TITLE = re.compile(r"^(E\d{2}-S\d{2}(?:-T\d+)?) · ")
RETRYABLE = ("rate limit", "secondary", "abuse", "too quickly", "502", "503", "504", "timeout", "timed out",
             "connection reset", "eof")


class GhError(RuntimeError):
    pass


class Gh:
    def __init__(self, binary: str, delay: float, verbose: bool) -> None:
        self.binary = binary
        self.delay = delay
        self.verbose = verbose

    def json(self, *args: str, mutation: bool = False) -> dict:
        """Runs a gh command that prints JSON and returns the parsed object."""
        out = self.run(*args, mutation=mutation)
        parsed = json.loads(out) if out else {}
        if not isinstance(parsed, dict):
            raise GhError(f"Unexpected output from gh {' '.join(args[:2])}: {out[:200]}")
        return parsed

    def run(self, *args: str, mutation: bool = False) -> str:
        cmd = [self.binary, *args]
        for attempt in range(6):
            if self.verbose:
                print("  $", " ".join(cmd), file=sys.stderr)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode == 0:
                if mutation and self.delay:
                    time.sleep(self.delay)          # stay below GitHub's secondary rate limits
                return proc.stdout.strip()
            err = (proc.stderr or proc.stdout).strip()
            if attempt < 5 and any(token in err.lower() for token in RETRYABLE):
                wait = 30 * (2 ** attempt)
                print(f"  ! GitHub asked us to slow down ({err.splitlines()[0][:120]}); retrying in {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            raise GhError(f"{' '.join(cmd[:4])} … failed: {err}")
        raise GhError("unreachable")


def check_auth(gh: Gh) -> None:
    proc = subprocess.run([gh.binary, "auth", "status"], capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit("gh is not logged in. Run: gh auth login")
    status = (proc.stdout + proc.stderr).lower()
    scopes = next((line for line in status.splitlines() if "token scopes" in line), None)
    if scopes is None:
        print("  ! Could not read token scopes (fine-grained token?). Make sure it can write Projects.",
              file=sys.stderr)
    elif not re.search(r"(?<!read:)\bproject\b", scopes):
        sys.exit("Your gh token lacks the 'project' scope. Run: gh auth refresh -s project")


def ensure_project(gh: Gh, owner: str, number: int | None, title: str) -> dict:
    if number is not None:
        project = gh.json("project", "view", str(number), "--owner", owner, "--format", "json")
        print(f"Using project #{project['number']}: {project.get('title')} ({project.get('url')})")
        return project
    project = gh.json("project", "create", "--owner", owner, "--title", title, "--format", "json", mutation=True)
    print(f"Created project #{project['number']}: {title} ({project.get('url')})")
    return project


def list_fields(gh: Gh, owner: str, number: int) -> dict[str, dict]:
    data = gh.json("project", "field-list", str(number), "--owner", owner, "--format", "json", "--limit", "100")
    return {f["name"]: f for f in data.get("fields", [])}


def ensure_fields(gh: Gh, owner: str, number: int, specs: list[dict]) -> dict[str, dict]:
    fields = list_fields(gh, owner, number)
    for spec in specs:
        name = spec["name"]
        if name in fields:
            if spec["type"] == "SINGLE_SELECT":
                have = {o["name"] for o in fields[name].get("options", [])}
                missing = [o for o in spec["options"] if o not in have]
                if missing:
                    print(f"  ! Field '{name}' exists but lacks options {missing}: add them in the project "
                          f"settings, then re-run with --update-existing.", file=sys.stderr)
            continue
        args = ["project", "field-create", str(number), "--owner", owner, "--name", name,
                "--data-type", spec["type"], "--format", "json"]
        if spec["type"] == "SINGLE_SELECT":
            args += ["--single-select-options", ",".join(spec["options"])]
        gh.run(*args, mutation=True)
        print(f"  + field '{name}' ({spec['type'].lower().replace('_', ' ')})")
    return list_fields(gh, owner, number)       # re-read to get option IDs


def existing_items(gh: Gh, owner: str, number: int) -> dict[str, str]:
    data = gh.json("project", "item-list", str(number), "--owner", owner, "--format", "json", "--limit", "3000")
    found = {}
    for item in data.get("items", []):
        title = item.get("title") or (item.get("content") or {}).get("title") or ""
        match = ID_IN_TITLE.match(title)
        if match:
            found[match.group(1)] = item["id"]
    return found


def set_fields(gh: Gh, project_id: str, item_id: str, values: dict, fields: dict[str, dict]) -> None:
    for name, value in values.items():
        field = fields.get(name)
        if field is None:
            print(f"  ! unknown field '{name}', skipped", file=sys.stderr)
            continue
        args = ["project", "item-edit", "--id", item_id, "--field-id", field["id"], "--project-id", project_id]
        options = field.get("options")
        if options is not None:                                   # single select
            option = next((o for o in options if o["name"] == value), None)
            if option is None:
                print(f"  ! option '{value}' missing in field '{name}', skipped", file=sys.stderr)
                continue
            args += ["--single-select-option-id", option["id"]]
        elif isinstance(value, (int, float)):
            args += ["--number", f"{value:g}"]
        else:
            args += ["--text", str(value)]
        gh.run(*args, "--format", "json", mutation=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Import the UNIX_CLUB backlog into a GitHub Project.")
    ap.add_argument("--owner", required=True, help='Project owner: a user login, an org login, or "@me"')
    ap.add_argument("--project-number", type=int, help="Existing project number (default: create a new project)")
    ap.add_argument("--title", help="Title for a new project (default from items.json)")
    ap.add_argument("--with-tasks", action="store_true", help="Also create one item per task (179 more items)")
    ap.add_argument("--update-existing", action="store_true",
                    help="Re-apply field values on items that already exist (titles/bodies are left untouched)")
    ap.add_argument("--limit", type=int, help="Only process the first N items (for a trial run)")
    ap.add_argument("--delay", type=float, default=0.6, help="Seconds to wait after each write (default 0.6)")
    ap.add_argument("--items", default=str(HERE / "items.json"), help="Path to items.json")
    ap.add_argument("--gh", default="gh", help="Path to the gh binary")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan without calling GitHub")
    ap.add_argument("--verbose", action="store_true", help="Print every gh command")
    args = ap.parse_args()

    data = json.loads(Path(args.items).read_text(encoding="utf-8"))
    items = [i for i in data["items"] if args.with_tasks or i["level"] == "Story"]
    if args.limit:
        items = items[: args.limit]
    title = args.title or data["project_title"]

    if args.dry_run:
        target = f"project #{args.project_number}" if args.project_number else f"new project '{title}'"
        print(f"Dry run → owner {args.owner}, {target}")
        print("Fields:", ", ".join(f"{f['name']} ({f['type']})" for f in data["fields"]))
        print(f"Items: {len(items)} ({sum(i['level'] == 'Story' for i in items)} stories, "
              f"{sum(i['level'] == 'Task' for i in items)} tasks)")
        for item in items[:5]:
            print(f"  - {item['title']}  {item['fields']}")
        writes = len(items) * (1 + 7) + len(data["fields"]) + 1
        print(f"≈ {writes} GitHub writes; at --delay {args.delay}s this takes ≈ {writes * (args.delay + 0.8) / 60:.0f} min")
        return

    gh = Gh(args.gh, args.delay, args.verbose)
    check_auth(gh)
    project = ensure_project(gh, args.owner, args.project_number, title)
    number, project_id = int(project["number"]), project["id"]
    fields = ensure_fields(gh, args.owner, number, data["fields"])
    present = existing_items(gh, args.owner, number)

    created = updated = skipped = 0
    for index, item in enumerate(items, 1):
        prefix = f"[{index}/{len(items)}] {item['backlog_id']}"
        if item["backlog_id"] in present:
            if args.update_existing:
                set_fields(gh, project_id, present[item["backlog_id"]], item["fields"], fields)
                updated += 1
                print(f"{prefix} fields re-applied")
            else:
                skipped += 1
                print(f"{prefix} already in project, skipped")
            continue
        new = gh.json("project", "item-create", str(number), "--owner", args.owner, "--title", item["title"],
                     "--body", item["body"], "--format", "json", mutation=True)
        set_fields(gh, project_id, new["id"], item["fields"], fields)
        created += 1
        print(f"{prefix} created")

    print(f"\nDone: {created} created, {updated} updated, {skipped} skipped.")
    print(f"Open: {project.get('url') or f'gh project view {number} --owner {args.owner} --web'}")
    print("Next: set up the views as described in README.md §4 (views can't be created through the API).")


if __name__ == "__main__":
    try:
        main()
    except GhError as error:
        sys.exit(f"\nStopped: {error}\nFix the cause and run the same command again; finished items are skipped.")
