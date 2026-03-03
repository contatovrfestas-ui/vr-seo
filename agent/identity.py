"""
Sistema de identidade do agente Aurora SEO.

Carrega a configuracao de persona do YAML e compila em um system prompt
dinamico. A identidade define personalidade, especialidades, estilo de
comunicacao e limites comportamentais do agente.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger("aurora.identity")


class AgentIdentity:
    """
    Gerencia a identidade e personalidade do agente.

    Carrega configuracao de um arquivo YAML e gera o system prompt
    dinamicamente, incluindo contexto temporal e memoria relevante.
    """

    def __init__(self, persona_path: str | Path) -> None:
        self._persona_path = Path(persona_path)
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Carrega o arquivo YAML de persona."""
        if not self._persona_path.exists():
            logger.warning(
                f"Arquivo de persona nao encontrado: {self._persona_path}. "
                "Usando configuracao padrao."
            )
            self._config = self._default_config()
            return

        with open(self._persona_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        logger.info(f"Persona carregada: {self.name} ({self.role})")

    def _default_config(self) -> dict[str, Any]:
        """Configuracao padrao caso o YAML nao exista."""
        return {
            "name": "Aurora SEO",
            "role": "Agente autonomo especialista em SEO",
            "personality_traits": ["proativo", "analitico", "profissional"],
            "communication_style": "Direto e profissional",
            "boundaries": [
                "Nunca executar operacoes destrutivas sem confirmacao"
            ],
            "expertise": ["Auditoria SEO", "Geracao de conteudo"],
            "language": "pt-BR",
            "proactive_behaviors": [],
            "greeting": "Ola! Sou o Aurora SEO. Como posso ajudar?",
        }

    @property
    def name(self) -> str:
        return self._config.get("name", "Aurora SEO")

    @property
    def role(self) -> str:
        return self._config.get("role", "Agente SEO")

    @property
    def language(self) -> str:
        return self._config.get("language", "pt-BR")

    @property
    def greeting(self) -> str:
        return self._config.get("greeting", f"Ola! Sou o {self.name}.")

    @property
    def traits(self) -> list[str]:
        return self._config.get("personality_traits", [])

    @property
    def expertise(self) -> list[str]:
        return self._config.get("expertise", [])

    @property
    def boundaries(self) -> list[str]:
        return self._config.get("boundaries", [])

    @property
    def proactive_behaviors(self) -> list[str]:
        return self._config.get("proactive_behaviors", [])

    def build_system_prompt(
        self,
        memory_context: Optional[str] = None,
        active_tools: Optional[list[str]] = None,
        pending_tasks: Optional[list[str]] = None,
    ) -> str:
        """
        Gera o system prompt completo do agente.

        Combina a identidade da persona com contexto dinamico:
        - Data/hora atual
        - Memorias relevantes
        - Ferramentas disponiveis
        - Tarefas pendentes

        Args:
            memory_context: Memorias relevantes recuperadas do long-term store
            active_tools: Nomes das ferramentas ativas no registro
            pending_tasks: Tarefas pendentes que o agente deve lembrar

        Returns:
            System prompt compilado
        """
        now = datetime.now()
        sections: list[str] = []

        # Secao 1: Identidade core
        sections.append(self._build_identity_section())

        # Secao 2: Especialidades e capacidades
        sections.append(self._build_expertise_section(active_tools))

        # Secao 3: Comportamento e limites
        sections.append(self._build_behavior_section())

        # Secao 4: Contexto temporal
        sections.append(
            f"## Contexto Atual\n"
            f"- Data: {now.strftime('%d/%m/%Y')}\n"
            f"- Hora: {now.strftime('%H:%M')}\n"
            f"- Idioma padrao: {self.language}"
        )

        # Secao 5: Memoria (se houver)
        if memory_context:
            sections.append(
                f"## Contexto de Memoria\n"
                f"Informacoes relevantes de interacoes anteriores:\n\n"
                f"{memory_context}"
            )

        # Secao 6: Tarefas pendentes (se houver)
        if pending_tasks:
            task_list = "\n".join(f"- {t}" for t in pending_tasks)
            sections.append(
                f"## Tarefas Pendentes\n"
                f"O usuario tem as seguintes tarefas em andamento:\n\n"
                f"{task_list}"
            )

        # Secao 7: Comportamento proativo
        if self.proactive_behaviors:
            sections.append(self._build_proactive_section())

        return "\n\n".join(sections)

    def _build_identity_section(self) -> str:
        """Constroi a secao de identidade do system prompt."""
        traits_str = ", ".join(self.traits) if self.traits else "profissional"
        style = self._config.get("communication_style", "Direto e profissional")

        return (
            f"# Identidade\n"
            f"Voce e **{self.name}**, {self.role}.\n\n"
            f"## Personalidade\n"
            f"Tracos: {traits_str}\n"
            f"Estilo de comunicacao: {style}\n\n"
            f"Voce sempre responde em {self.language} a menos que o usuario "
            f"solicite outro idioma."
        )

    def _build_expertise_section(
        self, active_tools: Optional[list[str]] = None
    ) -> str:
        """Constroi a secao de especialidades."""
        lines = ["## Especialidades"]
        for exp in self.expertise:
            lines.append(f"- {exp}")

        if active_tools:
            lines.append("\n## Ferramentas Disponiveis")
            lines.append(
                "Voce tem acesso as seguintes ferramentas para executar "
                "tarefas autonomamente. Use-as quando necessario para "
                "responder o usuario com dados reais:"
            )
            for tool_name in active_tools:
                lines.append(f"- `{tool_name}`")

        return "\n".join(lines)

    def _build_behavior_section(self) -> str:
        """Constroi a secao de comportamento e limites."""
        lines = ["## Diretrizes de Comportamento"]

        lines.append("\n### Limites")
        for boundary in self.boundaries:
            lines.append(f"- {boundary}")

        lines.append("\n### Regras Gerais")
        lines.append(
            "- Sempre explique seu raciocinio antes de executar acoes complexas"
        )
        lines.append(
            "- Ao usar ferramentas, informe ao usuario o que esta fazendo"
        )
        lines.append(
            "- Se uma tarefa requer multiplos passos, apresente o plano antes"
        )
        lines.append(
            "- Quando encontrar erros, explique o problema e sugira alternativas"
        )
        lines.append(
            "- Salve fatos importantes sobre o usuario na memoria de longo prazo"
        )

        return "\n".join(lines)

    def _build_proactive_section(self) -> str:
        """Constroi a secao de comportamento proativo."""
        lines = [
            "## Comportamento Proativo",
            "Quando apropriado, voce deve proativamente:",
        ]
        for behavior in self.proactive_behaviors:
            lines.append(f"- {behavior}")

        return "\n".join(lines)
