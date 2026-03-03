"""
Tool de web crawling para o agente Aurora SEO.

Porta direta da logica do crawler Node.js, adaptada para Python async
com httpx e BeautifulSoup.
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools.crawler")


class CrawlerParams(BaseModel):
    """Parametros para o crawler."""

    url: str = Field(description="URL inicial para crawlear")
    max_depth: int = Field(
        default=2,
        description="Profundidade maxima de crawling (0 = apenas a pagina inicial)",
    )
    max_pages: int = Field(
        default=20,
        description="Numero maximo de paginas a crawlear",
    )


class WebCrawlerTool(BaseTool):
    """Crawler que navega um site coletando dados de cada pagina."""

    name = "web_crawler"
    description = (
        "Crawlea um site web a partir de uma URL, navegando pelos links internos "
        "ate a profundidade especificada. Retorna dados de cada pagina encontrada "
        "incluindo status HTTP, links, titulo, e meta description. "
        "Use para mapear a estrutura de um site antes de uma auditoria detalhada."
    )
    parameters = CrawlerParams

    USER_AGENT = "VR-SEO-Aurora/2.0"
    TIMEOUT = 10.0  # seconds

    async def execute(self, params: CrawlerParams) -> str:
        visited: dict[str, bool] = {}
        queue: list[dict] = [{"url": params.url, "depth": 0}]
        results: list[dict] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.TIMEOUT,
            follow_redirects=True,
            verify=False,
        ) as client:
            while queue and len(results) < params.max_pages:
                item = queue.pop(0)
                url = item["url"]
                depth = item["depth"]

                if url in visited or depth > params.max_depth:
                    continue
                visited[url] = True

                try:
                    response = await client.get(url)
                    page_data = {
                        "url": url,
                        "status": response.status_code,
                        "depth": depth,
                        "title": "",
                        "meta_description": "",
                        "h1": "",
                        "links_count": 0,
                    }

                    if (
                        response.status_code < 400
                        and "text/html" in response.headers.get("content-type", "")
                    ):
                        soup = BeautifulSoup(response.text, "lxml")

                        # Extrair metadados basicos
                        title_tag = soup.find("title")
                        page_data["title"] = (
                            title_tag.get_text(strip=True) if title_tag else ""
                        )

                        meta_desc = soup.find("meta", attrs={"name": "description"})
                        page_data["meta_description"] = (
                            meta_desc.get("content", "") if meta_desc else ""
                        )

                        h1_tag = soup.find("h1")
                        page_data["h1"] = (
                            h1_tag.get_text(strip=True) if h1_tag else ""
                        )

                        # Extrair links internos
                        links = []
                        for a_tag in soup.find_all("a", href=True):
                            href = a_tag["href"]
                            resolved = urljoin(url, href)
                            if self._is_same_origin(params.url, resolved):
                                links.append(resolved)
                                if (
                                    depth + 1 <= params.max_depth
                                    and resolved not in visited
                                ):
                                    queue.append(
                                        {"url": resolved, "depth": depth + 1}
                                    )

                        page_data["links_count"] = len(links)

                    results.append(page_data)
                    logger.debug(
                        f"Crawled: {url} ({response.status_code})"
                    )

                except Exception as e:
                    results.append(
                        {
                            "url": url,
                            "status": 0,
                            "depth": depth,
                            "error": str(e),
                        }
                    )
                    logger.warning(f"Falha ao crawlear {url}: {e}")

        summary = {
            "total_pages": len(results),
            "successful": sum(1 for r in results if r.get("status", 0) < 400),
            "errors": sum(1 for r in results if r.get("status", 0) >= 400 or r.get("error")),
            "pages": results,
        }

        return json.dumps(summary, ensure_ascii=False, indent=2)

    @staticmethod
    def _is_same_origin(base_url: str, target_url: str) -> bool:
        """Verifica se duas URLs pertencem ao mesmo dominio."""
        try:
            base = urlparse(base_url)
            target = urlparse(target_url)
            return base.netloc == target.netloc
        except Exception:
            return False
