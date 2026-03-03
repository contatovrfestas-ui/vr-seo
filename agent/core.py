"""
Core do agente Aurora SEO - loop principal ReAct.

Implementa o ciclo:
  Receive input -> Think -> Decide (respond or use tool) -> Act -> Observe -> Repeat

O core orquestra todos os componentes:
- Identity (system prompt)
- Memory (working + long-term)
- Tools (registry + dispatch)
- LLM (chamadas ao modelo)
- Planner (tarefas multi-step)
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

from agent.identity import AgentIdentity
from agent.llm import LLMClient, LLMResponse
from agent.memory.manager import MemoryManager
from agent.planner import Planner
from agent.tools.memory_tool import MemoryTool
from agent.tools.registry import ToolRegistry

logger = logging.getLogger("aurora.core")

# Limite de iteracoes do loop de tools para evitar loops infinitos
MAX_TOOL_ITERATIONS = 15


class AgentCore:
    """
    Nucleo do agente autonomo Aurora SEO.

    Coordena identity, memory, tools e LLM em um loop ReAct.
    """

    def __init__(
        self,
        llm: LLMClient,
        identity: AgentIdentity,
        memory: MemoryManager,
        tools: ToolRegistry,
    ) -> None:
        self.llm = llm
        self.identity = identity
        self.memory = memory
        self.tools = tools
        self.planner = Planner()

        # Injeta o memory manager na MemoryTool
        MemoryTool.set_memory_manager(memory)

        logger.info(
            f"AgentCore inicializado: {identity.name} com "
            f"{len(tools)} tools"
        )

    async def process_message(self, user_input: str) -> str:
        """
        Processa uma mensagem do usuario e retorna a resposta do agente.

        Este e o metodo principal do loop ReAct:
        1. Adiciona a mensagem do usuario na working memory
        2. Recupera contexto da memoria de longo prazo
        3. Constroi o system prompt com identidade + contexto
        4. Envia para o LLM com as tools disponiveis
        5. Se o LLM pedir tools, executa e retorna resultado
        6. Repete ate o LLM dar uma resposta final

        Args:
            user_input: Mensagem do usuario

        Returns:
            Resposta final do agente
        """
        # Step 1: Adiciona mensagem na working memory
        self.memory.add_message("user", user_input)

        # Step 2: Recupera contexto da memoria
        memory_context = await self.memory.get_context_for_prompt(user_input)
        pending_tasks = await self.memory.get_pending_tasks_summary()

        # Step 3: Constroi system prompt
        system_prompt = self.identity.build_system_prompt(
            memory_context=memory_context,
            active_tools=self.tools.list_names(),
            pending_tasks=pending_tasks if pending_tasks else None,
        )

        # Step 4: Loop ReAct - envia ao LLM e processa tool calls
        tool_classes = self.tools.list_tools()
        iterations = 0

        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1

            # Envia mensagens para o LLM
            messages = self.memory.get_messages()
            response = await self.llm.chat(
                messages=messages,
                system=system_prompt,
                tools=tool_classes if tool_classes else None,
            )

            # Se o LLM retornou texto sem tool calls, temos a resposta final
            if response.is_end_turn or not response.has_tool_calls:
                if response.text:
                    self.memory.add_message("assistant", response.text)
                break

            # Step 5: Processar tool calls
            # Primeiro, adiciona a resposta do assistant (com text + tool_use)
            assistant_content = self._build_assistant_content(response)
            self.memory.add_message("assistant", assistant_content)

            # Executa cada tool call
            tool_results = []
            for tool_call in response.tool_calls:
                logger.info(
                    f"Tool call: {tool_call.name}({json.dumps(tool_call.arguments, ensure_ascii=False)[:200]})"
                )

                result = await self.tools.execute(
                    tool_call.name, tool_call.arguments
                )

                tool_results.append(
                    self.llm.format_tool_result(
                        tool_call_id=tool_call.id,
                        result=result,
                        is_error="Erro" in result[:50] if result else False,
                    )
                )

            # Adiciona resultados das tools na working memory
            self.memory.add_message("user", tool_results)

        # Step 6: Verifica se precisa consolidar a working memory
        if await self.memory.should_consolidate():
            await self._consolidate_memory()

        return response.text if response.text else "Desculpe, nao consegui gerar uma resposta."

    def _build_assistant_content(self, response: LLMResponse) -> list[dict]:
        """
        Constroi o content do assistant message no formato da API.
        Inclui texto e tool_use blocks.
        """
        content = []

        if response.text:
            content.append({"type": "text", "text": response.text})

        for tc in response.tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                }
            )

        return content

    async def _consolidate_memory(self) -> None:
        """
        Consolida a working memory pedindo ao LLM para sumarizar.
        """
        conversation_text = self.memory.working.get_conversation_text()

        try:
            summary_response = await self.llm.chat(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Resuma esta conversa em 3-5 frases, preservando "
                            "informacoes importantes como: sites mencionados, "
                            "acoes executadas, decisoes tomadas, preferencias "
                            "do usuario, e tarefas pendentes.\n\n"
                            f"Conversa:\n{conversation_text}"
                        ),
                    }
                ],
                system="Voce e um sumarizador. Crie resumos concisos e informativos.",
                max_tokens=500,
            )

            if summary_response.text:
                await self.memory.consolidate(summary_response.text)
                logger.info("Working memory consolidada com sucesso")

        except Exception as e:
            logger.error(f"Falha na consolidacao da memoria: {e}")

    async def get_greeting(self) -> str:
        """
        Retorna a saudacao do agente, enriquecida com contexto.

        Se o agente ja conhece o usuario (tem fatos salvos),
        personaliza a saudacao.
        """
        greeting = self.identity.greeting

        # Verifica se tem contexto do usuario
        try:
            facts = await self.memory.list_facts()
            tasks = await self.memory.list_tasks()

            if facts or tasks:
                greeting += "\n\nVejo que ja temos historico juntos!"
                if tasks:
                    greeting += f"\nVoce tem {len(tasks)} tarefa(s) pendente(s)."
        except Exception:
            pass  # Nao falha se a memoria nao estiver disponivel

        return greeting

    async def on_shutdown(self) -> None:
        """Chamado quando o agente esta sendo encerrado."""
        # Salva resumo da sessao
        if self.memory.working.get_message_count() > 2:
            try:
                conversation_text = self.memory.working.get_conversation_text()
                summary_response = await self.llm.chat(
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Resuma esta sessao de conversa em 2-3 frases "
                                "para referencia futura:\n\n"
                                f"{conversation_text[:3000]}"
                            ),
                        }
                    ],
                    system="Crie um resumo conciso da conversa.",
                    max_tokens=300,
                )

                if summary_response.text:
                    await self.memory.on_session_end(summary_response.text)

            except Exception as e:
                logger.error(f"Erro ao salvar resumo da sessao: {e}")

        self.memory.close()
        logger.info("AgentCore encerrado")
