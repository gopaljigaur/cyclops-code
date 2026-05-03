import difflib
import os
from pathlib import Path

from cyclops import BaseTool


class EditTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="Edit",
            description="Replace exact text in a file. old_string must match exactly once.",
        )

    async def execute(self, path: str, old_string: str, new_string: str) -> str:
        p = Path(path)
        if not p.exists():
            return f"Error: file not found: {path}"

        try:
            original = p.read_text()
        except OSError as e:
            return f"Error reading {path}: {e}"

        count = original.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {path}"
        if count > 1:
            return (
                f"Error: old_string matches {count} times in {path} — must be unique. "
                "Add more context around the text to make it unique."
            )

        updated = original.replace(old_string, new_string, 1)
        tmp = p.with_suffix(p.suffix + ".tmp")
        try:
            tmp.write_text(updated)
            os.replace(tmp, p)
        except OSError as e:
            tmp.unlink(missing_ok=True)
            return f"Error writing {path}: {e}"

        diff = list(difflib.unified_diff(
            old_string.splitlines(keepends=True),
            new_string.splitlines(keepends=True),
            lineterm="",
        ))
        removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
        added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        diff_text = "".join(diff)
        return f"DIFF:{path}\n-{removed} +{added}\n{diff_text}"
