"""
Tool de integracao com Google Analytics (GA4) para o agente Aurora.

Porta da integracao Node.js com Analytics Data API v1beta.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools.ga4")


class AnalyticsParams(BaseModel):
    """Parametros para consultas ao Google Analytics."""

    action: str = Field(
        description=(
            "Acao a executar. Opcoes: "
            "'top_pages' (paginas mais visitadas), "
            "'traffic_sources' (fontes de trafego), "
            "'organic_traffic' (trafego organico), "
            "'report' (relatorio personalizado)"
        )
    )
    property_id: str = Field(
        description="ID da propriedade GA4 (apenas o numero, ex: '123456789')"
    )
    start_date: str = Field(
        default="28daysAgo",
        description="Data inicial (formato YYYY-MM-DD ou '28daysAgo', '7daysAgo')",
    )
    end_date: str = Field(
        default="today",
        description="Data final (formato YYYY-MM-DD ou 'today', 'yesterday')",
    )
    limit: int = Field(
        default=20,
        description="Numero maximo de resultados",
    )


class GoogleAnalyticsTool(BaseTool):
    """Consulta dados do Google Analytics (GA4)."""

    name = "google_analytics"
    description = (
        "Acessa dados do Google Analytics 4 para analisar trafego e comportamento. "
        "Pode obter top paginas, fontes de trafego, trafego organico, e "
        "relatorios com metricas como pageviews, sessoes, bounce rate, e "
        "duracao media da sessao. "
        "Requer que o usuario tenha feito login Google previamente."
    )
    parameters = AnalyticsParams

    async def execute(self, params: AnalyticsParams) -> str:
        try:
            from googleapiclient.discovery import build

            auth_client = self._get_auth_client()
            service = build("analyticsdata", "v1beta", credentials=auth_client)

            if params.action == "top_pages":
                return await self._top_pages(service, params)
            elif params.action == "traffic_sources":
                return await self._traffic_sources(service, params)
            elif params.action == "organic_traffic":
                return await self._organic_traffic(service, params)
            elif params.action == "report":
                return await self._custom_report(service, params)
            else:
                return json.dumps(
                    {"error": f"Acao desconhecida: {params.action}"},
                    ensure_ascii=False,
                )

        except ImportError:
            return json.dumps(
                {
                    "error": "google-api-python-client nao instalado. Execute: pip install google-api-python-client google-auth-oauthlib"
                },
                ensure_ascii=False,
            )
        except FileNotFoundError:
            return json.dumps(
                {
                    "error": "Nao autenticado com Google. O usuario precisa configurar a autenticacao OAuth2 primeiro."
                },
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps(
                {"error": f"Erro no Analytics: {str(e)}"},
                ensure_ascii=False,
            )

    def _get_auth_client(self):
        """Obtem cliente autenticado do Google."""
        from pathlib import Path
        from google.oauth2.credentials import Credentials

        token_path = Path.home() / ".vr-seo" / "google-tokens.json"
        if not token_path.exists():
            raise FileNotFoundError("Token Google nao encontrado")

        return Credentials.from_authorized_user_file(str(token_path))

    async def _run_report(self, service, params: AnalyticsParams, dimensions, metrics) -> dict:
        """Executa um relatorio generico no GA4."""
        request = {
            "dateRanges": [
                {"startDate": params.start_date, "endDate": params.end_date}
            ],
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"name": m} for m in metrics],
            "limit": str(params.limit),
        }

        response = (
            service.properties()
            .runReport(
                property=f"properties/{params.property_id}",
                body=request,
            )
            .execute()
        )

        # Parse response
        dim_headers = [h.get("name") for h in response.get("dimensionHeaders", [])]
        met_headers = [h.get("name") for h in response.get("metricHeaders", [])]

        rows = []
        for row in response.get("rows", []):
            obj = {}
            for i, val in enumerate(row.get("dimensionValues", [])):
                obj[dim_headers[i]] = val.get("value", "")
            for i, val in enumerate(row.get("metricValues", [])):
                try:
                    obj[met_headers[i]] = float(val.get("value", "0"))
                except ValueError:
                    obj[met_headers[i]] = val.get("value", "")
            rows.append(obj)

        return {"rows": rows, "row_count": response.get("rowCount", 0)}

    async def _top_pages(self, service, params: AnalyticsParams) -> str:
        """Paginas mais visitadas."""
        data = await self._run_report(
            service,
            params,
            dimensions=["pagePath"],
            metrics=["screenPageViews", "sessions", "bounceRate"],
        )

        return json.dumps(
            {
                "action": "top_pages",
                "property": params.property_id,
                "period": f"{params.start_date} a {params.end_date}",
                "pages": data["rows"],
            },
            ensure_ascii=False,
            indent=2,
        )

    async def _traffic_sources(self, service, params: AnalyticsParams) -> str:
        """Fontes de trafego."""
        data = await self._run_report(
            service,
            params,
            dimensions=["sessionSource", "sessionMedium"],
            metrics=["sessions", "screenPageViews"],
        )

        return json.dumps(
            {
                "action": "traffic_sources",
                "property": params.property_id,
                "period": f"{params.start_date} a {params.end_date}",
                "sources": data["rows"],
            },
            ensure_ascii=False,
            indent=2,
        )

    async def _organic_traffic(self, service, params: AnalyticsParams) -> str:
        """Trafego organico."""
        request = {
            "dateRanges": [
                {"startDate": params.start_date, "endDate": params.end_date}
            ],
            "dimensions": [{"name": "landingPage"}, {"name": "sessionSource"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "screenPageViews"},
                {"name": "bounceRate"},
            ],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "sessionMedium",
                    "stringFilter": {"value": "organic"},
                }
            },
            "limit": str(params.limit),
        }

        response = (
            service.properties()
            .runReport(
                property=f"properties/{params.property_id}",
                body=request,
            )
            .execute()
        )

        dim_headers = [h.get("name") for h in response.get("dimensionHeaders", [])]
        met_headers = [h.get("name") for h in response.get("metricHeaders", [])]

        rows = []
        for row in response.get("rows", []):
            obj = {}
            for i, val in enumerate(row.get("dimensionValues", [])):
                obj[dim_headers[i]] = val.get("value", "")
            for i, val in enumerate(row.get("metricValues", [])):
                try:
                    obj[met_headers[i]] = float(val.get("value", "0"))
                except ValueError:
                    obj[met_headers[i]] = val.get("value", "")
            rows.append(obj)

        return json.dumps(
            {
                "action": "organic_traffic",
                "property": params.property_id,
                "period": f"{params.start_date} a {params.end_date}",
                "organic_data": rows,
            },
            ensure_ascii=False,
            indent=2,
        )

    async def _custom_report(self, service, params: AnalyticsParams) -> str:
        """Relatorio personalizado com metricas gerais."""
        data = await self._run_report(
            service,
            params,
            dimensions=["pagePath"],
            metrics=[
                "screenPageViews",
                "sessions",
                "bounceRate",
                "averageSessionDuration",
            ],
        )

        return json.dumps(
            {
                "action": "report",
                "property": params.property_id,
                "period": f"{params.start_date} a {params.end_date}",
                "data": data["rows"],
                "total_rows": data["row_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
