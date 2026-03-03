"""
Abstracao do cliente LLM - provider agnostic.

Design: o agente nao conhece o provider diretamente. Esta camada
isola a logica de chamada ao LLM, permitindo trocar de provider
(Anthropic, OpenAI, Google) sem alterar o codigo do agente.

Suporta:
- Chat simples (mensagens -> resposta)
- Tool use (function calling nativo do Claude)
- Streaming (futuro)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import anthropic

logger = logging.getLogger("aurora.llm")


@dataclass
class ToolCall:
    """Representa uma chamada de ferramenta solicitada pelo LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Resposta padronizada do LLM, independente do provider."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    @property
    def is_end_turn(self) -> bool:
        return self.stop_reason == "end_turn"


def _build_tool_schema(tool_class: Any) -> dict:
    """
    Converte uma classe de tool (com schema Pydantic) para o formato
    de tool do Anthropic API.
    """
    schema = tool_class.parameters.model_json_schema()

    # Remove chaves que o Anthropic nao aceita no input_schema
    schema.pop("title", None)

    # Converte $defs para definitions se necessario
    if "$defs" in schema:
        schema["definitions"] = schema.pop("$defs")

    return {
        "name": tool_class.name,
        "description": tool_class.description,
        "input_schema": schema,
    }


class LLMClient:
    """
    Cliente LLM com suporte a tool-use.

    Encapsula a comunicacao com o provider e normaliza as respostas
    para um formato unico usado pelo core do agente.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> None:
        if not api_key:
            raise ValueError(
                "API key e obrigatoria. Configure ANTHROPIC_API_KEY no .env"
            )

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

        logger.info(f"LLM client inicializado: model={model}")

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: Optional[list[Any]] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Envia mensagens para o LLM e retorna resposta padronizada.

        Args:
            messages: Lista de mensagens no formato [{"role": ..., "content": ...}]
            system: System prompt
            tools: Lista de classes de tools registradas (com .name, .description, .parameters)
            max_tokens: Override do max_tokens padrao

        Returns:
            LLMResponse com texto, tool_calls, e metadados
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        # Converter tools para formato Anthropic
        if tools:
            kwargs["tools"] = [_build_tool_schema(t) for t in tools]

        logger.debug(
            f"LLM request: {len(messages)} messages, "
            f"{len(tools or [])} tools, model={self.model}"
        )

        try:
            response = self._client.messages.create(**kwargs)
            return self._parse_response(response)
        except anthropic.APIError as e:
            logger.error(f"Erro na API do LLM: {e}")
            raise

    def _parse_response(self, response: Any) -> LLMResponse:
        """Converte a resposta do Anthropic para o formato padronizado."""
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        result = LLMResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage=usage,
            raw=response,
        )

        logger.debug(
            f"LLM response: {len(result.text)} chars, "
            f"{len(tool_calls)} tool_calls, stop={response.stop_reason}"
        )

        return result

    def format_tool_result(
        self, tool_call_id: str, result: str, is_error: bool = False
    ) -> dict[str, Any]:
        """
        Formata o resultado de uma tool call para enviar de volta ao LLM.

        Args:
            tool_call_id: ID da tool call original
            result: String com o resultado da execucao
            is_error: Se True, marca como erro

        Returns:
            Mensagem formatada para incluir na conversa
        """
        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": result,
            "is_error": is_error,
        }
