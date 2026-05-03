import json
from datetime import datetime, timezone
from typing import Any

from cyclops_code.config import Config


class Session:
    def __init__(self, config: Config) -> None:
        self._sessions_dir = config.get_sessions_dir()

    def save(self, name: str, history: list[dict[str, Any]], model: str) -> str:
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = self._sessions_dir / f"{name}.json"
        data = {
            "name": name,
            "model": model,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "history": history,
        }
        session_file.write_text(json.dumps(data, indent=2))
        return str(session_file)

    def load(self, name: str) -> dict[str, Any]:
        session_file = self._sessions_dir / f"{name}.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {name}")
        try:
            return json.loads(session_file.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupt session file for '{name}': {e}") from e

    def list_sessions(self) -> list[str]:
        if not self._sessions_dir.exists():
            return []
        files = sorted(
            self._sessions_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [p.stem for p in files]
