#!/usr/bin/env python3
"""
Builds the GitHub Projects import data from the backlog markdown.

Reads   ../backlog/E*.md
Writes  items.json            (input of import_github_project.py)
        backlog-stories.csv   (spreadsheet-friendly, one row per story)
        backlog-tasks.csv     (spreadsheet-friendly, one row per task)

Run it again whenever the backlog markdown changes:
    python3 build_items.py
Standard library only (Python >= 3.9).
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKLOG = HERE.parent / "backlog"
DOCS_ROOT = HERE.parent.parent  # .../docs

PROJECT_TITLE = "UNIX_CLUB · Virtual Clubroom"

EPIC_LABELS = {
    "E01": "E01 Foundation",
    "E02": "E02 Identity & auth",
    "E03": "E03 Shell & design system",
    "E04": "E04 Club lifecycle",
    "E05": "E05 Spaces & access",
    "E06": "E06 Discovery & landing",
    "E07": "E07 Membership & joining",
    "E08": "E08 Media uploads",
    "E09": "E09 Forum",
    "E10": "E10 Real-time & chat",
    "E11": "E11 Calendar & events",
    "E12": "E12 Notifications & email",
    "E13": "E13 Governance",
    "E14": "E14 Archival & history",
    "E15": "E15 Admin console",
    "E16": "E16 Deploy & submission",
}

MILESTONE_LABELS = {
    "M0": "M0 Skeleton + login",
    "M1": "M1 Clubs exist",
    "M2": "M2 Community",
    "M3": "M3 Calendar",
    "M4": "M4 Lifecycle",
    "M5": "M5 Ship",
}

OWNER_OPTIONS = ["A", "B", "C", "A + B", "A + C", "B + C", "A + B + C"]
LAYER_OPTIONS = ["BE", "FE", "DB", "TEST", "OPS", "DOC", "BE+FE"]

# Suggested assignment (backlog/README.md §5): B works full-stack on these epics.
B_FULL_STACK = {"E05", "E08", "E09", "E10", "E11", "E12"}
# First-hour ops tasks handed to B (backlog/README.md §5.2, row 0).
OWNER_OVERRIDES = {"E02-S01-T1": "B", "E16-S02-T1": "B"}

FIELDS = [
    {"name": "Backlog ID", "type": "TEXT"},
    {"name": "Level", "type": "SINGLE_SELECT", "options": ["Story", "Task"]},
    {"name": "Epic", "type": "SINGLE_SELECT", "options": list(EPIC_LABELS.values())},
    {"name": "Priority", "type": "SINGLE_SELECT", "options": ["Must", "Should", "Could"]},
    {"name": "Delivery milestone", "type": "SINGLE_SELECT", "options": list(MILESTONE_LABELS.values())},
    {"name": "Suggested owner", "type": "SINGLE_SELECT", "options": OWNER_OPTIONS},
    {"name": "Estimate (h)", "type": "NUMBER"},
    {"name": "MVP saving (h)", "type": "NUMBER"},
    {"name": "Layer", "type": "SINGLE_SELECT", "options": LAYER_OPTIONS},
    {"name": "Story", "type": "TEXT"},
    {"name": "Depends on", "type": "TEXT"},
    {"name": "PR", "type": "TEXT"},
]

LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def req(pattern: str, text: str, flags: int = 0) -> re.Match:
    """re.search that fails loudly: the backlog format is fixed, a miss means the markdown was edited wrongly."""
    match = re.search(pattern, text, flags)
    if match is None:
        raise ValueError(f"Backlog format error: {pattern!r} not found near: {text[:80]!r}")
    return match


def plain_links(text: str, source_dir: Path) -> str:
    """Relative markdown links don't resolve inside GitHub draft items: turn them into 'label (docs/path)'."""
    def repl(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:")):
            return m.group(0)
        path = target.split("#", 1)[0]
        resolved = (source_dir / path).resolve() if path else None
        if resolved is None:
            return label
        try:
            rel = resolved.relative_to(DOCS_ROOT.parent)
        except ValueError:
            rel = Path(os.path.relpath(resolved, DOCS_ROOT.parent))
        return f"{label} (`{rel.as_posix()}`)"
    return LINK.sub(repl, text)


def task_owner(epic: str, task_id: str, layer: str, story_track: str) -> str:
    if task_id in OWNER_OVERRIDES:
        return OWNER_OVERRIDES[task_id]
    if layer == "DOC" and "All" in story_track:
        return "A + B + C"                         # shared README / rehearsal / slides work
    if epic in B_FULL_STACK:
        return "B"
    if epic == "E06" and layer in ("BE", "DB"):
        return "B"
    if layer == "FE" or (layer == "TEST" and epic == "E16"):
        return "C"
    if layer == "BE+FE":
        return "A + C"
    return "A"


def merge_owners(owners: list[str]) -> str:
    letters = sorted({part.strip() for o in owners for part in o.split("+")})
    return " + ".join(letters)


def num(x: float) -> str:
    return f"{x:g}"


def parse_epic(path: Path) -> tuple[dict, list[dict]]:
    text = path.read_text(encoding="utf-8")
    epic_id = path.name[:3]
    epic_title = req(r"^# E\d{2} — (.+)$", text, re.M).group(1)
    sections = re.split(r"(?=^### E\d{2}-S\d{2} · )", text, flags=re.M)[1:]
    stories = []
    for sec in sections:
        sec = re.sub(r"\n---\s*$", "\n", sec.strip() + "\n")
        sid, title = req(r"^### (E\d{2}-S\d{2}) · (.+)", sec).groups()
        meta = req(r"\*\*Priority:\*\* (\w+) · \*\*Milestone:\*\* (M\d) · \*\*Track:\*\* ([^·]+?) · "
                   r"\*\*Estimate:\*\* ([\d.]+) h", sec)
        priority, milestone, track, estimate = meta.group(1), meta.group(2), meta.group(3).strip(), float(meta.group(4))
        story_text = sec.split("\n", 1)[1]
        story_text = story_text.replace(meta.group(0), "").strip()
        tasks = []
        for row in re.findall(r"^\| (E\d{2}-S\d{2}-T\d+) \| (.+?) \| ([A-Z+]+) \| ([\d.]+) \| (.+?) \| (.+?) \|$",
                              sec, re.M):
            tid, desc, layer, est, deps, ref = row
            tasks.append({"id": tid, "desc": desc, "layer": layer, "estimate": float(est),
                          "depends": deps, "ref": ref, "owner": task_owner(epic_id, tid, layer, track)})
        mvp = re.search(r"\*\*MVP cut \(saves ~([\d.]+) h\):\*\* (.+)", sec)
        branch = re.search(r"\*\*Branch:\*\* (.+)", sec)
        branch_name = re.search(r"`([^`]+)`", branch.group(1)) if branch else None
        intro = re.split(r"^\| Task \|", story_text, flags=re.M)[0].strip()
        stories.append({
            "id": sid, "title": title, "priority": priority, "milestone": milestone, "track": track,
            "estimate": estimate, "intro": intro, "tasks": tasks,
            "mvp_saving": float(mvp.group(1)) if mvp else 0.0, "mvp_text": mvp.group(2).strip() if mvp else "",
            "branch": branch.group(1).strip() if branch else "",
            "branch_name": branch_name.group(1) if branch_name else "",
            "owner": merge_owners([t["owner"] for t in tasks]) if tasks else "A",
        })
    return {"id": epic_id, "title": epic_title, "file": path.name}, stories


def story_body(epic: dict, s: dict) -> str:
    src = BACKLOG
    lines = [
        f"**Epic:** {epic['id']} — {epic['title']}  ",
        f"**Priority:** {s['priority']} · **Milestone:** {MILESTONE_LABELS[s['milestone']]} · "
        f"**Estimate:** {num(s['estimate'])} h · **Suggested owner:** {s['owner']} (design track: {s['track']})",
        "",
        plain_links(s["intro"], src),
        "",
        "### Tasks",
    ]
    for t in s["tasks"]:
        lines.append(f"- [ ] **{t['id']}** · {plain_links(t['desc'], src)} — {t['layer']}, {num(t['estimate'])} h, "
                     f"owner {t['owner']}" + (f", depends on {t['depends']}" if t["depends"] not in ("—", "-") else ""))
    if s["mvp_text"]:
        lines += ["", f"### MVP cut (saves ~{num(s['mvp_saving'])} h)", plain_links(s["mvp_text"], src)]
    if s["branch"]:
        lines += ["", "### Branch", s["branch"]]
    refs = sorted({plain_links(t["ref"], src) for t in s["tasks"] if t["ref"] not in ("—", "-")})
    if refs:
        lines += ["", "### Design references"] + [f"- {r}" for r in refs]
    lines += ["", "---", f"Source: `docs/implementation/backlog/{epic['file']}` · "
              "Workflow: `docs/implementation/CONTRIBUTING.md`"]
    return "\n".join(lines).strip() + "\n"


def task_body(epic: dict, s: dict, t: dict) -> str:
    src = BACKLOG
    lines = [
        f"**Story:** {s['id']} · {s['title']}  ",
        f"**Epic:** {epic['id']} — {epic['title']}  ",
        f"**Layer:** {t['layer']} · **Estimate:** {num(t['estimate'])} h · **Suggested owner:** {t['owner']} · "
        f"**Priority:** {s['priority']} · **Milestone:** {MILESTONE_LABELS[s['milestone']]}",
        "",
        plain_links(t["desc"], src),
        "",
        f"**Depends on:** {t['depends']}  ",
        f"**Design reference:** {plain_links(t['ref'], src)}",
        "",
        f"**Branch (if worked separately):** `UNIX_CLUB/dev/feat({t['id']})/<short-desc>`",
        "",
        "---",
        f"Source: `docs/implementation/backlog/{epic['file']}`",
    ]
    return "\n".join(lines) + "\n"


def short(text: str, limit: int = 110) -> str:
    text = re.sub(r"[`*]", "", LINK.sub(lambda m: m.group(1), text))
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def main() -> None:
    items, story_rows, task_rows = [], [], []
    for path in sorted(BACKLOG.glob("E[0-9][0-9]-*.md")):
        epic, stories = parse_epic(path)
        for s in stories:
            common = {
                "Epic": EPIC_LABELS[epic["id"]],
                "Priority": s["priority"],
                "Delivery milestone": MILESTONE_LABELS[s["milestone"]],
            }
            items.append({
                "level": "Story",
                "backlog_id": s["id"],
                "title": f"{s['id']} · {s['title']}",
                "body": story_body(epic, s),
                "fields": {**common, "Backlog ID": s["id"], "Level": "Story", "Suggested owner": s["owner"],
                           "Estimate (h)": s["estimate"],
                           **({"MVP saving (h)": s["mvp_saving"]} if s["mvp_saving"] else {})},
            })
            story_rows.append([s["id"], s["title"], EPIC_LABELS[epic["id"]], s["priority"],
                               MILESTONE_LABELS[s["milestone"]], s["track"], s["owner"], num(s["estimate"]),
                               num(s["mvp_saving"]), len(s["tasks"]), s["branch_name"],
                               f"docs/implementation/backlog/{epic['file']}"])
            for t in s["tasks"]:
                items.append({
                    "level": "Task",
                    "backlog_id": t["id"],
                    "title": f"{t['id']} · {short(t['desc'])}",
                    "body": task_body(epic, s, t),
                    "fields": {**common, "Backlog ID": t["id"], "Level": "Task", "Story": s["id"],
                               "Layer": t["layer"], "Suggested owner": t["owner"], "Estimate (h)": t["estimate"],
                               **({"Depends on": t["depends"]} if t["depends"] not in ("—", "-") else {})},
                })
                task_rows.append([t["id"], s["id"], short(t["desc"], 300), t["layer"], num(t["estimate"]),
                                  "" if t["depends"] in ("—", "-") else t["depends"], t["owner"], s["priority"],
                                  MILESTONE_LABELS[s["milestone"]], EPIC_LABELS[epic["id"]]])

    (HERE / "items.json").write_text(json.dumps(
        {"project_title": PROJECT_TITLE, "fields": FIELDS, "items": items}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    with open(HERE / "backlog-stories.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Backlog ID", "Title", "Epic", "Priority", "Delivery milestone", "Design track",
                    "Suggested owner", "Estimate (h)", "MVP saving (h)", "Tasks", "Branch", "Source"])
        w.writerows(story_rows)
    with open(HERE / "backlog-tasks.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Backlog ID", "Story", "Description", "Layer", "Estimate (h)", "Depends on",
                    "Suggested owner", "Priority", "Delivery milestone", "Epic"])
        w.writerows(task_rows)

    n_s = sum(1 for i in items if i["level"] == "Story")
    print(f"items.json: {n_s} stories, {len(items) - n_s} tasks · backlog-stories.csv · backlog-tasks.csv")


if __name__ == "__main__":
    main()
