"""
Tool de analise e geracao de meta tags para o agente Aurora.

Busca uma URL, extrai o conteudo da pagina, e analisa/sugere
meta tags otimizadas.
"""

from __future__ import annotations

import json
import logging

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools.metatags")


class MetaTagsParams(BaseModel):
    """Parametros para analise de meta tags."""

    url: str = Field(description="URL da pagina para analisar/gerar meta tags")
    language: str = Field(
        default="pt-BR",
        description="Idioma das meta tags sugeridas",
    )


class MetaTagsAnalyzerTool(BaseTool):
    """Analisa meta tags atuais de uma pagina e sugere melhorias."""

    name = "meta_tags_analyzer"
    description = (
        "Analisa as meta tags atuais de uma pagina web e extrai informacoes "
        "sobre title, description, Open Graph, Twitter Cards, canonical, "
        "e outros elementos. Retorna os dados atuais e identifica problemas "
        "para que voce possa sugerir meta tags otimizadas."
    )
    parameters = MetaTagsParams

    async def execute(self, params: MetaTagsParams) -> str:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "VR-SEO-Aurora/2.0"},
                timeout=10.0,
                follow_redirects=True,
                verify=False,
            ) as client:
                response = await client.get(params.url)

            soup = BeautifulSoup(response.text, "lxml")

            # Extract current meta tags
            current = {
                "title": "",
                "meta_description": "",
                "canonical": "",
                "open_graph": {},
                "twitter": {},
                "other_meta": [],
                "headings": {"h1": [], "h2": []},
                "word_count": 0,
                "issues": [],
            }

            # Title
            title_tag = soup.find("title")
            current["title"] = title_tag.get_text(strip=True) if title_tag else ""

            # Meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            current["meta_description"] = (
                meta_desc.get("content", "") if meta_desc else ""
            )

            # Canonical
            canonical = soup.find("link", rel="canonical")
            current["canonical"] = canonical.get("href", "") if canonical else ""

            # Open Graph
            og_tags = soup.find_all("meta", property=True)
            for tag in og_tags:
                prop = tag.get("property", "")
                if prop.startswith("og:"):
                    current["open_graph"][prop] = tag.get("content", "")

            # Twitter Cards
            twitter_tags = soup.find_all("meta", attrs={"name": True})
            for tag in twitter_tags:
                name = tag.get("name", "")
                if name.startswith("twitter:"):
                    current["twitter"][name] = tag.get("content", "")

            # Headings
            for h1 in soup.find_all("h1"):
                current["headings"]["h1"].append(h1.get_text(strip=True))
            for h2 in soup.find_all("h2"):
                current["headings"]["h2"].append(h2.get_text(strip=True))

            # Word count
            body = soup.find("body")
            if body:
                text = body.get_text(" ", strip=True)
                current["word_count"] = len(text.split())
                # Content preview for context
                current["content_preview"] = text[:1000]

            # Identify issues
            if not current["title"]:
                current["issues"].append("Title tag ausente")
            elif len(current["title"]) > 60:
                current["issues"].append(
                    f"Title muito longo ({len(current['title'])} chars)"
                )

            if not current["meta_description"]:
                current["issues"].append("Meta description ausente")
            elif len(current["meta_description"]) > 160:
                current["issues"].append(
                    f"Meta description muito longa ({len(current['meta_description'])} chars)"
                )

            if not current["open_graph"]:
                current["issues"].append("Open Graph tags ausentes")

            if not current["twitter"]:
                current["issues"].append("Twitter Card tags ausentes")

            if not current["canonical"]:
                current["issues"].append("Canonical tag ausente")

            return json.dumps(current, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps(
                {"error": f"Erro ao analisar {params.url}: {str(e)}"},
                ensure_ascii=False,
            )
