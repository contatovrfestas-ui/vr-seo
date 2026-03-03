"""
Working Memory - memoria de curto prazo da conversa atual.

Mantem o historico de mensagens da sessao atual, com capacidade de:
- Adicionar mensagens (user, assistant, tool results)
- Truncar quando excede limites de tokens
- Sumarizar mensagens antigas para preservar contexto
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("aurora.memory.working")


@dataclass
class Message:
    """Uma mensagem na conversa."""

    role: str  # "user", "assistant", "system"
    content: Any  # str ou list (para tool results)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_api_format(self) -> dict[str, Any]:
        """Converte para o formato esperado pela API do LLM."""
        return {"role": self.role, "content": self.content}

    def estimate_tokens(self) -> int:
        """Estimativa grosseira de tokens (4 chars ~= 1 token)."""
        if isinstance(self.content, str):
            return len(self.content) // 4
        elif isinstance(self.content, list):
            total = 0
            for item in self.content:
                if isinstance(item, dict):
                    if "content" in item:
                        total += len(str(item["content"])) // 4
                    else:
                        total += len(str(item)) // 4
                else:
                    total += len(str(item)) // 4
            return total
        return 0


class WorkingMemory:
    """
    Memoria de trabalho da conversa atual.

    Funciona como um buffer de mensagens com limites configurados.
    Quando o buffer excede os limites, as mensagens mais antigas
    sao descartadas ou sumarizadas.
    """

    def __init__(
        self,
        max_messages: int = 50,
        max_tokens: int = 100000,
    ) -> None:
        self._messages: list[Message] = []
        self._max_messages = max_messages
        self._max_tokens = max_tokens
        self._summary: str = ""  # Resumo de mensagens descartadas

    def add(self, role: str, content: Any) -> None:
        """Adiciona uma mensagem a memoria de trabalho."""
        msg = Message(role=role, content=content)
        self._messages.append(msg)

        # Verifica limites
        self._enforce_limits()

    def get_messages(self) -> list[dict[str, Any]]:
        """
        Retorna todas as mensagens no formato da API.
        Inclui o resumo como primeira mensagem se existir.
        """
        messages = []

        # Se temos um resumo de mensagens anteriores, inclui como contexto
        if self._summary:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"[Contexto da conversa anterior: {self._summary}]\n\n"
                        "Continue a conversa normalmente."
                    ),
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": "Entendido, tenho o contexto da conversa anterior. Como posso ajudar?",
                }
            )

        for msg in self._messages:
            messages.append(msg.to_api_format())

        return messages

    def get_last_user_message(self) -> str | None:
        """Retorna a ultima mensagem do usuario."""
        for msg in reversed(self._messages):
            if msg.role == "user" and isinstance(msg.content, str):
                return msg.content
        return None

    def get_message_count(self) -> int:
        """Numero de mensagens na memoria."""
        return len(self._messages)

    def estimate_total_tokens(self) -> int:
        """Estima o total de tokens nas mensagens."""
        total = len(self._summary) // 4 if self._summary else 0
        for msg in self._messages:
            total += msg.estimate_tokens()
        return total

    def clear(self) -> None:
        """Limpa toda a memoria de trabalho."""
        self._messages.clear()
        self._summary = ""

    def set_summary(self, summary: str) -> None:
        """Define o resumo de mensagens anteriores (consolidacao)."""
        self._summary = summary

    def _enforce_limits(self) -> None:
        """Remove mensagens antigas se exceder os limites."""
        # Limite por numero de mensagens
        while len(self._messages) > self._max_messages:
            removed = self._messages.pop(0)
            logger.debug(
                f"Mensagem removida por limite de quantidade: {removed.role}"
            )

        # Limite por tokens estimados
        while (
            self.estimate_total_tokens() > self._max_tokens
            and len(self._messages) > 2
        ):
            removed = self._messages.pop(0)
            logger.debug(
                f"Mensagem removida por limite de tokens: {removed.role}"
            )

    def get_conversation_text(self) -> str:
        """Retorna a conversa como texto plano (para sumarizacao)."""
        lines = []
        for msg in self._messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            lines.append(f"{msg.role}: {content}")
        return "\n".join(lines)
