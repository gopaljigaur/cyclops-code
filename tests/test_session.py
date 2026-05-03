from pathlib import Path

import pytest

from cyclops_code.config import Config
from cyclops_code.session import Session


class TestSession:
    def _session_with_dir(self, tmp_path: Path):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        config = Config()
        session = Session.__new__(Session)
        session._sessions_dir = sessions_dir
        return session, sessions_dir

    def test_save_creates_json_file(self, tmp_path: Path) -> None:
        session, sessions_dir = self._session_with_dir(tmp_path)
        history = [{"role": "user", "content": "hello"}]

        path = session.save("my-session", history, "claude-3-5-haiku-20241022")

        saved = sessions_dir / "my-session.json"
        assert saved.exists()
        assert path == str(saved)

    def test_save_stores_history_and_model(self, tmp_path: Path) -> None:
        import json

        session, sessions_dir = self._session_with_dir(tmp_path)
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

        session.save("test", history, "gpt-4")

        data = json.loads((sessions_dir / "test.json").read_text())
        assert data["history"] == history
        assert data["model"] == "gpt-4"
        assert data["name"] == "test"
        assert "timestamp" in data

    def test_load_returns_saved_data(self, tmp_path: Path) -> None:
        session, _ = self._session_with_dir(tmp_path)
        history = [{"role": "user", "content": "test message"}]

        session.save("load-test", history, "model-x")
        loaded = session.load("load-test")

        assert loaded["history"] == history
        assert loaded["model"] == "model-x"

    def test_load_raises_on_missing_session(self, tmp_path: Path) -> None:
        session, _ = self._session_with_dir(tmp_path)

        with pytest.raises(FileNotFoundError, match="Session not found"):
            session.load("does-not-exist")

    def test_load_raises_on_corrupt_json(self, tmp_path: Path) -> None:
        session, sessions_dir = self._session_with_dir(tmp_path)
        (sessions_dir / "bad.json").write_text("{ not valid json }")

        with pytest.raises(ValueError, match="Corrupt session file"):
            session.load("bad")

    def test_list_sessions_returns_names(self, tmp_path: Path) -> None:
        session, _ = self._session_with_dir(tmp_path)

        session.save("alpha", [], "m")
        session.save("beta", [], "m")
        session.save("gamma", [], "m")

        names = session.list_sessions()
        assert set(names) == {"alpha", "beta", "gamma"}

    def test_list_sessions_sorted_by_mtime(self, tmp_path: Path) -> None:
        import time

        session, sessions_dir = self._session_with_dir(tmp_path)

        session.save("first", [], "m")
        time.sleep(0.02)
        session.save("second", [], "m")
        time.sleep(0.02)
        session.save("third", [], "m")

        names = session.list_sessions()
        assert names[0] == "third"
        assert names[-1] == "first"

    def test_list_sessions_empty_when_no_sessions(self, tmp_path: Path) -> None:
        session, sessions_dir = self._session_with_dir(tmp_path)
        sessions_dir.rmdir()

        names = session.list_sessions()
        assert names == []
