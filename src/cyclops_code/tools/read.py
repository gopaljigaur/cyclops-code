from pathlib import Path

from cyclops import BaseTool

_MAX_LINES = 2000


class ReadTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="Read",
            description="Read file contents. Returns contents with line numbers.",
        )

    async def execute(self, path: str, start_line: int = 1, end_line: int = 0) -> str:
        p = Path(path)
        if not p.exists():
            return f"Error: file not found: {path}"
        if not p.is_file():
            return f"Error: not a file: {path}"

        try:
            lines = p.read_text(errors="replace").splitlines()
        except OSError as e:
            return f"Error reading {path}: {e}"

        total = len(lines)
        start = max(1, start_line)
        end = total if end_line == 0 else min(end_line, total)

        selected = lines[start - 1 : end]
        truncated = False
        if len(selected) > _MAX_LINES:
            selected = selected[:_MAX_LINES]
            truncated = True

        numbered = "\n".join(
            f"{start + i:4d}: {line}" for i, line in enumerate(selected)
        )

        if truncated:
            numbered += f"\n\n[Truncated: showing lines {start}-{start + _MAX_LINES - 1} of {total}]"

        return numbered
