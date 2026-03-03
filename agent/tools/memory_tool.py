"""
Tool de memoria para o agente Aurora.

Permite que o agente salve e recupere informacoes na memoria
de longo prazo durante a conversa. O agente pode usar esta tool
para lembrar fatos sobre o usuario, sites, e tarefas.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools.memory")


class MemoryParams(BaseModel):
    """Parametros para operacoes de memoria."""

    action: str = Field(
        description=(
            "Acao a executar. Opcoes: "
            "'save_fact' (salvar fato sobre o usuario ou site), "
            "'search' (buscar memorias por termo), "
            "'list_facts' (listar fatos salvos), "
            "'save_task' (salvar tarefa pendente), "
            "'list_tasks' (listar tarefas pendentes), "
            "'complete_task' (marcar tarefa como concluida)"
        )
    )
    content: str = Field(
        default="",
        description="Conteudo a salvar ou termo de busca",
    )
    category: str = Field(
        default="general",
        description="Categoria do fato: 'user_preference', 'site_data', 'task', 'general'",
    )
    task_id: int = Field(
        default=0,
        description="ID da tarefa (para complete_task)",
    )


class MemoryTool(BaseTool):
    """Gerencia a memoria de longo prazo do agente."""

    name = "memory"
    description = (
        "Gerencia a memoria persistente do agente. Permite salvar e buscar "
        "fatos sobre o usuario, dados de sites auditados, tarefas pendentes "
        "e preferencias. Use para lembrar informacoes importantes entre sessoes. "
        "Exemplos: salvar que o usuario prefere conteudo em pt-BR, "
        "lembrar o score SEO de um site, ou registrar tarefas de follow-up."
    )
    parameters = MemoryParams

    # Referencia ao memory manager sera injetada pelo core
    _memory_manager = None

    @classmethod
    def set_memory_manager(cls, manager) -> None:
        """Injeta o memory manager. Chamado pelo core na inicializacao."""
        cls._memory_manager = manager

    async def execute(self, params: MemoryParams) -> str:
        if self._memory_manager is None:
            return json.dumps(
                {"error": "Sistema de memoria nao inicializado."},
                ensure_ascii=False,
            )

        try:
            if params.action == "save_fact":
                if not params.content:
                    return json.dumps({"error": "Conteudo e obrigatorio para save_fact"})

                await self._memory_manager.save_fact(
                    content=params.content,
                    category=params.category,
                )
                return json.dumps(
                    {
                        "status": "saved",
                        "content": params.content,
                        "category": params.category,
                    },
                    ensure_ascii=False,
                )

            elif params.action == "search":
                if not params.content:
                    return json.dumps({"error": "Termo de busca e obrigatorio"})

                results = await self._memory_manager.search(params.content)
                return json.dumps(
                    {"results": results, "count": len(results)},
                    ensure_ascii=False,
                    indent=2,
                )

            elif params.action == "list_facts":
                facts = await self._memory_manager.list_facts(
                    category=params.category if params.category != "general" else None
                )
                return json.dumps(
                    {"facts": facts, "count": len(facts)},
                    ensure_ascii=False,
                    indent=2,
                )

            elif params.action == "save_task":
                if not params.content:
                    return json.dumps({"error": "Descricao da tarefa e obrigatoria"})

                task_id = await self._memory_manager.save_task(params.content)
                return json.dumps(
                    {"status": "task_saved", "task_id": task_id, "description": params.content},
                    ensure_ascii=False,
                )

            elif params.action == "list_tasks":
                tasks = await self._memory_manager.list_tasks()
                return json.dumps(
                    {"tasks": tasks, "count": len(tasks)},
                    ensure_ascii=False,
                    indent=2,
                )

            elif params.action == "complete_task":
                if not params.task_id:
                    return json.dumps({"error": "task_id e obrigatorio"})

                await self._memory_manager.complete_task(params.task_id)
                return json.dumps(
                    {"status": "completed", "task_id": params.task_id},
                    ensure_ascii=False,
                )

            else:
                return json.dumps(
                    {"error": f"Acao desconhecida: {params.action}"},
                    ensure_ascii=False,
                )

        except Exception as e:
            return json.dumps(
                {"error": f"Erro na memoria: {str(e)}"},
                ensure_ascii=False,
            )
