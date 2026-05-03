"""prompt_toolkit + rich REPL for the cyclops coding agent."""

from __future__ import annotations

import getpass
import json
import random
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import shutil

from prompt_toolkit import Application, PromptSession
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit, VerticalAlign, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

from cyclops import AgentHooks
from cyclops_code.config import Config
from cyclops_code.session import Session

_SLASH_COMMANDS: dict[str, str] = {
    "/help":     "List all commands",
    "/clear":    "Wipe conversation history and start fresh",
    "/compact":  "Summarize history via LLM, replace with summary",
    "/model":    "Switch model, type to filter, Enter to confirm",
    "/mode":     "Toggle auto / review tool approval  (or Shift+Tab)",
    "/mcp":      "Manage MCP servers  list|add|remove|connect|disconnect",
    "/save":     "Save session to disk  [name]",
    "/load":     "Load a saved session  <name>",
    "/sessions": "List saved sessions",
    "/cost":     "Show total token usage and cost",
    "/exit":     "Quit",
}

_PICKER_PROVIDERS = {"anthropic", "openai", "gemini", "groq", "deepseek", "mistral", "ollama"}

_WORKING_WORDS = [
    "Thinking", "Working", "Reasoning", "Computing",
    "Pondering", "Processing", "Analyzing", "Deliberating",
]


def _get_picker_models() -> list[tuple[str, str, str]]:
    import litellm
    results: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    for model_name, info in litellm.model_cost.items():
        if not isinstance(info, dict):
            continue
        if info.get("mode") != "chat":
            continue
        provider = info.get("litellm_provider", "")
        if provider not in _PICKER_PROVIDERS:
            continue
        if model_name in seen:
            continue
        seen.add(model_name)
        if provider == "openai":
            litellm_id = model_name
        elif model_name.startswith(f"{provider}/"):
            litellm_id = model_name  # already prefixed (e.g. ollama/llama2)
        else:
            litellm_id = f"{provider}/{model_name}"
        display_name = model_name.removeprefix(f"{provider}/")
        results.append((provider, display_name, litellm_id))

    # Ollama: query local server — litellm has no SDK for this (issue #5894)
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1) as r:
            for m in _json.loads(r.read()).get("models", []):
                name = m["name"]
                litellm_id = f"ollama/{name}"
                if litellm_id not in seen:
                    seen.add(litellm_id)
                    results.append(("ollama", name, litellm_id))
    except Exception:
        pass

    results.sort(key=lambda x: (x[0], x[1]))
    return results


def _short_path(cwd: str) -> str:
    home = str(Path.home())
    if cwd.startswith(home):
        return "~" + cwd[len(home):]
    return cwd


def _model_short(model: str) -> str:
    return model.split("/")[-1]


_GIT_BRANCH_CACHE: dict[str, tuple[str, float]] = {}


def _git_branch(cwd: str) -> str:
    now = time.monotonic()
    cached = _GIT_BRANCH_CACHE.get(cwd)
    if cached and now - cached[1] < 5.0:
        return cached[0]
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=2,
        )
        result = r.stdout.strip()
        result = result if result and result != "HEAD" else ""
    except Exception:
        result = ""
    _GIT_BRANCH_CACHE[cwd] = (result, now)
    return result


def _make_agent(config: Config, cwd: str, hooks: AgentHooks, extra_tools: list | None = None):
    from cyclops import Agent, AgentConfig
    from cyclops_code.prompt import build_system_prompt
    from cyclops_code.tools import ALL_TOOLS

    tools = list(ALL_TOOLS) + (extra_tools or [])
    return Agent(
        AgentConfig(
            model=config.model,
            temperature=config.temperature,
            max_iterations=config.max_iterations,
            system_prompt=build_system_prompt(cwd),
            hooks=hooks,
        ),
        tools=tools,
    )


# ── Completers ────────────────────────────────────────────────────────────────

class SlashCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        query = text[1:].lower()
        for cmd, desc in _SLASH_COMMANDS.items():
            if not query or query in cmd[1:].lower() or query in desc.lower():
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display=cmd,
                    display_meta=desc,
                )


class ModelCompleter(Completer):
    def get_completions(self, document, complete_event):
        query = document.text_before_cursor.lower().strip()
        for provider, name, model_id in _get_picker_models():
            if not query or query in model_id.lower() or query in name.lower() or query in provider.lower():
                yield Completion(
                    model_id,
                    start_position=-len(document.text_before_cursor),
                    display=f"{provider:<12} {name}",
                    display_meta=provider,
                )


# ── Hooks ─────────────────────────────────────────────────────────────────────

class CyclopsHooks(AgentHooks):
    def __init__(self, repl: "CyclopsRepl") -> None:
        self._repl = repl

    def on_tool_start(self, tool_name: str, args: dict) -> str:
        primary = next(iter(args.values()), "") if args else ""
        if isinstance(primary, str) and len(primary) > 60:
            primary = primary[:57] + "..."
        icon = "▼" if self._repl._tools_expanded else "▶"
        t = Text()
        t.append(f"  {icon} ", style="#888888")
        t.append(tool_name, style="bold #5fafff")
        if primary:
            t.append(f"  {primary}", style="dim")
        self._repl.console.print(t)
        if self._repl.mode == "auto" or self._repl._approve_all:
            return "allow"
        return self._repl._prompt_approval(tool_name, args)

    def on_tool_end(self, tool_name: str, args: dict, result: str) -> None:
        if tool_name == "Plan":
            _render_plan(self._repl.console, args)
        elif tool_name == "PlanUpdate":
            _render_plan_update(self._repl.console, args)
        elif result.startswith("DIFF:"):
            _render_diff(self._repl.console, result)
        elif self._repl._tools_expanded and result and not result.startswith("Error:"):
            preview = "\n".join(result.splitlines()[:20])
            self._repl.console.print(Text(f"    {preview}", style="dim"))

    def on_llm_end(self, response) -> None:
        try:
            import litellm
            cost = litellm.completion_cost(completion_response=response) or 0.0
            tokens = getattr(response.usage, "total_tokens", 0) or 0
            self._repl.total_cost += cost
            self._repl.total_tokens += tokens
        except Exception:
            pass


# ── Rich renderers ────────────────────────────────────────────────────────────

def _render_diff(console: Console, result: str) -> None:
    lines = result.splitlines()
    path = lines[0][5:] if lines else ""
    summary = lines[1] if len(lines) > 1 else ""
    diff_lines = lines[2:] if len(lines) > 2 else []
    t = Text()
    t.append(f"\n{path}", style="bold #888888")
    t.append(f"  {summary}\n", style="dim")
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            t.append(line + "\n", style="#3fb950")
        elif line.startswith("-") and not line.startswith("---"):
            t.append(line + "\n", style="#f85149")
        elif line.startswith("@@"):
            t.append(line + "\n", style="#58a6ff")
        else:
            t.append(line + "\n", style="dim")
    console.print(t)


def _render_plan(console: Console, args: dict) -> None:
    title = args.get("title", "Plan")
    steps: list[str] = args.get("steps", [])
    t = Text()
    t.append(f"\n{title}\n", style="bold #5fafff")
    for i, step in enumerate(steps, 1):
        t.append(f"  {i}. ", style="dim")
        t.append("[ ] ", style="#555555")
        t.append(step + "\n")
    console.print(t)


def _render_plan_update(console: Console, args: dict) -> None:
    step = args.get("step", "?")
    status = args.get("status", "")
    icons = {"todo": "[ ]", "in_progress": "[-]", "done": "[x]"}
    colors = {"todo": "#555555", "in_progress": "#d7af00", "done": "#5faf5f"}
    icon = icons.get(status, "[ ]")
    color = colors.get(status, "#555555")
    t = Text()
    t.append(f"  step {step} ", style="dim")
    t.append(icon, style=color)
    t.append(f" {status}", style=color)
    console.print(t)


# ── Main REPL ─────────────────────────────────────────────────────────────────

class CyclopsRepl:
    def __init__(self, config: Config, cwd: str) -> None:
        self.config = config
        self.cwd = cwd
        self.console = Console()
        self.session_manager = Session(config)
        self.total_cost = 0.0
        self.total_tokens = 0
        self.mode = "review"
        self._tools_expanded = False
        self._approve_all = False
        self._cancelled = False
        self._current_live: Live | None = None
        self._user = getpass.getuser()
        self._host = socket.gethostname().split(".")[0]
        self._mcp_bridge = None
        self._mcp_server_tools: dict[str, list] = {}
        self.agent = None

    def _status_line_str(self) -> str:
        branch = _git_branch(self.cwd)
        parts = [f"{self._user}@{self._host}", _short_path(self.cwd)]
        if branch:
            parts.append(f"({branch})")
        parts.append(_model_short(self.config.model))
        if self.total_tokens > 0:
            parts.append(f"{self.total_tokens:,}tok")
        if self.total_cost > 0:
            parts.append(f"${self.total_cost:.4f}")
        if self.mode == "auto":
            parts.append("[auto]")
        if self._tools_expanded:
            parts.append("[tools▼]")
        return "  ·  ".join(parts)

    @property
    def _mcp_tools(self) -> list:
        return [t for ts in self._mcp_server_tools.values() for t in ts]

    def _get_or_create_bridge(self):
        if self._mcp_bridge is None:
            from cyclops.mcp.bridge import MCPBridge
            self._mcp_bridge = MCPBridge()
        return self._mcp_bridge

    def _make_prompt_app(self) -> tuple[Application, Buffer]:
        buf = Buffer(
            history=FileHistory(str(self.config.get_history_file())),
            completer=SlashCompleter(),
            complete_while_typing=True,
            multiline=True,
            name="main",
        )

        kb = KeyBindings()

        @kb.add("s-tab")
        def _cycle_mode(event):
            self.mode = "auto" if self.mode == "review" else "review"
            event.app.invalidate()

        @kb.add("enter")
        def _submit(event):
            event.app.exit(result=event.app.current_buffer.text)

        @kb.add("escape", "enter")
        def _newline(event):
            event.app.current_buffer.insert_text("\n")

        @kb.add("c-o")
        def _toggle_tools(event):
            self._tools_expanded = not self._tools_expanded
            event.app.invalidate()

        @kb.add("c-c")
        def _interrupt(event):
            event.app.exit(exception=KeyboardInterrupt())

        @kb.add("c-d")
        def _eof(event):
            if not event.app.current_buffer.text:
                event.app.exit(exception=EOFError())

        def _sep():
            return "─" * shutil.get_terminal_size().columns

        layout = Layout(
            FloatContainer(
                content=HSplit([
                    Window(height=1, content=FormattedTextControl(_sep), style="class:sep"),
                    Window(
                        content=BufferControl(
                            buffer=buf,
                            input_processors=[BeforeInput("❯ ")],
                        ),
                        wrap_lines=True,
                        dont_extend_height=True,
                    ),
                    Window(height=1, content=FormattedTextControl(_sep), style="class:sep"),
                    Window(height=1, content=FormattedTextControl(self._status_line_str), style="class:status"),
                ], align=VerticalAlign.TOP),
                floats=[
                    Float(
                        xcursor=True,
                        top=4,
                        content=CompletionsMenu(max_height=8, scroll_offset=1),
                    )
                ],
            )
        )

        _style = Style.from_dict({
            "sep":                                "#444444",
            "status":                             "#555555",
            "completion-menu":                    "bg:#111111 #888888",
            "completion-menu.completion":         "bg:#111111 #888888",
            "completion-menu.completion.current": "bg:#1a3060 bold #ffffff",
            "completion-menu.meta":               "bg:#111111 #555555",
            "completion-menu.meta.current":       "bg:#1a3060 #888888",
            "scrollbar.background":               "bg:#111111",
            "scrollbar.button":                   "bg:#333333",
        })

        app = Application(layout=layout, key_bindings=kb, style=_style, full_screen=False)
        return app, buf

    def run(self) -> None:
        hooks = CyclopsHooks(self)
        if self.config.mcp_servers:
            self._get_or_create_bridge()
            self._auto_connect_mcp_servers()
        self.agent = _make_agent(self.config, self.cwd, hooks, self._mcp_tools)
        self._print_header(self.agent)
        prompt_app, prompt_buf = self._make_prompt_app()
        _ctrl_c = 0

        try:
            while True:
                try:
                    prompt_buf.reset()
                    text = prompt_app.run()
                    n = (text or "").count("\n") + 1
                    sys.stdout.write(f"\r\033[{n+3}A\033[2K\r\033[{n+1}B\033[J")
                    sys.stdout.flush()
                    if text is None:
                        text = ""
                    text = text.strip()
                    _ctrl_c = 0
                except KeyboardInterrupt:
                    _ctrl_c += 1
                    if _ctrl_c >= 2:
                        break
                    self.console.print("[dim](ctrl+c again to exit)[/dim]")
                    continue
                except EOFError:
                    break

                if not text:
                    continue

                if text in ("exit", "quit"):
                    break

                if text.startswith("/"):
                    self._handle_slash(text, self.agent, prompt_app)
                    continue

                if text.startswith("!"):
                    self._run_shell(text[1:].strip())
                    continue

                self._approve_all = False
                self._run_generation(text, self.agent)
        finally:
            if self._mcp_bridge is not None:
                self._mcp_bridge.stop()

        self.console.print("\n[dim]bye.[/dim]")

    def _auto_connect_mcp_servers(self) -> None:
        for server_cfg in self.config.mcp_servers:
            self._connect_mcp_server(server_cfg, quiet=False)

    def _connect_mcp_server(self, server_cfg, *, quiet: bool = False) -> int:
        from cyclops.mcp.tools import tools_from_server
        bridge = self._get_or_create_bridge()
        try:
            _, tools = tools_from_server(bridge, server_cfg.name, server_cfg.full_command, env=server_cfg.env or None)
            self._mcp_server_tools[server_cfg.name] = tools
            if not quiet:
                label = f"{len(tools)} tool{'s' if len(tools) != 1 else ''}"
                self.console.print(Text.assemble(("  mcp  ", "dim"), (server_cfg.name, "green"), (f"  {label}", "dim")))
            return len(tools)
        except Exception as exc:
            self.console.print(f"[red]mcp connect error ({server_cfg.name}):[/red] {exc}")
            return 0

    def _disconnect_mcp_server(self, name: str) -> bool:
        if name not in self._mcp_server_tools or self._mcp_bridge is None:
            return False
        self._mcp_bridge.disconnect(name)
        del self._mcp_server_tools[name]
        return True

    def _rebuild_agent(self) -> None:
        hooks = CyclopsHooks(self)
        history = list(self.agent.messages) if self.agent else []
        self.agent = _make_agent(self.config, self.cwd, hooks, self._mcp_tools)
        for msg in history:
            self.agent._history.append(msg)

    def _print_header(self, agent) -> None:
        from cyclops_code import __version__
        branch = _git_branch(self.cwd)
        self.console.print()
        t = Text()
        t.append("( ◉ )", style="bold #58a6ff")
        t.append("  cyclops", style="bold white")
        t.append(f"  v{__version__}\n", style="dim")
        t.append(f"       {_model_short(self.config.model)}\n", style="dim")
        t.append(f"       {_short_path(self.cwd)}", style="dim")
        if branch:
            t.append(f"  ({branch})", style="dim")
        self.console.print(t)
        self.console.print()

    def _run_generation(self, text: str, agent) -> None:
        self._cancelled = False
        start = time.monotonic()
        chunks: list[str] = []
        word = random.choice(_WORKING_WORDS)
        sp = Spinner("dots", text=Text(f" {word}...", style="bold #5fafff"))
        status_fn = self._status_line_str

        class _Display:
            def __rich_console__(self_, console, options):
                yield sp
                yield Text("─" * options.max_width, style="#444444", no_wrap=True)
                yield Text(status_fn(), style="#555555")

        try:
            with Live(_Display(), console=self.console, refresh_per_second=12, transient=True) as live:
                self._current_live = live
                for chunk in agent.stream(text):
                    if self._cancelled:
                        break
                    chunks.append(chunk)
        except KeyboardInterrupt:
            self._cancelled = True
        except Exception as exc:
            self._current_live = None
            raw = str(exc).split("\n")[0]
            msg = raw.split(" - {")[0][:120]
            self.console.print(f"[red]error:[/red] {msg}")
            return
        finally:
            self._current_live = None

        full = "".join(chunks)
        elapsed = time.monotonic() - start
        if full.strip():
            self.console.print(Markdown(full))
        self.console.print(Text(f"· {elapsed:.1f}s", style="dim"))
        self.console.print()

    def _run_shell(self, cmd: str) -> None:
        if not cmd:
            return
        self.console.print(Text(f"$ {cmd}", style="dim #888888"))
        try:
            proc = subprocess.Popen(
                cmd, shell=True, cwd=self.cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            assert proc.stdout
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
            proc.wait()
            if proc.returncode != 0:
                self.console.print(Text(f"exit {proc.returncode}", style="dim #f85149"))
        except Exception as exc:
            self.console.print(f"[red]shell error:[/red] {exc}")

    def _prompt_approval(self, tool_name: str, args: dict) -> str:
        live = self._current_live
        if live is not None:
            live.stop()

        options = ["Yes", "No", "Yes to all"]
        sel = [0]

        def _text():
            result = []
            for i, opt in enumerate(options):
                if i == sel[0]:
                    result.append(("bold #ffffff", f"  ❯ {opt}"))
                else:
                    result.append(("#555555", f"    {opt}"))
                result.append(("", "\n"))
            return result

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            sel[0] = (sel[0] - 1) % len(options)
            event.app.invalidate()

        @kb.add("down")
        def _down(event):
            sel[0] = (sel[0] + 1) % len(options)
            event.app.invalidate()

        @kb.add("enter")
        def _enter(event):
            event.app.exit(result=sel[0])

        @kb.add("c-c")
        @kb.add("escape")
        def _cancel(event):
            event.app.exit(result=-1)

        picker = Application(
            layout=Layout(Window(content=FormattedTextControl(_text), height=len(options))),
            key_bindings=kb,
            full_screen=False,
        )
        choice = picker.run()
        if choice is None:
            choice = -1

        if live is not None:
            live.start()

        if choice == 0:
            return "allow"
        if choice == 2:
            self._approve_all = True
            return "allow"
        return "deny"

    # ── Slash commands ────────────────────────────────────────────────────────

    def _handle_slash(self, text: str, agent, app: Application) -> None:
        parts = text.strip().split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command == "/help":
            self.console.print()
            for cmd, desc in _SLASH_COMMANDS.items():
                t = Text()
                t.append(f"{cmd:<18}", style="yellow")
                t.append(desc, style="dim")
                self.console.print(t)
            self.console.print()

        elif command == "/clear":
            agent.reset()
            self.console.clear()
            self._print_header(self.agent)

        elif command == "/compact":
            msgs = list(agent.messages)
            if len(msgs) < 4:
                self.console.print("[dim]nothing to compact[/dim]")
            else:
                history_text = "\n".join(
                    f"{m['role'].upper()}: {str(m.get('content', ''))[:600]}"
                    for m in msgs
                    if isinstance(m.get("content"), str)
                )
                prompt = (
                    f"Conversation so far:\n\n{history_text}\n\n"
                    "Summarize this conversation concisely, preserving all important "
                    "context, decisions, file paths, and code changes. "
                    "This summary replaces the full history."
                )
                try:
                    import litellm
                    with self.console.status("Compacting...", spinner="dots", spinner_style="bold #5fafff"):
                        resp = litellm.completion(
                            model=self.config.model,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.1,
                        )
                    summary = resp.choices[0].message.content
                    agent.reset()
                    agent._history.append({"role": "assistant", "content": f"[Conversation summary]\n{summary}"})
                    self.console.print(Text.assemble(
                        ("compacted → ", "dim"), (f"{len(msgs)} msgs → summary", "green"),
                    ))
                except Exception as e:
                    self.console.print(f"[red]compact error:[/red] {e}")

        elif command == "/mode":
            self.mode = "auto" if self.mode == "review" else "review"
            self.console.print(Text.assemble(("mode → ", "dim"), (self.mode, "green")))

        elif command == "/mcp":
            self._handle_mcp(arg.strip())

        elif command == "/model":
            if arg.strip():
                self._set_model(arg.strip(), agent)
            else:
                self._model_picker(agent)

        elif command == "/save":
            name = arg.strip() or datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = self.session_manager.save(name, agent.messages, self.config.model)
            self.console.print(Text.assemble(
                ("saved → ", "dim"), (name, "green"), (f"  ({path})", "dim"),
            ))

        elif command == "/load":
            if not arg:
                self.console.print("[red]usage:[/red] /load <name>")
            else:
                try:
                    data = self.session_manager.load(arg.strip())
                    agent.reset()
                    for msg in data.get("history", []):
                        agent._history.append(msg)
                    model = data.get("model", self.config.model)
                    self.console.print(Text.assemble(
                        ("loaded → ", "dim"), (arg.strip(), "green"),
                        (f"  ({len(agent.messages)} msgs, {model})", "dim"),
                    ))
                except (FileNotFoundError, ValueError) as e:
                    self.console.print(f"[red]{e}[/red]")

        elif command == "/sessions":
            names = self.session_manager.list_sessions()
            if not names:
                self.console.print("[dim]no saved sessions[/dim]")
            else:
                for name in names:
                    self.console.print(f"[yellow]{name}[/yellow]")

        elif command == "/cost":
            self.console.print(Text.assemble(
                ("tokens → ", "dim"), (f"{self.total_tokens:,}", "green"),
                ("   cost → ", "dim"), (f"${self.total_cost:.4f}", "green"),
            ))

        elif command in ("/exit", "/quit"):
            raise SystemExit(0)

        else:
            self.console.print(f"[red]unknown:[/red] {command}  (try /help)")

    def _handle_mcp(self, arg: str) -> None:
        parts = arg.split(maxsplit=1)
        sub = parts[0].lower() if parts else "list"
        rest = parts[1] if len(parts) > 1 else ""

        if sub in ("", "list"):
            configured = {s.name: s for s in self.config.mcp_servers}
            connected = set(self._mcp_server_tools.keys())
            if not configured and not connected:
                self.console.print("[dim]no MCP servers configured[/dim]")
                return
            all_names = sorted(set(configured) | connected)
            for name in all_names:
                status = "connected" if name in connected else "disconnected"
                color = "green" if name in connected else "#555555"
                n_tools = len(self._mcp_server_tools.get(name, []))
                s = configured.get(name)
                cmd = " ".join(s.full_command) if s else ""
                t = Text()
                t.append(f"  {name:<20}", style="yellow")
                t.append(f"{status:<14}", style=color)
                if n_tools:
                    t.append(f"{n_tools} tools  ", style="dim")
                t.append(cmd, style="dim")
                self.console.print(t)

        elif sub == "add":
            rparts = rest.split(maxsplit=1)
            if len(rparts) < 2:
                self.console.print("[red]usage:[/red] /mcp add <name> <command> [args...]")
                return
            name = rparts[0]
            cmd_parts = rparts[1].split()
            command = cmd_parts[0]
            cmd_args = cmd_parts[1:]
            from cyclops_code.config import MCPServerConfig
            server_cfg = MCPServerConfig(name=name, command=command, args=cmd_args)
            self.config.add_mcp_server(server_cfg)
            n = self._connect_mcp_server(server_cfg)
            if n > 0:
                self._rebuild_agent()

        elif sub == "remove":
            name = rest.strip()
            if not name:
                self.console.print("[red]usage:[/red] /mcp remove <name>")
                return
            self._disconnect_mcp_server(name)
            removed = self.config.remove_mcp_server(name)
            if removed:
                self._rebuild_agent()
                self.console.print(Text.assemble(("mcp remove  ", "dim"), (name, "green")))
            else:
                self.console.print(f"[red]not found:[/red] {name}")

        elif sub == "connect":
            name = rest.strip()
            if not name:
                self.console.print("[red]usage:[/red] /mcp connect <name>")
                return
            cfg = next((s for s in self.config.mcp_servers if s.name == name), None)
            if cfg is None:
                self.console.print(f"[red]not configured:[/red] {name}  (use /mcp add first)")
                return
            n = self._connect_mcp_server(cfg)
            if n > 0:
                self._rebuild_agent()

        elif sub == "disconnect":
            name = rest.strip()
            if not name:
                self.console.print("[red]usage:[/red] /mcp disconnect <name>")
                return
            if self._disconnect_mcp_server(name):
                self._rebuild_agent()
                self.console.print(Text.assemble(("mcp disconnect  ", "dim"), (name, "green")))
            else:
                self.console.print(f"[red]not connected:[/red] {name}")

        else:
            self.console.print(f"[red]unknown mcp subcommand:[/red] {sub}  (list|add|remove|connect|disconnect)")

    def _model_picker(self, agent) -> None:
        models = _get_picker_models()
        current = self.config.model
        self.console.print(Text.assemble(
            ("  current  ", "dim"), (current, "#888888"),
            ("   ·  type to filter", "dim"),
        ))

        model_session = PromptSession(
            completer=ModelCompleter(),
            complete_while_typing=True,
        )
        try:
            choice = model_session.prompt("  model ❯ ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not choice:
            return

        for _, _, model_id in models:
            if choice.lower() == model_id.lower():
                self._set_model(model_id, agent)
                return

        for provider, name, model_id in models:
            if choice.lower() in model_id.lower() or choice.lower() in name.lower():
                self._set_model(model_id, agent)
                return

        self.console.print(f"[red]no match:[/red] {choice}")

    def _set_model(self, model_id: str, agent) -> None:
        self.config.model = model_id
        self.config.save()
        agent.config.model = model_id
        self.console.print(Text.assemble(("model → ", "dim"), (model_id, "green")))


# ── First-run setup ───────────────────────────────────────────────────────────

def _first_run_setup(config: Config, console: Console) -> None:
    console.print()
    console.print(Text.assemble(
        ("( ◉ )", "bold #58a6ff"), ("  cyclops", "bold white"), ("  — first run setup\n", "dim"),
    ))
    console.rule(style="#444444")
    console.print()
    console.print("[dim]Choose a model to get started.[/dim]")
    console.print("[dim]Set API keys via environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.).[/dim]")
    console.print()

    models = _get_picker_models()
    for i, (provider, name, model_id) in enumerate(models[:30]):  # cap at 30 for first run
        is_default = model_id == config.model
        num = Text(f"  {i+1:>3}. ", style="dim")
        if is_default:
            row = Text.assemble(num, ("● ", "bold #58a6ff"), (f"{provider:<12} ", "dim"), (name, "bold white"), (" (default)", "dim"))
        else:
            row = Text.assemble(num, ("  ", ""), (f"{provider:<12} ", "dim"), (name, "#888888"))
        console.print(row)

    console.print()
    model_session = PromptSession(completer=ModelCompleter(), complete_while_typing=True)
    try:
        choice = model_session.prompt("  Select model (Enter to keep default) ❯ ").strip()
    except (KeyboardInterrupt, EOFError):
        choice = ""

    if choice:
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(models[:30]):
                config.model = models[idx][2]
        else:
            for _, _, model_id in models:
                if choice.lower() in model_id.lower():
                    config.model = model_id
                    break

    config.save()
    console.print()
    console.print(Text.assemble(("model → ", "dim"), (config.model, "green")))
    console.print()


# ── Entrypoint wrapper ────────────────────────────────────────────────────────

class REPL:
    """Thin wrapper kept for cli.py compatibility."""

    def __init__(self, config: Config, cwd: str) -> None:
        self._config = config
        self._cwd = cwd

    def run(self) -> None:
        config_file = Path.home() / ".cyclops" / "config.json"
        console = Console()
        if not config_file.exists():
            _first_run_setup(self._config, console)
        repl = CyclopsRepl(self._config, self._cwd)
        repl.run()
