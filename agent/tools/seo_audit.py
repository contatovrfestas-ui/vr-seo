"""
Tool de auditoria SEO completa para o agente Aurora.

Porta das funcionalidades do AuditAgent Node.js:
- Analise HTML (title, meta, headings, images, canonical, etc.)
- Analise de robots.txt
- Verificacao de links quebrados
- Analise de performance basica
- Deteccao de sitemap

A auditoria e executada de forma integrada em uma unica chamada.
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

logger = logging.getLogger("aurora.tools.audit")


class AuditParams(BaseModel):
    """Parametros para auditoria SEO."""

    url: str = Field(description="URL do site a ser auditado")
    max_pages: int = Field(
        default=10,
        description="Numero maximo de paginas a analisar no crawl",
    )
    check_links: bool = Field(
        default=True,
        description="Se deve verificar links quebrados",
    )
    check_robots: bool = Field(
        default=True,
        description="Se deve analisar o robots.txt",
    )


class SeoAuditTool(BaseTool):
    """Auditoria SEO completa de um site."""

    name = "seo_audit"
    description = (
        "Executa uma auditoria SEO completa em um site web. "
        "Analisa HTML de cada pagina (title, meta description, headings, "
        "imagens sem alt, canonical, viewport, Open Graph, lang), "
        "verifica robots.txt, detecta links quebrados, analisa performance "
        "basica e busca sitemap. Retorna score, issues e recomendacoes."
    )
    parameters = AuditParams

    USER_AGENT = "VR-SEO-Aurora/2.0"
    TIMEOUT = 10.0

    async def execute(self, params: AuditParams) -> str:
        all_issues: list[dict] = []
        pages_data: list[dict] = []

        async with httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.TIMEOUT,
            follow_redirects=True,
            verify=False,
        ) as client:
            # Step 1: Crawl pages
            pages_html = await self._crawl_pages(
                client, params.url, params.max_pages
            )

            # Step 2: Analyze HTML of each page
            for page in pages_html:
                if page.get("html") and page.get("status", 0) < 400:
                    html_issues, html_data = self._analyze_html(
                        page["html"], page["url"]
                    )
                    all_issues.extend(html_issues)
                    pages_data.append(
                        {"url": page["url"], "status": page["status"], **html_data}
                    )
                else:
                    pages_data.append(
                        {"url": page["url"], "status": page.get("status", 0)}
                    )

            # Step 3: Analyze robots.txt
            if params.check_robots:
                robots_issues = await self._analyze_robots(client, params.url)
                all_issues.extend(robots_issues)

            # Step 4: Check broken links
            if params.check_links:
                link_issues = await self._check_links(client, pages_html)
                all_issues.extend(link_issues)

            # Step 5: Check sitemap
            sitemap_found = await self._find_sitemap(client, params.url)
            if not sitemap_found:
                all_issues.append(
                    {
                        "title": "Sitemap nao encontrado",
                        "severity": "warning",
                        "description": "Nao foi possivel encontrar sitemap.xml.",
                        "recommendation": "Crie um sitemap.xml e submeta ao Google Search Console.",
                    }
                )

            # Step 6: Performance analysis
            perf_issues = self._analyze_performance(pages_html)
            all_issues.extend(perf_issues)

        # Calculate score
        score = self._calculate_score(all_issues)

        result = {
            "url": params.url,
            "score": score,
            "summary": (
                f"Analisadas {len(pages_data)} paginas. "
                f"Encontrados {len(all_issues)} problemas."
            ),
            "issues": all_issues,
            "pages": pages_data,
            "sitemap_found": sitemap_found,
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    async def _crawl_pages(
        self, client: httpx.AsyncClient, start_url: str, max_pages: int
    ) -> list[dict]:
        """Crawl basico para coletar HTML das paginas."""
        visited: set[str] = set()
        queue = [start_url]
        results: list[dict] = []

        while queue and len(results) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                response = await client.get(url)
                content_type = response.headers.get("content-type", "")
                html = response.text if "text/html" in content_type else ""

                results.append(
                    {
                        "url": str(response.url),
                        "status": response.status_code,
                        "html": html,
                        "headers": dict(response.headers),
                    }
                )

                # Extract internal links for queue
                if html and response.status_code < 400:
                    soup = BeautifulSoup(html, "lxml")
                    for a_tag in soup.find_all("a", href=True):
                        href = urljoin(url, a_tag["href"])
                        parsed = urlparse(href)
                        base_parsed = urlparse(start_url)
                        if (
                            parsed.netloc == base_parsed.netloc
                            and href not in visited
                            and not parsed.fragment
                        ):
                            # Normalize and add
                            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                            if clean_url not in visited:
                                queue.append(clean_url)

            except Exception as e:
                results.append({"url": url, "status": 0, "html": "", "error": str(e)})

        return results

    def _analyze_html(self, html: str, url: str) -> tuple[list[dict], dict]:
        """Analisa HTML de uma pagina e retorna issues e dados extraidos."""
        soup = BeautifulSoup(html, "lxml")
        issues: list[dict] = []
        data: dict = {}

        # Title tag
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        data["title"] = title

        if not title:
            issues.append(
                {"title": "Title tag ausente", "severity": "critical", "page": url}
            )
        elif len(title) > 60:
            issues.append(
                {
                    "title": "Title tag muito longo",
                    "severity": "warning",
                    "page": url,
                    "description": f"{len(title)} caracteres (max 60)",
                }
            )
        elif len(title) < 30:
            issues.append(
                {
                    "title": "Title tag muito curto",
                    "severity": "warning",
                    "page": url,
                    "description": f"{len(title)} caracteres (min 30)",
                }
            )

        # Meta description
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc_tag.get("content", "") if meta_desc_tag else ""
        data["meta_description"] = meta_desc

        if not meta_desc:
            issues.append(
                {
                    "title": "Meta description ausente",
                    "severity": "critical",
                    "page": url,
                }
            )
        elif len(meta_desc) > 160:
            issues.append(
                {
                    "title": "Meta description muito longa",
                    "severity": "warning",
                    "page": url,
                    "description": f"{len(meta_desc)} caracteres (max 160)",
                }
            )

        # H1 tags
        h1_tags = soup.find_all("h1")
        data["h1"] = h1_tags[0].get_text(strip=True) if h1_tags else ""

        if len(h1_tags) == 0:
            issues.append(
                {"title": "H1 tag ausente", "severity": "critical", "page": url}
            )
        elif len(h1_tags) > 1:
            issues.append(
                {
                    "title": "Multiplas H1 tags",
                    "severity": "warning",
                    "page": url,
                    "description": f"Encontradas {len(h1_tags)} H1 tags",
                }
            )

        # Heading hierarchy
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            headings.append(int(tag.name[1]))

        for i in range(1, len(headings)):
            if headings[i] - headings[i - 1] > 1:
                issues.append(
                    {
                        "title": "Nivel de heading pulado",
                        "severity": "warning",
                        "page": url,
                        "description": f"H{headings[i-1]} para H{headings[i]}",
                    }
                )
                break

        # Images without alt
        imgs_no_alt = len(soup.find_all("img", alt=False)) + len(
            soup.find_all("img", alt="")
        )
        if imgs_no_alt > 0:
            issues.append(
                {
                    "title": "Imagens sem alt text",
                    "severity": "warning",
                    "page": url,
                    "description": f"{imgs_no_alt} imagem(ns) sem alt text",
                }
            )

        # Canonical
        canonical = soup.find("link", rel="canonical")
        data["canonical"] = canonical.get("href", "") if canonical else ""
        if not canonical:
            issues.append(
                {"title": "Canonical tag ausente", "severity": "warning", "page": url}
            )

        # Viewport
        if not soup.find("meta", attrs={"name": "viewport"}):
            issues.append(
                {
                    "title": "Viewport meta tag ausente",
                    "severity": "warning",
                    "page": url,
                }
            )

        # Open Graph
        if not soup.find("meta", property="og:title"):
            issues.append(
                {
                    "title": "Open Graph tags ausentes",
                    "severity": "info",
                    "page": url,
                }
            )

        # Language
        html_tag = soup.find("html")
        lang = html_tag.get("lang", "") if html_tag else ""
        data["lang"] = lang
        if not lang:
            issues.append(
                {
                    "title": "Atributo lang ausente no html",
                    "severity": "warning",
                    "page": url,
                }
            )

        # Word count
        body = soup.find("body")
        body_text = body.get_text(" ", strip=True) if body else ""
        data["word_count"] = len(body_text.split())

        return issues, data

    async def _analyze_robots(
        self, client: httpx.AsyncClient, base_url: str
    ) -> list[dict]:
        """Analisa o robots.txt do site."""
        issues: list[dict] = []
        robots_url = urljoin(base_url, "/robots.txt")

        try:
            response = await client.get(robots_url)

            if response.status_code == 404:
                issues.append(
                    {
                        "title": "robots.txt ausente",
                        "severity": "warning",
                        "description": "Nenhum robots.txt encontrado.",
                        "recommendation": "Crie um robots.txt para controlar o acesso de crawlers.",
                    }
                )
                return issues

            content = response.text

            # Check if entire site is blocked
            for line in content.split("\n"):
                if line.strip() == "Disallow: /":
                    issues.append(
                        {
                            "title": "Site inteiro bloqueado pelo robots.txt",
                            "severity": "critical",
                            "description": 'robots.txt contem "Disallow: /" bloqueando todos os crawlers.',
                            "recommendation": 'Remova ou modifique a regra "Disallow: /".',
                        }
                    )

            # Check for sitemap reference
            if "sitemap:" not in content.lower():
                issues.append(
                    {
                        "title": "Sem referencia a sitemap no robots.txt",
                        "severity": "info",
                        "description": "robots.txt nao referencia um sitemap.",
                        "recommendation": 'Adicione "Sitemap: https://seusite.com/sitemap.xml".',
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "title": "Erro ao buscar robots.txt",
                    "severity": "info",
                    "description": str(e),
                }
            )

        return issues

    async def _check_links(
        self, client: httpx.AsyncClient, pages: list[dict]
    ) -> list[dict]:
        """Verifica links quebrados nas paginas crawleadas."""
        issues: list[dict] = []
        checked: dict[str, int] = {}

        for page in pages:
            if not page.get("html"):
                continue

            soup = BeautifulSoup(page["html"], "lxml")

            for a_tag in soup.find_all("a", href=True):
                href = urljoin(page["url"], a_tag["href"])
                if not href.startswith("http"):
                    continue

                if href in checked:
                    status = checked[href]
                else:
                    try:
                        resp = await client.head(href, timeout=5.0)
                        status = resp.status_code
                    except Exception:
                        status = 0
                    checked[href] = status

                if status >= 400 or status == 0:
                    issues.append(
                        {
                            "title": f"Link quebrado ({status})",
                            "severity": "critical" if status >= 500 or status == 0 else "warning",
                            "page": page["url"],
                            "description": f"Link para {href} retorna {status}",
                            "recommendation": "Corrija ou remova o link quebrado.",
                        }
                    )

            # Limit link checking to avoid too many requests
            if len(checked) > 100:
                break

        return issues

    async def _find_sitemap(
        self, client: httpx.AsyncClient, base_url: str
    ) -> bool:
        """Verifica se o site tem sitemap."""
        candidates = [
            urljoin(base_url, "/sitemap.xml"),
            urljoin(base_url, "/sitemap_index.xml"),
        ]

        for url in candidates:
            try:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200 and (
                    "<urlset" in response.text or "<sitemapindex" in response.text
                ):
                    return True
            except Exception:
                continue

        return False

    def _analyze_performance(self, pages: list[dict]) -> list[dict]:
        """Analise basica de performance baseada no HTML."""
        issues: list[dict] = []

        for page in pages:
            if not page.get("html") or page.get("status", 0) >= 400:
                continue

            html = page["html"]
            url = page["url"]

            # Page size
            size_kb = len(html.encode("utf-8")) / 1024
            if size_kb > 500:
                issues.append(
                    {
                        "title": "Pagina HTML muito grande",
                        "severity": "warning",
                        "page": url,
                        "description": f"Tamanho: {size_kb:.0f}KB (recomendado < 500KB)",
                    }
                )

            # Render-blocking scripts
            import re

            scripts = re.findall(r'<script[^>]*src="[^"]*"[^>]*>', html, re.I)
            blocking = [
                s for s in scripts if "async" not in s and "defer" not in s
            ]
            if len(blocking) > 3:
                issues.append(
                    {
                        "title": "Scripts bloqueando renderizacao",
                        "severity": "warning",
                        "page": url,
                        "description": f"{len(blocking)} scripts sem async/defer.",
                        "recommendation": "Adicione async ou defer aos scripts nao-criticos.",
                    }
                )

            # Mixed content
            if url.startswith("https://"):
                mixed = len(re.findall(r'(?:src|href)="http://', html, re.I))
                if mixed > 0:
                    issues.append(
                        {
                            "title": "Conteudo misto detectado",
                            "severity": "critical",
                            "page": url,
                            "description": f"{mixed} recursos HTTP em pagina HTTPS.",
                            "recommendation": "Atualize todas as URLs para HTTPS.",
                        }
                    )

            # Compression check
            headers = page.get("headers", {})
            if headers and not headers.get("content-encoding"):
                issues.append(
                    {
                        "title": "Sem compressao detectada",
                        "severity": "warning",
                        "page": url,
                        "description": "Resposta sem compressao gzip/brotli.",
                        "recommendation": "Habilite compressao no servidor.",
                    }
                )

        return issues

    @staticmethod
    def _calculate_score(issues: list[dict]) -> int:
        """Calcula score SEO baseado nos issues encontrados."""
        score = 100
        for issue in issues:
            severity = issue.get("severity", "info")
            if severity == "critical":
                score -= 10
            elif severity == "warning":
                score -= 3
            elif severity == "info":
                score -= 1
        return max(0, min(100, score))
