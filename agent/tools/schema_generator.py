"""
Tool de geracao de Schema markup (JSON-LD) para o agente Aurora.

Analisa uma pagina web e fornece contexto para gerar Schema markup
otimizado.
"""

from __future__ import annotations

import json
import logging

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools.schema")

VALID_SCHEMA_TYPES = [
    "Organization",
    "Article",
    "FAQ",
    "Product",
    "LocalBusiness",
    "WebSite",
    "BreadcrumbList",
    "HowTo",
    "Review",
    "Event",
]


class SchemaParams(BaseModel):
    """Parametros para geracao de Schema markup."""

    url: str = Field(description="URL da pagina para gerar o Schema")
    schema_type: str = Field(
        description=(
            "Tipo de Schema a gerar. Opcoes: "
            + ", ".join(VALID_SCHEMA_TYPES)
        )
    )
    language: str = Field(
        default="pt-BR",
        description="Idioma do conteudo",
    )


class SchemaGeneratorTool(BaseTool):
    """Analisa pagina e fornece contexto para geracao de Schema JSON-LD."""

    name = "schema_generator"
    description = (
        "Analisa uma pagina web e extrai informacoes relevantes para gerar "
        "Schema markup JSON-LD otimizado. Suporta tipos: Organization, Article, "
        "FAQ, Product, LocalBusiness, WebSite, BreadcrumbList, HowTo, Review, Event. "
        "Retorna dados extraidos da pagina para que voce gere o markup final."
    )
    parameters = SchemaParams

    async def execute(self, params: SchemaParams) -> str:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "VR-SEO-Aurora/2.0"},
                timeout=10.0,
                follow_redirects=True,
                verify=False,
            ) as client:
                response = await client.get(params.url)

            soup = BeautifulSoup(response.text, "lxml")

            # Extract page data
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            h1 = soup.find("h1")
            h1_text = h1.get_text(strip=True) if h1 else ""

            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc.get("content", "") if meta_desc else ""

            # Body text
            body = soup.find("body")
            body_text = body.get_text(" ", strip=True)[:2000] if body else ""

            # Existing schemas
            existing_schemas = []
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    existing_schemas.append(json.loads(script.string))
                except (json.JSONDecodeError, TypeError):
                    pass

            # Images
            images = []
            for img in soup.find_all("img", src=True)[:5]:
                images.append(
                    {"src": img["src"], "alt": img.get("alt", "")}
                )

            result = {
                "url": params.url,
                "schema_type_requested": params.schema_type,
                "page_data": {
                    "title": title,
                    "h1": h1_text,
                    "meta_description": description,
                    "content_preview": body_text[:500],
                    "images": images,
                },
                "existing_schemas": existing_schemas,
                "instructions": (
                    f"Gere um Schema markup JSON-LD do tipo '{params.schema_type}' "
                    f"para esta pagina. Use os dados extraidos acima como base. "
                    f"Siga as diretrizes do Google para structured data. "
                    f"Inclua todas as propriedades obrigatorias e recomendadas. "
                    f"Idioma: {params.language}."
                ),
            }

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps(
                {"error": f"Erro ao analisar {params.url}: {str(e)}"},
                ensure_ascii=False,
            )
