"""
Planner - planejamento e execucao de tarefas multi-step.

O planner permite que o agente decomponha tarefas complexas em
passos menores e os execute sequencialmente, mantendo estado
entre cada passo.

Exemplo de uso: "Audite meu site e gere conteudo para as 3 paginas
com pior score" -> O planner cria um plano com passos:
1. Executar auditoria SEO
2. Identificar 3 paginas com pior score
3. Gerar conteudo otimizado para cada pagina
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("aurora.planner")


class StepStatus(str, Enum):
    """Status de um passo do plano."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """Um passo individual do plano."""

    index: int
    description: str
    tool_name: Optional[str] = None
    tool_params: Optional[dict] = None
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "step": self.index + 1,
            "description": self.description,
            "tool": self.tool_name,
            "status": self.status.value,
            "result_preview": self.result[:200] if self.result else None,
            "error": self.error,
        }


@dataclass
class Plan:
    """Um plano de execucao com multiplos passos."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def current_step(self) -> Optional[PlanStep]:
        """Retorna o proximo passo pendente."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None

    @property
    def is_complete(self) -> bool:
        """Verifica se todos os passos foram executados."""
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED)
            for s in self.steps
        )

    @property
    def progress_text(self) -> str:
        """Texto de progresso do plano."""
        completed = sum(
            1 for s in self.steps
            if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        )
        return f"{completed}/{len(self.steps)} passos concluidos"

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "progress": self.progress_text,
            "steps": [s.to_dict() for s in self.steps],
        }

    def get_results_context(self) -> str:
        """Retorna os resultados dos passos concluidos como contexto."""
        context_parts = []
        for step in self.steps:
            if step.status == StepStatus.COMPLETED and step.result:
                context_parts.append(
                    f"### Passo {step.index + 1}: {step.description}\n"
                    f"Resultado: {step.result[:500]}"
                )
        return "\n\n".join(context_parts)


class Planner:
    """
    Gerencia planos de execucao multi-step.

    O planner trabalha em conjunto com o core do agente:
    1. O agente identifica que precisa de um plano
    2. O LLM gera o plano (lista de passos)
    3. O planner rastreia a execucao de cada passo
    4. O agente executa cada passo usando as tools

    Nota: o planner NAO executa passos automaticamente.
    Ele apenas gerencia o estado do plano. O core do agente
    e responsavel pela execucao real.
    """

    def __init__(self) -> None:
        self._active_plan: Optional[Plan] = None
        self._history: list[Plan] = []

    @property
    def has_active_plan(self) -> bool:
        return self._active_plan is not None and not self._active_plan.is_complete

    @property
    def active_plan(self) -> Optional[Plan]:
        return self._active_plan

    def create_plan(self, goal: str, steps: list[dict]) -> Plan:
        """
        Cria um novo plano de execucao.

        Args:
            goal: Objetivo geral do plano
            steps: Lista de dicts com 'description', 'tool_name' (opcional),
                   'tool_params' (opcional)

        Returns:
            O plano criado
        """
        plan_steps = [
            PlanStep(
                index=i,
                description=s.get("description", f"Passo {i + 1}"),
                tool_name=s.get("tool_name"),
                tool_params=s.get("tool_params"),
            )
            for i, s in enumerate(steps)
        ]

        # Arquiva plano anterior se existir
        if self._active_plan:
            self._history.append(self._active_plan)

        self._active_plan = Plan(goal=goal, steps=plan_steps)
        logger.info(
            f"Plano criado: '{goal}' com {len(plan_steps)} passos"
        )

        return self._active_plan

    def start_step(self, step_index: Optional[int] = None) -> Optional[PlanStep]:
        """Marca um passo como em andamento."""
        if not self._active_plan:
            return None

        step = (
            self._active_plan.steps[step_index]
            if step_index is not None
            else self._active_plan.current_step
        )

        if step and step.status == StepStatus.PENDING:
            step.status = StepStatus.IN_PROGRESS
            step.started_at = datetime.now()
            logger.info(f"Passo iniciado: {step.description}")
            return step

        return None

    def complete_step(
        self, step_index: int, result: str
    ) -> None:
        """Marca um passo como concluido com resultado."""
        if not self._active_plan:
            return

        step = self._active_plan.steps[step_index]
        step.status = StepStatus.COMPLETED
        step.result = result
        step.completed_at = datetime.now()

        logger.info(f"Passo concluido: {step.description}")

        # Verifica se o plano todo foi concluido
        if self._active_plan.is_complete:
            self._active_plan.completed_at = datetime.now()
            logger.info(f"Plano concluido: {self._active_plan.goal}")

    def fail_step(self, step_index: int, error: str) -> None:
        """Marca um passo como falhado."""
        if not self._active_plan:
            return

        step = self._active_plan.steps[step_index]
        step.status = StepStatus.FAILED
        step.error = error
        step.completed_at = datetime.now()

        logger.warning(f"Passo falhou: {step.description} - {error}")

    def cancel_plan(self) -> None:
        """Cancela o plano ativo."""
        if self._active_plan:
            self._history.append(self._active_plan)
            logger.info(f"Plano cancelado: {self._active_plan.goal}")
            self._active_plan = None

    def get_plan_status(self) -> str:
        """Retorna status do plano ativo em formato legivel."""
        if not self._active_plan:
            return "Nenhum plano ativo."

        plan = self._active_plan
        return json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
