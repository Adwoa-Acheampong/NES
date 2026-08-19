"""``nes chat`` — interactive multi-turn chat REPL."""

from __future__ import annotations

import logging
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict
from collections import defaultdict

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from nes.cli._tool_names import resolve_tool_names
from nes.core.config import load_config
from nes.core.events import EventBus
from nes.core.types import Message, Role
from nes.memory import publish_completed_exchange

logger = logging.getLogger(__name__)

_prompt_session = None

def _get_available_agents() -> List[str]:
    """Scans ~/.nes/agents/ to provide autocompletion and discovery."""
    agents_dir = Path.home() / ".nes" / "agents"
    if agents_dir.exists():
        return sorted([d.name for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith('_')])
    return []

def _get_completer():
    """Builds a nested completer for slash commands and agent names."""
    try:
        from prompt_toolkit.completion import NestedCompleter, WordCompleter
        agents = _get_available_agents()
        commands = {
            '/quit': None, '/exit': None, '/q': None,
            '/clear': None, '/model': None, '/help': None,
            '/history': None, '/paste': None, '/memory': None,
            '/agents': None,
            '/use': WordCompleter(agents, sentence=True)
        }
        return NestedCompleter.from_nested_dict(commands)
    except ImportError:
        return None

def _read_input(prompt: str = "You> ") -> Optional[str]:
    """Read user input with graceful EOF handling, Markdown syntax highlighting, and autocompletion."""
    global _prompt_session
    try:
        if _prompt_session is None:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.lexers import PygmentsLexer
            from pygments.lexers.markup import MarkdownLexer
            from pygments.styles import get_style_by_name
            from prompt_toolkit.styles import style_from_pygments_cls
            
            style = style_from_pygments_cls(get_style_by_name("monokai"))
            _prompt_session = PromptSession(
                lexer=PygmentsLexer(MarkdownLexer), 
                style=style,
                completer=_get_completer()
            )
        return _prompt_session.prompt(prompt)
    except ImportError:
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None
    except (EOFError, KeyboardInterrupt):
        return None


@click.command()
@click.option("-e", "--engine", "engine_key", default=None, help="Engine backend.")
@click.option("-m", "--model", "model_name", default=None, help="Model to use.")
@click.option("-a", "--agent", "agent_name", default=None, help="Agent type.")
@click.option("--tools", default=None, help="Comma-separated tool names.")
@click.option("--system", "system_prompt", default=None, help="Custom system prompt.")
@click.option(
    "--persona",
    "persona_name",
    default=None,
    help=(
        "Named persona dir under ~/.nes/personas/<name>/ "
        "(overrides config). Pass 'none' to disable all persona files."
    ),
)
def chat(
    engine_key: str | None,
    model_name: str | None,
    agent_name: str | None,
    tools: str | None,
    system_prompt: str | None,
    persona_name: str | None,
) -> None:
    """Start an interactive multi-turn chat session.

    Commands during chat:
      /quit, /exit  — end session
      /clear        — clear conversation history
      /model        — show current model
      /agents       — list all available agents by domain cluster
      /use <name>   — hot-swap to a specific agent
      /memory       — inspect agentic memory state
      /help         — show available commands
      /history      — show conversation history
    """
    console = Console(stderr=True)

    config = load_config()
    bus = EventBus(record_history=False)

    import dataclasses as _dc

    effective_mf = (
        _dc.replace(config.memory_files, persona_name=persona_name)
        if persona_name is not None
        else config.memory_files
    )

    # Resolve engine
    from nes.engine import get_engine
    from nes.intelligence import register_builtin_models

    register_builtin_models()

    resolved = get_engine(config, engine_key)
    if resolved is None:
        console.print("[red]No inference engine available.[/red]")
        sys.exit(1)

    engine_name, engine = resolved
    model = model_name or config.intelligence.default_model
    if not model:
        from nes.engine import discover_engines, discover_models

        all_engines = discover_engines(config)
        all_models = discover_models(all_engines)
        engine_models = all_models.get(engine_name, [])
        if engine_models:
            model = engine_models[0]
        else:
            console.print("[red]No model available.[/red]")
            sys.exit(1)

    # Resolve agent (optional)
    agent = None
    agent_key = agent_name or config.agent.default_agent
    if agent_key and agent_key != "none":
        try:
            import nes.agents  # noqa: F401 — trigger registration
            from nes.core.registry import AgentRegistry

            if AgentRegistry.contains(agent_key):
                agent_cls = AgentRegistry.get(agent_key)
                kwargs: dict = {"bus": bus}

                if getattr(agent_cls, "accepts_tools", False):
                    tool_names_list = resolve_tool_names(
                        tools,
                        getattr(config.tools, "enabled", None),
                        getattr(config.agent, "tools", None),
                    )
                    if tool_names_list:
                        import nes.tools  # noqa: F401 — trigger registration
                        from nes.core.registry import ToolRegistry
                        from nes.tools._stubs import BaseTool

                        tool_instances = []
                        for tname in tool_names_list:
                            if ToolRegistry.contains(tname):
                                tcls = ToolRegistry.get(tname)
                                if isinstance(tcls, type) and issubclass(
                                    tcls, BaseTool
                                ):
                                    tool_instances.append(tcls())
                                elif isinstance(tcls, BaseTool):
                                    tool_instances.append(tcls)
                        if tool_instances:
                            kwargs["tools"] = tool_instances
                    kwargs["max_turns"] = config.agent.max_turns

                    def _confirm(prompt: str) -> bool:
                        console.print(
                            f"[yellow]Confirm:[/yellow] {prompt} [y/N] ",
                            end="",
                        )
                        ans = input().strip().lower()
                        return ans in ("y", "yes")

                    kwargs["interactive"] = True
                    kwargs["confirm_callback"] = _confirm

                import inspect as _inspect

                if (
                    "prompt_builder"
                    in _inspect.signature(agent_cls.__init__).parameters
                ):
                    from nes.prompt.builder import SystemPromptBuilder

                    kwargs["prompt_builder"] = SystemPromptBuilder(
                        agent_template=config.agent.default_system_prompt or "",
                        memory_files_config=effective_mf,
                        system_prompt_config=config.system_prompt,
                    )

                agent = agent_cls(engine, model, **kwargs)
        except Exception as exc:
            console.print(f"[yellow]Agent '{agent_key}' failed: {exc}[/yellow]")

    # Print banner
    from nes.cli._banner import print_banner
    print_banner()
    console.print(
        f"[green bold]NES Chat[/green bold]\n"
        f"  Engine: [cyan]{engine_name}[/cyan]  Model: [cyan]{model}[/cyan]"
        f"  Agent: [cyan]{agent_key or 'direct'}[/cyan]\n"
        f"  Type /help for commands, /quit to exit.\n"
    )

    # Background-work status banner (disappears after first user message)
    from nes.cli._bg_state import get_status
    from nes.cli._chat_banner import render_startup_banner

    _banner = render_startup_banner(get_status())
    if _banner:
        console.print(f"[dim cyan]{_banner}[/dim cyan]")

    # Completion-notification dispatcher (fires once per task per session)
    from nes.cli._chat_notifications import NotificationDispatcher

    _notifications = NotificationDispatcher(get_status())

    # Automatic long-term memory — extracts durable facts in the background.
    memory_service = None
    try:
        from nes.memory import build_memory_service

        memory_service = build_memory_service(config, engine, model, event_bus=bus)
        if memory_service is not None:
            memory_service.start()
            console.print("[dim]  Memory: active[/dim]")
    except Exception as exc:
        console.print(f"[yellow]Memory service unavailable: {exc}[/yellow]")
        memory_service = None

    # The document backend and automatic fact store are separate persistence
    # mechanisms. Context injection combines both at read time so facts from
    # previous sessions are immediately available without a manual index step.
    memory_backend = None
    if config.agent.context_from_memory:
        from nes.cli.ask import _get_memory_backend

        memory_backend = _get_memory_backend(config)

    # Conversation state
    if not system_prompt:
        from nes.prompt.builder import SystemPromptBuilder

        builder = SystemPromptBuilder(
            agent_template=config.agent.default_system_prompt or "",
            memory_files_config=effective_mf,
            system_prompt_config=config.system_prompt,
        )
        system_prompt = builder.build()

    history: List[Message] = []
    if system_prompt:
        history.append(Message(role=Role.SYSTEM, content=system_prompt))

    # REPL loop
    while True:
        for note in _notifications.diff(get_status()):
            console.print(f"[dim cyan]{note}[/dim cyan]")

        user_input = _read_input()
        if user_input is None:
            console.print("\n[dim]Goodbye![/dim]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Handle slash commands
        cmd = user_input.lower().strip()
        
        if cmd == "/paste":
            console.print(Panel("[dim]Multi-line paste mode. Paste your text, then type '/end' on a new line (or press Ctrl-Z/Ctrl-D) to submit.[/dim]", title="Paste Mode", border_style="blue"))
            lines = []
            try:
                while True:
                    line = input("... ")
                    if line.strip().lower() == "/end":
                        break
                    lines.append(line)
            except (EOFError, KeyboardInterrupt):
                pass
            user_input = "\n".join(lines).strip()
            if not user_input:
                continue
            cmd = user_input.lower()

        if cmd in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye![/dim]")
            break
        elif cmd == "/clear":
            history = []
            if system_prompt:
                history.append(Message(role=Role.SYSTEM, content=system_prompt))
            console.print("[dim]History cleared.[/dim]")
            continue
        elif cmd == "/model":
            console.print(
                f"Model: [cyan]{model}[/cyan]  Engine: [cyan]{engine_name}[/cyan]"
            )
            continue
        elif cmd == "/agents":
            agents = _get_available_agents()
            if not agents:
                console.print("[yellow]No agents found in ~/.nes/agents/[/yellow]")
                continue
            
            # Group by prefix (e.g., engineering-, marketing-)
            clusters = defaultdict(list)
            for a in agents:
                if "-" in a:
                    cluster = a.split("-")[0]
                else:
                    cluster = "general"
                clusters[cluster].append(a)
                
            table = Table(title="Available NES Agent Clusters")
            table.add_column("Domain Cluster", style="cyan", no_wrap=True)
            table.add_column("Agents", style="green")
            
            for cluster, members in sorted(clusters.items()):
                table.add_row(cluster.upper(), ", ".join(members))
            console.print(table)
            continue
        elif cmd.startswith("/use "):
            target_agent = user_input[5:].strip()
            console.print(f"[yellow]Hot-swapping to agent: {target_agent}...[/yellow]")
            try:
                import nes.agents  # noqa: F401
                from nes.core.registry import AgentRegistry
                if AgentRegistry.contains(target_agent):
                    agent_cls = AgentRegistry.get(target_agent)
                    kwargs = {"bus": bus, "max_turns": config.agent.max_turns}
                    
                    import inspect as _inspect
                    if "prompt_builder" in _inspect.signature(agent_cls.__init__).parameters:
                        from nes.prompt.builder import SystemPromptBuilder
                        kwargs["prompt_builder"] = SystemPromptBuilder(
                            agent_template=config.agent.default_system_prompt or "",
                            memory_files_config=effective_mf,
                            system_prompt_config=config.system_prompt,
                        )
                    
                    agent = agent_cls(engine, model, **kwargs)
                    agent_key = target_agent
                    console.print(f"[green]Successfully switched to {target_agent}[/green]")
                    
                    # Reset system prompt for the new agent
                    if hasattr(agent, "prompt_builder"):
                        system_prompt = agent.prompt_builder.build()
                        history = [Message(role=Role.SYSTEM, content=system_prompt)]
                else:
                    console.print(f"[red]Agent '{target_agent}' not found in registry.[/red]")
            except Exception as e:
                console.print(f"[red]Failed to swap agent: {e}[/red]")
            continue
        elif cmd == "/memory":
            if memory_backend and hasattr(memory_backend, "count"):
                count = memory_backend.count()
                console.print(f"[cyan]Memory Backend:[/cyan] {type(memory_backend).__name__}")
                console.print(f"[cyan]Stored Facts:[/cyan] {count}")
            elif memory_service and hasattr(memory_service, "list_facts"):
                facts = memory_service.list_facts()
                console.print(f"[cyan]Memory Service:[/cyan] Active ({len(facts)} facts loaded)")
            else:
                console.print("[yellow]Memory service not active or no backend configured.[/yellow]")
            continue
        elif cmd == "/help":
            console.print(
                "[bold]Commands:[/bold]\n"
                "  /quit, /exit  — end session\n"
                "  /clear        — clear conversation\n"
                "  /model        — show model info\n"
                "  /agents       — list all 200+ agents by domain cluster\n"
                "  /use <name>   — hot-swap to a specific agent\n"
                "  /memory       — inspect agentic memory state\n"
                "  /history      — show conversation\n"
                "  /help         — this message"
            )
            continue
        elif cmd == "/history":
            if not history:
                console.print("[dim]No history yet.[/dim]")
            else:
                for msg in history:
                    role_str = msg.role if isinstance(msg.role, str) else msg.role.value
                    role = role_str.upper()
                    console.print(f"[bold]{role}:[/bold] {msg.content[:200]}")
            continue

        # Add user message
        history.append(Message(role=Role.USER, content=user_input))

        generation_history = history
        agent_context_message = None
        if config.agent.context_from_memory:
            try:
                from nes.memory import load_configured_facts
                from nes.tools.storage.context import (
                    ContextConfig,
                    inject_context,
                )

                if memory_service is not None and hasattr(memory_service, "list_facts"):
                    facts = memory_service.list_facts()
                else:
                    facts = load_configured_facts(config)
                ctx_cfg = ContextConfig(
                    top_k=config.memory.context_top_k,
                    min_score=config.memory.context_min_score,
                    max_context_tokens=config.memory.context_max_tokens,
                )
                context_messages = inject_context(
                    user_input,
                    [] if agent is not None else history,
                    memory_backend,
                    config=ctx_cfg,
                    facts=facts,
                )
                if agent is not None:
                    if context_messages:
                        agent_context_message = context_messages[0]
                else:
                    generation_history = context_messages
            except Exception:
                logger.debug("Failed to inject memory context", exc_info=True)

        # Generate response even when optional memory context is unavailable.
        try:
            with console.status("[bold cyan]NES is thinking...[/bold cyan]", spinner="dots") as status:
                if agent is not None:
                    from nes.agents._stubs import AgentContext

                    agent_context = AgentContext()
                    if agent_context_message is not None:
                        agent_context.conversation.add(agent_context_message)
                    for msg in history[:-1]:
                        if msg.role != Role.SYSTEM:
                            agent_context.conversation.add(msg)
                    response = agent.run(user_input, context=agent_context)
                    content = (
                        response.content if hasattr(response, "content") else str(response)
                    )
                else:
                    result = engine.generate(generation_history, model=model)
                    content = (
                        result.get("content", "")
                        if isinstance(result, dict)
                        else str(result)
                    )
                
                status.stop() # Stop spinner before printing

            history.append(Message(role=Role.ASSISTANT, content=content))
            console.print()
            console.print(Markdown(content))
            console.print()

            publish_completed_exchange(
                bus,
                user_input,
                content,
                source="cli.chat",
            )
        except KeyboardInterrupt:
            console.print("\n[dim]Generation interrupted.[/dim]")
        except Exception as exc:
            console.print(f"\n[red]Error: {exc}[/red]\n")

    if memory_service is not None:
        memory_service.stop()


__all__ = ["chat"]
