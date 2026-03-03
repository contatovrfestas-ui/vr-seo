"""
Tool de integracao com Google Search Console para o agente Aurora.

Porta da integracao Node.js com googleapis, adaptada para Python.
Requer autenticacao OAuth2 previa.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools.gsc")


class SearchConsoleParams(BaseModel):
    """Parametros para consultas ao Google Search Console."""

    action: str = Field(
        description=(
            "Acao a executar. Opcoes: "
            "'list_sites' (listar sites verificados), "
            "'top_queries' (queries com mais cliques), "
            "'top_pages' (paginas com mais cliques), "
            "'search_analytics' (relatorio personalizado)"
        )
    )
    site_url: str = Field(
        default="",
        description="URL do site no Search Console (ex: https://example.com/)",
    )
    start_date: str = Field(
        default="",
        description="Data inicial no formato YYYY-MM-DD (padrao: 28 dias atras)",
    )
    end_date: str = Field(
        default="",
        description="Data final no formato YYYY-MM-DD (padrao: hoje)",
    )
    limit: int = Field(
        default=20,
        description="Numero maximo de resultados a retornar",
    )


class GoogleSearchConsoleTool(BaseTool):
    """Consulta dados do Google Search Console."""

    name = "google_search_console"
    description = (
        "Acessa dados do Google Search Console para analisar performance de busca. "
        "Pode listar sites verificados, obter top queries (palavras-chave), "
        "top paginas, e relatorios de search analytics com metricas como "
        "cliques, impressoes, CTR e posicao media. "
        "Requer que o usuario tenha feito login Google previamente."
    )
    parameters = SearchConsoleParams

    async def execute(self, params: SearchConsoleParams) -> str:
        try:
            from googleapiclient.discovery import build

            auth_client = self._get_auth_client()
            service = build("searchconsole", "v1", credentials=auth_client)

            if params.action == "list_sites":
                return await self._list_sites(service)
            elif params.action == "top_queries":
                return await self._top_queries(service, params)
            elif params.action == "top_pages":
                return await self._top_pages(service, params)
            elif params.action == "search_analytics":
                return await self._search_analytics(service, params)
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
                {"error": f"Erro no Search Console: {str(e)}"},
                ensure_ascii=False,
            )

    def _get_auth_client(self):
        """Obtem cliente autenticado do Google."""
        import os
        from pathlib import Path
        from google.oauth2.credentials import Credentials

        # Busca tokens no diretorio padrao
        token_path = Path.home() / ".vr-seo" / "google-tokens.json"
        if not token_path.exists():
            raise FileNotFoundError("Token Google nao encontrado")

        creds = Credentials.from_authorized_user_file(str(token_path))
        return creds

    async def _list_sites(self, service) -> str:
        """Lista sites verificados no Search Console."""
        response = service.sites().list().execute()
        sites = response.get("siteEntry", [])

        result = {
            "action": "list_sites",
            "sites": [
                {
                    "url": s.get("siteUrl", ""),
                    "permission": s.get("permissionLevel", ""),
                }
                for s in sites
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    async def _top_queries(self, service, params: SearchConsoleParams) -> str:
        """Obtem top queries por cliques."""
        if not params.site_url:
            return json.dumps(
                {"error": "site_url e obrigatorio para top_queries"},
                ensure_ascii=False,
            )

        start, end = self._get_date_range(params)

        response = (
            service.searchanalytics()
            .query(
                siteUrl=params.site_url,
                body={
                    "startDate": start,
                    "endDate": end,
                    "dimensions": ["query"],
                    "rowLimit": params.limit,
                },
            )
            .execute()
        )

        rows = response.get("rows", [])
        result = {
            "action": "top_queries",
            "site": params.site_url,
            "period": f"{start} a {end}",
            "queries": [
                {
                    "query": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 0), 1),
                }
                for row in rows
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    async def _top_pages(self, service, params: SearchConsoleParams) -> str:
        """Obtem top paginas por cliques."""
        if not params.site_url:
            return json.dumps(
                {"error": "site_url e obrigatorio para top_pages"},
                ensure_ascii=False,
            )

        start, end = self._get_date_range(params)

        response = (
            service.searchanalytics()
            .query(
                siteUrl=params.site_url,
                body={
                    "startDate": start,
                    "endDate": end,
                    "dimensions": ["page"],
                    "rowLimit": params.limit,
                },
            )
            .execute()
        )

        rows = response.get("rows", [])
        result = {
            "action": "top_pages",
            "site": params.site_url,
            "period": f"{start} a {end}",
            "pages": [
                {
                    "page": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 0), 1),
                }
                for row in rows
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    async def _search_analytics(
        self, service, params: SearchConsoleParams
    ) -> str:
        """Relatorio de search analytics personalizado."""
        if not params.site_url:
            return json.dumps(
                {"error": "site_url e obrigatorio"},
                ensure_ascii=False,
            )

        start, end = self._get_date_range(params)

        response = (
            service.searchanalytics()
            .query(
                siteUrl=params.site_url,
                body={
                    "startDate": start,
                    "endDate": end,
                    "dimensions": ["query", "page"],
                    "rowLimit": params.limit,
                },
            )
            .execute()
        )

        rows = response.get("rows", [])
        result = {
            "action": "search_analytics",
            "site": params.site_url,
            "period": f"{start} a {end}",
            "data": [
                {
                    "query": row["keys"][0],
                    "page": row["keys"][1],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 0), 1),
                }
                for row in rows
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    @staticmethod
    def _get_date_range(params: SearchConsoleParams) -> tuple[str, str]:
        """Calcula o range de datas."""
        end = params.end_date or datetime.now().strftime("%Y-%m-%d")
        start = params.start_date or (
            datetime.now() - timedelta(days=28)
        ).strftime("%Y-%m-%d")
        return start, end
