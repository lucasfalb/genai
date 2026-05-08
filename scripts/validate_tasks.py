import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ALLOWED_GROUPS = {
    "CORE",
    "AUTH",
    "REGISTRY",
    "ENGINE",
    "PROMPTS",
    "RAG",
    "HANDOFF",
    "CHANNELS",
    "OBSERVABILITY",
    "SECURITY",
    "FRONTEND",
}
ALLOWED_STATUSES = {"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED"}
ALLOWED_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
REQUIRED_ATTRIBUTES = [
    "ID",
    "Group",
    "Status",
    "Stage Ref",
    "Spec Ref",
    "Priority",
    "Owner",
    "Created At",
    "Updated At",
]
REQUIRED_SECTIONS = [
    "Context",
    "Objectives",
    "Non-Goals",
    "Stage Boundaries",
    "Dependencies",
    "Inputs & Contracts",
    "Constraints & Rules",
    "Implementation Checklist",
    "Acceptance Criteria",
    "Verification",
    "Risks & Rollback",
    "Execution Log",
]


@dataclass
class TaskInfo:
    path: Path
    task_id: str
    status: str
    priority: str
    stage_ref: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_attribute_table(content: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in re.finditer(r"^\|\s*\*\*(?P<key>[^*]+)\*\*\s*\|\s*(?P<value>.*?)\s*\|$", content, re.MULTILINE):
        attrs[match.group("key").strip()] = match.group("value").strip()
    return attrs


def extract_section(content: str, section: str) -> str:
    match = re.search(rf"^## {re.escape(section)}\s*$", content, re.MULTILINE)
    if not match:
        return ""
    next_match = re.search(r"^##\s+", content[match.end() :], re.MULTILINE)
    if next_match:
        return content[match.end() : match.end() + next_match.start()]
    return content[match.end() :]


def validate_task_file(file_path: Path, repo_root: Path) -> tuple[list[str], TaskInfo | None]:
    content = read_text(file_path)
    errors: list[str] = []

    title_match = re.search(r"^# Task: (TASK-\d{3})\s+[-–—]\s+.+$", content, re.MULTILINE)
    if not title_match:
        errors.append("Missing or invalid title. Expected: # Task: TASK-XXX - Short title")

    filename_match = re.match(r"task_(\d{3})_[a-z0-9_]+\.md$", file_path.name)
    if file_path.name != "task_template.md" and not filename_match:
        errors.append("Invalid filename. Expected: task_XXX_slug.md")

    attrs = parse_attribute_table(content)
    for attr in REQUIRED_ATTRIBUTES:
        if attr not in attrs:
            errors.append(f"Missing attribute in table: {attr}")

    task_id = attrs.get("ID", "")
    if task_id and not re.fullmatch(r"TASK-\d{3}", task_id):
        errors.append("Invalid ID attribute. Expected TASK-XXX")
    if title_match and task_id and title_match.group(1) != task_id:
        errors.append("Title task ID does not match ID attribute")
    if filename_match and task_id and filename_match.group(1) != task_id[-3:]:
        errors.append("Filename task number does not match ID attribute")

    group = attrs.get("Group", "")
    if group and group not in ALLOWED_GROUPS:
        errors.append(f"Invalid Group: {group}")

    status = attrs.get("Status", "")
    if status and status not in ALLOWED_STATUSES:
        errors.append(f"Invalid Status: {status}")

    priority = attrs.get("Priority", "")
    if priority and priority not in ALLOWED_PRIORITIES:
        errors.append(f"Invalid Priority: {priority}")

    for date_attr in ("Created At", "Updated At"):
        value = attrs.get(date_attr, "")
        if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            errors.append(f"Invalid {date_attr}. Expected YYYY-MM-DD")

    stage_ref = attrs.get("Stage Ref", "").strip("`")
    if stage_ref:
        stage_path = (repo_root / stage_ref).resolve()
        try:
            stage_path.relative_to(repo_root.resolve())
        except ValueError:
            errors.append("Stage Ref must point inside the repository")
        if not stage_path.exists():
            errors.append(f"Stage Ref does not exist: {stage_ref}")

    spec_ref = attrs.get("Spec Ref", "").strip("`")
    if spec_ref and not (repo_root / spec_ref).exists():
        errors.append(f"Spec Ref does not exist: {spec_ref}")

    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^## {re.escape(section)}\s*$", content, re.MULTILINE):
            errors.append(f"Missing section: ## {section}")

    for checklist_section in ("Objectives", "Implementation Checklist", "Acceptance Criteria"):
        section_content = extract_section(content, checklist_section)
        if section_content and not re.search(r"^\s*-\s+\[( |x|~)\]\s+\S", section_content, re.MULTILINE):
            errors.append(f"{checklist_section} must contain checklist items using [ ], [x], or [~]")
        if status == "COMPLETED" and re.search(r"^\s*-\s+\[( |~)\]\s+\S", section_content, re.MULTILINE):
            errors.append(f"{checklist_section} has pending/in-progress items but task status is COMPLETED")

    execution_log = extract_section(content, "Execution Log")
    if execution_log and not re.search(r"^\s*-\s+`\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]`:\s+\S", execution_log, re.MULTILINE):
        errors.append("Execution Log entries must follow: - `[YYYY-MM-DD HH:MM]`: ...")

    if errors:
        return errors, None
    return errors, TaskInfo(file_path, task_id, status, priority, stage_ref)


def parse_stage_rows(content: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in content.splitlines():
        if not line.startswith("| TASK-"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 5:
            rows.append({"error": f"Invalid stage task row: {line}"})
            continue
        task_id, task, status, priority, depends_on = parts
        link_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", task)
        rows.append(
            {
                "task_id": task_id,
                "task": task,
                "task_title": link_match.group(1) if link_match else task,
                "task_file": link_match.group(2) if link_match else "",
                "status": status,
                "priority": priority,
                "depends_on": depends_on,
            }
        )
    return rows


def validate_stage_index(stage_file: Path, task_infos: dict[str, TaskInfo]) -> list[str]:
    content = read_text(stage_file)
    errors: list[str] = []
    if not re.search(r"^# Stage \d{2} Tasks\s+-\s+.+$", content, re.MULTILINE):
        errors.append("Missing or invalid stage title. Expected: # Stage XX Tasks - Title")
    if "| ID | Task | Status | Priority | Depends On |" not in content:
        errors.append("Missing stage task table header")

    seen: set[str] = set()
    for row in parse_stage_rows(content):
        if "error" in row:
            errors.append(row["error"])
            continue
        task_id = row["task_id"]
        if task_id in seen:
            errors.append(f"Duplicate task row: {task_id}")
        seen.add(task_id)

        if row["status"] not in ALLOWED_STATUSES:
            errors.append(f"{task_id}: invalid status in stage index: {row['status']}")
        if row["priority"] not in ALLOWED_PRIORITIES:
            errors.append(f"{task_id}: invalid priority in stage index: {row['priority']}")
        if not row["task_file"]:
            errors.append(f"{task_id}: task row must link to its task_XXX_slug.md file")
        else:
            linked_path = (stage_file.parent / row["task_file"]).resolve()
            if not linked_path.exists():
                errors.append(f"{task_id}: linked task file does not exist: {row['task_file']}")

        task_info = task_infos.get(task_id)
        if not task_info:
            errors.append(f"{task_id}: detailed task file not found")
            continue
        if task_info.status != row["status"]:
            errors.append(f"{task_id}: status mismatch between stage index and task file")
        if task_info.priority != row["priority"]:
            errors.append(f"{task_id}: priority mismatch between stage index and task file")

        if row["depends_on"] != "-":
            for dep in [dep.strip() for dep in row["depends_on"].split(",")]:
                if not re.fullmatch(r"TASK-\d{3}", dep):
                    errors.append(f"{task_id}: invalid dependency format: {dep}")

    if not seen:
        errors.append("Stage index must include at least one TASK row")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GenAI task and stage documentation.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    tasks_dir = repo_root / "docs" / "tasks"
    if not tasks_dir.exists():
        print("ERROR: docs/tasks directory not found.")
        return 1

    all_passed = True
    task_infos: dict[str, TaskInfo] = {}
    for task_file in sorted(tasks_dir.glob("task_*.md")):
        if task_file.name == "task_template.md":
            continue
        errors, task_info = validate_task_file(task_file, repo_root)
        if errors:
            print(f"ERROR {task_file.relative_to(repo_root)}")
            for error in errors:
                print(f"  - {error}")
            all_passed = False
        else:
            print(f"OK {task_file.relative_to(repo_root)}")
            if task_info:
                task_infos[task_info.task_id] = task_info

    for stage_file in sorted(tasks_dir.glob("stage_*_tasks.md")):
        errors = validate_stage_index(stage_file, task_infos)
        if errors:
            print(f"ERROR {stage_file.relative_to(repo_root)}")
            for error in errors:
                print(f"  - {error}")
            all_passed = False
        else:
            print(f"OK {stage_file.relative_to(repo_root)}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
