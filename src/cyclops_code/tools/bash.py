import asyncio
import os

from cyclops import BaseTool

_MAX_OUTPUT = 10000


class BashTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="Bash",
            description="Run a shell command. Use for tests, builds, git, and CLI tools.",
        )

    async def execute(self, command: str, timeout: int = 30) -> str:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd(),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            code = proc.returncode
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"[exit 1]\nCommand timed out after {timeout}s"

        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")
        combined = (stdout + stderr).strip()

        if len(combined) > _MAX_OUTPUT:
            combined = (
                combined[:_MAX_OUTPUT]
                + f"\n\n[Truncated: output exceeded {_MAX_OUTPUT} chars]"
            )

        return f"[exit {code}]\n{combined}"
