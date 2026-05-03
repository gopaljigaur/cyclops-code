import json
from pathlib import Path
from typing import Any


_CYCLOPS_HOME = Path.home() / ".cyclops"
_CONFIG_PATH = _CYCLOPS_HOME / "config.json"
_SESSIONS_DIR = _CYCLOPS_HOME / "sessions"
_HISTORY_FILE = _CYCLOPS_HOME / "history"


class MCPServerConfig:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MCPServerConfig":
        return cls(
            name=d["name"],
            command=d["command"],
            args=d.get("args", []),
            env=d.get("env", {}),
        )

    @property
    def full_command(self) -> list[str]:
        return [self.command] + self.args


class Config:
    model: str
    stream: bool
    max_iterations: int
    temperature: float
    mcp_servers: list[MCPServerConfig]

    def __init__(
        self,
        model: str = "anthropic/claude-haiku-4-5-20251001",
        stream: bool = True,
        max_iterations: int = 15,
        temperature: float = 0.2,
        mcp_servers: list[MCPServerConfig] | None = None,
    ) -> None:
        self.model = model
        self.stream = stream
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.mcp_servers = mcp_servers or []

    @classmethod
    def load(cls) -> "Config":
        if not _CONFIG_PATH.exists():
            return cls()
        try:
            data: dict[str, Any] = json.loads(_CONFIG_PATH.read_text())
            servers = [
                MCPServerConfig.from_dict(s)
                for s in data.get("mcp_servers", [])
                if isinstance(s, dict) and "name" in s and "command" in s
            ]
            return cls(
                model=data.get("model", "anthropic/claude-haiku-4-5-20251001"),
                stream=data.get("stream", True),
                max_iterations=data.get("max_iterations", 15),
                temperature=data.get("temperature", 0.2),
                mcp_servers=servers,
            )
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self) -> None:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(
            json.dumps(
                {
                    "model": self.model,
                    "stream": self.stream,
                    "max_iterations": self.max_iterations,
                    "temperature": self.temperature,
                    "mcp_servers": [s.to_dict() for s in self.mcp_servers],
                },
                indent=2,
            )
        )

    def add_mcp_server(self, server: MCPServerConfig) -> None:
        self.mcp_servers = [s for s in self.mcp_servers if s.name != server.name]
        self.mcp_servers.append(server)
        self.save()

    def remove_mcp_server(self, name: str) -> bool:
        before = len(self.mcp_servers)
        self.mcp_servers = [s for s in self.mcp_servers if s.name != name]
        if len(self.mcp_servers) < before:
            self.save()
            return True
        return False

    def get_sessions_dir(self) -> Path:
        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        return _SESSIONS_DIR

    def get_history_file(self) -> Path:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        return _HISTORY_FILE
