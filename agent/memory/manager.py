"""
Memory Manager - orquestra working memory + long-term memory.

Responsavel por:
- Coordenar as duas camadas de memoria
- Recuperar contexto relevante antes de cada chamada ao LLM
- Consolidar working memory quando necessario
- Interface unificada para o core do agente
"""

from __future__ import annotations

import logging
from typing import Optional

from agent.memory.working import WorkingMemory
from agent.memory.long_term import LongTermMemory

logger = logging.getLogger("aurora.memory.manager")


class MemoryManager:
    """
    Orquestra working memory e long-term memory.

    Fornece uma interface unificada para o core do agente
    gerenciar todo o sistema de memoria.
    """

    def __init__(
        self,
        db_path: str,
        max_working_messages: int = 50,
        max_context_tokens: int = 100000,
        consolidation_threshold: int = 30,
    ) -> None:
        self.working = WorkingMemory(
            max_messages=max_working_messages,
            max_tokens=max_context_tokens,
        )
        self.long_term = LongTermMemory(db_path=db_path)
        self._consolidation_threshold = consolidation_threshold

        logger.info("MemoryManager inicializado")

    # --- Delegacao para working memory ---

    def add_message(self, role: str, content) -> None:
        """Adiciona mensagem na working memory."""
        self.working.add(role, content)

    def get_messages(self) -> list[dict]:
        """Retorna mensagens da working memory."""
        return self.working.get_messages()

    def get_last_user_message(self) -> str | None:
        """Retorna ultima mensagem do usuario."""
        return self.working.get_last_user_message()

    # --- Delegacao para long-term memory ---

    async def save_fact(self, content: str, category: str = "general") -> int:
        """Salva fato na memoria de longo prazo."""
        return await self.long_term.save_fact(content, category)

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Busca na memoria de longo prazo."""
        return await self.long_term.search_facts(query, limit)

    async def list_facts(self, category: Optional[str] = None) -> list[dict]:
        """Lista fatos salvos."""
        return await self.long_term.list_facts(category)

    async def save_task(self, description: str) -> int:
        """Salva tarefa pendente."""
        return await self.long_term.save_task(description)

    async def list_tasks(self) -> list[dict]:
        """Lista tarefas pendentes."""
        return await self.long_term.list_tasks()

    async def complete_task(self, task_id: int) -> None:
        """Marca tarefa como concluida."""
        await self.long_term.complete_task(task_id)

    # --- Contexto para o LLM ---

    async def get_context_for_prompt(self, current_input: str = "") -> str:
        """
        Recupera contexto relevante da memoria para injetar no system prompt.

        Combina:
        1. Fatos relevantes ao input atual
        2. Tarefas pendentes
        3. Resumos de conversas recentes
        """
        return await self.long_term.get_relevant_context(
            query=current_input, limit=10
        )

    async def get_pending_tasks_summary(self) -> list[str]:
        """Retorna lista de descricoes de tarefas pendentes."""
        tasks = await self.long_term.list_tasks("pending")
        return [t["description"] for t in tasks]

    # --- Consolidacao ---

    async def should_consolidate(self) -> bool:
        """Verifica se a working memory precisa de consolidacao."""
        return self.working.get_message_count() >= self._consolidation_threshold

    async def consolidate(self, summary: str) -> None:
        """
        Consolida a working memory: salva resumo no long-term
        e limpa mensagens antigas da working memory.

        O resumo deve ser gerado pelo LLM (o core chama isso apos
        pedir ao LLM para sumarizar a conversa).
        """
        # Salva resumo da conversa no long-term
        message_count = self.working.get_message_count()
        await self.long_term.save_conversation_summary(
            summary=summary,
            topics=[],  # Poderia ser extraido pelo LLM
            message_count=message_count,
        )

        # Limpa working memory e define o resumo como contexto
        self.working.clear()
        self.working.set_summary(summary)

        logger.info(
            f"Working memory consolidada: {message_count} mensagens -> resumo"
        )

    # --- Lifecycle ---

    async def on_session_end(self, conversation_summary: str = "") -> None:
        """
        Chamado quando a sessao termina.
        Salva o resumo da conversa se houver.
        """
        if conversation_summary and self.working.get_message_count() > 0:
            await self.long_term.save_conversation_summary(
                summary=conversation_summary,
                topics=[],
                message_count=self.working.get_message_count(),
            )
            logger.info("Resumo da sessao salvo na memoria de longo prazo")

        self.working.clear()

    def close(self) -> None:
        """Fecha recursos."""
        self.long_term.close()
