import os
import re
from datetime import datetime, timezone
from pathlib import Path

from cyclops import BaseTool

_STATUS_ICONS = {
    "todo": "[ ]",
    "in_progress": "[-]",
    "done": "[x]",
}


class PlanTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="Plan",
            description=(
                "Write an implementation plan to .cyclops/plans/ before starting work. "
                "Use for any multi-step task. Returns the plan path — pass it to "
                "PlanUpdate to mark steps as in_progress or done as you work."
            ),
        )

    async def execute(self, title: str, steps: list[str]) -> str:
        cwd = Path(os.getcwd())
        plans_dir = cwd / ".cyclops" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:40].strip("_")
        plan_file = plans_dir / f"{ts}_{slug}.md"

        lines = [f"# {title}\n"]
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. [ ] {step}")
        plan_file.write_text("\n".join(lines) + "\n")

        return f"Plan saved: {plan_file}\nSteps: {len(steps)}"


class PlanUpdateTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="PlanUpdate",
            description=(
                "Update the status of a step in an existing plan file. "
                "status must be one of: todo, in_progress, done."
            ),
        )

    async def execute(self, plan_path: str, step: int, status: str) -> str:
        if status not in _STATUS_ICONS:
            return f"Invalid status '{status}'. Use: todo, in_progress, done"

        path = Path(plan_path)
        if not path.exists():
            return f"Plan file not found: {plan_path}"

        icon = _STATUS_ICONS[status]
        lines = path.read_text().splitlines()
        pattern = re.compile(rf"^({step}\.) \[[ x\-]\] (.+)$")
        updated = False
        for i, line in enumerate(lines):
            m = pattern.match(line)
            if m:
                lines[i] = f"{m.group(1)} {icon} {m.group(2)}"
                updated = True
                break

        if not updated:
            return f"Step {step} not found in plan"

        path.write_text("\n".join(lines) + "\n")
        return f"Step {step} marked {status}"
