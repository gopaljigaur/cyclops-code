import os
from pathlib import Path

from cyclops import BaseTool


class WriteTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="Write",
            description="Create or overwrite a file with the given content.",
        )

    async def execute(self, path: str, content: str) -> str:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        tmp = p.with_suffix(p.suffix + ".tmp")
        try:
            tmp.write_text(content)
            os.replace(tmp, p)
        except OSError as e:
            tmp.unlink(missing_ok=True)
            return f"Error writing {path}: {e}"

        line_count = content.count("\n") + (
            1 if content and not content.endswith("\n") else 0
        )
        return f"Wrote {line_count} lines to {path}"
