from pathlib import Path

from cyclops import BaseTool

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
_MAX_RESULTS = 200


class GlobTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="Glob",
            description="Find files matching a glob pattern.",
        )

    async def execute(self, pattern: str, path: str = ".") -> str:
        base = Path(path).resolve()
        if not base.exists():
            return f"Error: path not found: {path}"

        recursive = "**" in pattern

        if recursive:
            raw_matches = base.rglob(pattern)
        else:
            raw_matches = base.glob(pattern)

        results: list[str] = []
        for p in raw_matches:
            parts = p.relative_to(base).parts
            if any(part in _SKIP_DIRS for part in parts):
                continue
            results.append(str(p))
            if len(results) >= _MAX_RESULTS:
                break

        results.sort()

        if not results:
            return f"No files matching '{pattern}' in {path}"

        output = "\n".join(results)
        if len(results) == _MAX_RESULTS:
            output += f"\n\n[Showing first {_MAX_RESULTS} results]"
        else:
            output += f"\n\n[{len(results)} file(s) found]"

        return output
