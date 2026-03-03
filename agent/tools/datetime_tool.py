"""
Tool de data/hora para o agente Aurora.

Fornece acesso ao horario atual e calculos de datas.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from agent.tools.base import BaseTool


class DateTimeParams(BaseModel):
    """Parametros para consultas de data/hora."""

    action: str = Field(
        description=(
            "Acao a executar. Opcoes: "
            "'now' (data e hora atuais), "
            "'add_days' (adicionar dias a data atual), "
            "'format' (formatar data em diferentes formatos)"
        )
    )
    days: int = Field(
        default=0,
        description="Numero de dias a adicionar (negativo para subtrair). Usado com action='add_days'.",
    )
    date_string: str = Field(
        default="",
        description="String de data no formato YYYY-MM-DD. Usado com action='format'.",
    )


class DateTimeTool(BaseTool):
    """Fornece informacoes de data e hora."""

    name = "datetime"
    description = (
        "Fornece a data e hora atuais, permite calcular datas futuras/passadas, "
        "e formatar datas. Util para definir periodos de relatorios, "
        "agendar tarefas e calcular intervalos de tempo."
    )
    parameters = DateTimeParams

    async def execute(self, params: DateTimeParams) -> str:
        now = datetime.now()

        if params.action == "now":
            result = {
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "formatted_br": now.strftime("%d/%m/%Y %H:%M"),
            }

        elif params.action == "add_days":
            target = now + timedelta(days=params.days)
            result = {
                "original": now.strftime("%Y-%m-%d"),
                "days_added": params.days,
                "result": target.strftime("%Y-%m-%d"),
                "result_formatted_br": target.strftime("%d/%m/%Y"),
            }

        elif params.action == "format":
            try:
                dt = datetime.strptime(params.date_string, "%Y-%m-%d")
                result = {
                    "iso": dt.isoformat(),
                    "br": dt.strftime("%d/%m/%Y"),
                    "us": dt.strftime("%m/%d/%Y"),
                    "long_br": dt.strftime("%d de %B de %Y"),
                    "day_of_week": dt.strftime("%A"),
                }
            except ValueError:
                result = {"error": f"Formato de data invalido: {params.date_string}. Use YYYY-MM-DD."}

        else:
            result = {"error": f"Acao desconhecida: {params.action}"}

        return json.dumps(result, ensure_ascii=False, indent=2)
