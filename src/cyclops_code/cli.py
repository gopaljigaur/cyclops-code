import logging
import os
from typing import Optional

import click
import litellm

litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from cyclops_code.config import Config, MCPServerConfig


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--model", "-m", default=None, help="LLM model to use")
@click.option("--stream/--no-stream", default=None, help="Enable or disable streaming")
@click.option("--cwd", default=None, help="Working directory (default: current dir)")
@click.argument("prompt", nargs=-1)
@click.pass_context
def main(
    ctx: click.Context,
    model: Optional[str],
    stream: Optional[bool],
    cwd: Optional[str],
    prompt: tuple[str, ...],
) -> None:
    """cyclops: a coding agent for your terminal."""
    config = Config.load()

    if model is not None:
        config.model = model
    if stream is not None:
        config.stream = stream

    working_dir = os.path.abspath(cwd) if cwd else os.getcwd()

    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["cwd"] = working_dir

    if ctx.invoked_subcommand is None:
        if prompt:
            _run_oneshot(" ".join(prompt), config, working_dir)
        else:
            _run_repl(config, working_dir)


# ── mcp subcommand group ──────────────────────────────────────────────────────

@main.group("mcp")
@click.pass_context
def mcp_group(ctx: click.Context) -> None:
    """Manage MCP servers."""
    ctx.ensure_object(dict)
    if "config" not in ctx.obj:
        ctx.obj["config"] = Config.load()


@mcp_group.command("add")
@click.argument("name")
@click.argument("command")
@click.argument("args", nargs=-1)
@click.option("--env", "-e", multiple=True, metavar="KEY=VALUE", help="Extra env vars")
@click.pass_context
def mcp_add(
    ctx: click.Context,
    name: str,
    command: str,
    args: tuple[str, ...],
    env: tuple[str, ...],
) -> None:
    """Add an MCP server to config. Example: cyclops mcp add myserver npx -- -y @server/pkg"""
    console = Console()
    config: Config = ctx.obj["config"]

    env_dict: dict[str, str] = {}
    for pair in env:
        if "=" in pair:
            k, v = pair.split("=", 1)
            env_dict[k] = v
        else:
            console.print(f"[yellow]warning:[/yellow] ignoring malformed env var: {pair}")

    server = MCPServerConfig(name=name, command=command, args=list(args), env=env_dict)
    config.add_mcp_server(server)
    t = Text()
    t.append("mcp add  ", style="dim")
    t.append(name, style="green")
    t.append(f"  {command}", style="dim")
    if args:
        t.append(f" {' '.join(args)}", style="dim")
    console.print(t)


@mcp_group.command("remove")
@click.argument("name")
@click.pass_context
def mcp_remove(ctx: click.Context, name: str) -> None:
    """Remove an MCP server from config."""
    console = Console()
    config: Config = ctx.obj["config"]
    if config.remove_mcp_server(name):
        console.print(Text.assemble(("mcp remove  ", "dim"), (name, "green")))
    else:
        console.print(f"[red]not found:[/red] {name}")


@mcp_group.command("list")
@click.pass_context
def mcp_list(ctx: click.Context) -> None:
    """List configured MCP servers."""
    console = Console()
    config: Config = ctx.obj["config"]
    if not config.mcp_servers:
        console.print("[dim]no MCP servers configured[/dim]")
        return
    for s in config.mcp_servers:
        cmd = " ".join([s.command] + s.args)
        t = Text()
        t.append(f"  {s.name:<20}", style="yellow")
        t.append(cmd, style="dim")
        console.print(t)


# ── oneshot / repl helpers ────────────────────────────────────────────────────

def _run_oneshot(text: str, config: Config, cwd: str) -> None:
    from cyclops import Agent, AgentConfig
    from cyclops_code.prompt import build_system_prompt
    from cyclops_code.tools import ALL_TOOLS

    console = Console()
    agent = Agent(
        AgentConfig(
            model=config.model,
            temperature=config.temperature,
            max_iterations=config.max_iterations,
            system_prompt=build_system_prompt(cwd),
        ),
        tools=ALL_TOOLS,
    )

    if config.stream:
        from rich.live import Live

        full = ""
        with Live(console=console, refresh_per_second=15, vertical_overflow="visible") as live:
            for chunk in agent.stream(text):
                full += chunk
                live.update(Markdown(full))
    else:
        resp = agent.run_with_response(text)
        console.print(Markdown(resp.content))


def _run_repl(config: Config, cwd: str) -> None:
    from cyclops_code.repl import REPL

    repl = REPL(config, cwd)
    repl.run()
