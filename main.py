#!/usr/bin/env python3
"""
VR SEO Aurora - Agente Autonomo de SEO
Entry point: loop de chat interativo no terminal.

Uso:
    python main.py           # Inicia o chat interativo
    python main.py --help    # Mostra opcoes
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretorio do projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from config.settings import get_settings, DATA_DIR
from agent.core import AgentCore
from agent.identity import AgentIdentity
from agent.llm import LLMClient
from agent.memory.manager import MemoryManager
from agent.tools.registry import create_default_registry

# Tema do terminal
THEME = Theme(
    {
        "agent_name": "bold cyan",
        "user_name": "bold green",
        "info": "dim",
        "warning": "yellow",
        "error": "bold red",
        "tool": "magenta",
    }
)

console = Console(theme=THEME)


def setup_logging(level: str = "WARNING") -> None:
    """Configura logging - WARNING por padrao para nao poluir o chat."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.WARNING),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Silencia logs verbosos de bibliotecas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def create_agent() -> AgentCore:
    """
    Factory que cria e configura o agente completo.

    Inicializa todos os componentes na ordem correta:
    1. Settings (carrega .env)
    2. Identity (carrega persona.yaml)
    3. LLM client
    4. Memory manager
    5. Tool registry
    6. AgentCore
    """
    settings = get_settings()

    # Identity
    identity = AgentIdentity(persona_path=settings.persona_path)

    # LLM Client
    if not settings.anthropic.api_key:
        console.print(
            "[error]ANTHROPIC_API_KEY nao configurada.[/error]\n"
            "Configure no arquivo .env ou execute:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...",
        )
        sys.exit(1)

    llm = LLMClient(
        api_key=settings.anthropic.api_key,
        model=settings.anthropic.model,
        max_tokens=settings.anthropic.max_tokens,
    )

    # Memory
    memory = MemoryManager(
        db_path=settings.memory.db_path,
        max_working_messages=settings.memory.max_working_memory_messages,
        max_context_tokens=settings.memory.max_context_tokens,
        consolidation_threshold=settings.memory.consolidation_threshold,
    )

    # Tools
    tools = create_default_registry()

    # Core
    agent = AgentCore(
        llm=llm,
        identity=identity,
        memory=memory,
        tools=tools,
    )

    return agent


def show_banner(agent_name: str) -> None:
    """Mostra o banner de boas-vindas."""
    banner = Text()
    banner.append("VR SEO Aurora", style="bold cyan")
    banner.append(" v2.0\n", style="dim")
    banner.append(f"Agente: {agent_name}\n", style="cyan")
    banner.append("Digite sua mensagem ou /help para comandos.", style="dim")

    console.print(
        Panel(
            banner,
            border_style="cyan",
            padding=(1, 2),
        )
    )


def show_help() -> None:
    """Mostra comandos disponiveis."""
    help_text = """
## Comandos

| Comando | Descricao |
|---------|-----------|
| `/help` | Mostra esta ajuda |
| `/tools` | Lista ferramentas disponiveis |
| `/memory` | Mostra status da memoria |
| `/tasks` | Lista tarefas pendentes |
| `/clear` | Limpa a conversa atual |
| `/exit` ou `/quit` | Encerra o agente |

## Exemplos de uso

- "Audite o site https://example.com"
- "Gere um blog post sobre SEO para e-commerce"
- "Quais sao minhas top queries no Search Console?"
- "Crie schema markup para minha pagina de contato"
- "Analise as meta tags de https://example.com"
"""
    console.print(Markdown(help_text))


async def handle_command(command: str, agent: AgentCore) -> bool:
    """
    Processa comandos especiais (prefixados com /).

    Returns:
        True se o comando foi processado, False se deve ser tratado como mensagem
    """
    cmd = command.strip().lower()

    if cmd in ("/exit", "/quit", "/sair"):
        return True  # Signal to exit

    elif cmd == "/help":
        show_help()

    elif cmd == "/tools":
        tools = agent.tools.list_names()
        console.print("\n[bold]Ferramentas disponiveis:[/bold]")
        for name in tools:
            tool = agent.tools.get(name)
            desc = tool.description[:80] if tool else ""
            console.print(f"  [tool]{name}[/tool] - {desc}")
        console.print()

    elif cmd == "/memory":
        msg_count = agent.memory.working.get_message_count()
        tokens = agent.memory.working.estimate_total_tokens()
        facts = await agent.memory.list_facts()
        tasks = await agent.memory.list_tasks()

        console.print("\n[bold]Status da Memoria:[/bold]")
        console.print(f"  Working memory: {msg_count} mensagens (~{tokens} tokens)")
        console.print(f"  Fatos salvos: {len(facts)}")
        console.print(f"  Tarefas pendentes: {len(tasks)}")
        console.print()

    elif cmd == "/tasks":
        tasks = await agent.memory.list_tasks()
        if tasks:
            console.print("\n[bold]Tarefas Pendentes:[/bold]")
            for t in tasks:
                console.print(f"  [#{t['id']}] {t['description']}")
        else:
            console.print("\n[info]Nenhuma tarefa pendente.[/info]")
        console.print()

    elif cmd == "/clear":
        agent.memory.working.clear()
        console.print("[info]Conversa limpa.[/info]\n")

    else:
        console.print(f"[warning]Comando desconhecido: {cmd}[/warning]")
        console.print("[info]Digite /help para ver comandos disponiveis.[/info]\n")

    return False


async def chat_loop(agent: AgentCore) -> None:
    """Loop principal de chat interativo."""
    # Historico de comandos persistente
    history_path = DATA_DIR / "chat_history.txt"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    session: PromptSession = PromptSession(
        history=FileHistory(str(history_path)),
        auto_suggest=AutoSuggestFromHistory(),
    )

    # Greeting
    greeting = await agent.get_greeting()
    console.print(f"\n[agent_name]{agent.identity.name}:[/agent_name] {greeting}\n")

    while True:
        try:
            # Prompt do usuario
            user_input = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: session.prompt(
                    "\nvoc\u00ea > ",
                ),
            )

            user_input = user_input.strip()
            if not user_input:
                continue

            # Processa comandos /
            if user_input.startswith("/"):
                should_exit = await handle_command(user_input, agent)
                if should_exit:
                    break
                continue

            # Processa mensagem com o agente
            console.print(f"\n[agent_name]{agent.identity.name}:[/agent_name] ", end="")

            with console.status("[tool]Pensando...[/tool]", spinner="dots"):
                response = await agent.process_message(user_input)

            # Renderiza resposta como Markdown
            console.print()
            console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n[info]Use /exit para sair.[/info]")
            continue

        except EOFError:
            break

        except Exception as e:
            console.print(f"\n[error]Erro: {e}[/error]")
            logging.getLogger("aurora").exception("Erro no chat loop")


async def main() -> None:
    """Entry point principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="VR SEO Aurora - Agente Autonomo de SEO"
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de logging (default: WARNING)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="VR SEO Aurora v2.0.0",
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    # Cria o agente
    agent = create_agent()
    show_banner(agent.identity.name)

    try:
        await chat_loop(agent)
    finally:
        # Shutdown gracioso
        console.print("\n[info]Salvando sessao...[/info]")
        await agent.on_shutdown()
        console.print("[info]Ate a proxima![/info]\n")


if __name__ == "__main__":
    asyncio.run(main())
