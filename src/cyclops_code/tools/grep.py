import fnmatch
import re
from pathlib import Path

from cyclops import BaseTool

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
_MAX_MATCHES = 100
_BINARY_CHUNK = 8192


def _is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:_BINARY_CHUNK]
        return b"\x00" in chunk
    except OSError:
        return True


class GrepTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="Grep",
            description="Search for a regex pattern in files.",
        )

    async def execute(self, pattern: str, path: str = ".", include: str = "") -> str:
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            return f"Error: invalid regex pattern: {e}"

        base = Path(path).resolve()
        if not base.exists():
            return f"Error: path not found: {path}"

        matches: list[str] = []
        total = 0

        if base.is_file():
            files = [base]
        else:
            files = (
                p
                for p in base.rglob("*")
                if p.is_file()
                and not any(part in _SKIP_DIRS for part in p.relative_to(base).parts)
            )

        for filepath in files:
            if include and not fnmatch.fnmatch(filepath.name, include):
                continue
            if _is_binary(filepath):
                continue

            try:
                text = filepath.read_text(errors="replace")
            except OSError:
                continue

            for lineno, line in enumerate(text.splitlines(), start=1):
                if compiled.search(line):
                    total += 1
                    if len(matches) < _MAX_MATCHES:
                        matches.append(f"{filepath}:{lineno}: {line}")

        if not matches:
            return f"No matches for '{pattern}'"

        output = "\n".join(matches)
        if total > _MAX_MATCHES:
            output += f"\n\n[Showing {_MAX_MATCHES} of {total} matches]"
        else:
            output += f"\n\n[{total} match(es)]"

        return output
