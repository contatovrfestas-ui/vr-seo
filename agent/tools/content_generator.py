"""
Tool de geracao de conteudo SEO para o agente Aurora.

Porta dos geradores de conteudo Node.js (blog, landing page, institutional).
Ao inves de chamar a Claude API diretamente, retorna o conteudo gerado
pelo LLM via tool-use - o agente usa esta tool e o LLM gera o conteudo.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools.content")

# Diretorio dos templates de prompt
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "src" / "agents" / "content" / "templates"


class ContentParams(BaseModel):
    """Parametros para geracao de conteudo."""

    content_type: str = Field(
        description=(
            "Tipo de conteudo a gerar. Opcoes: "
            "'blog' (post otimizado), "
            "'landing-page' (pagina de conversao), "
            "'institutional' (pagina institucional/sobre)"
        )
    )
    topic: str = Field(
        description="Topico principal do conteudo"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Lista de palavras-chave alvo para otimizacao SEO",
    )
    tone: str = Field(
        default="professional",
        description="Tom de escrita: professional, casual, technical, friendly, persuasive",
    )
    language: str = Field(
        default="pt-BR",
        description="Idioma do conteudo (ex: pt-BR, en-US)",
    )
    additional_instructions: str = Field(
        default="",
        description="Instrucoes adicionais para a geracao de conteudo",
    )


class ContentGeneratorTool(BaseTool):
    """Gera conteudo otimizado para SEO."""

    name = "content_generator"
    description = (
        "Gera conteudo otimizado para SEO. Suporta blog posts, landing pages "
        "e paginas institucionais. O conteudo e gerado com base no topico, "
        "keywords e tom especificados, seguindo melhores praticas de SEO "
        "(headings otimizados, keyword density, meta tags, CTAs, etc). "
        "Retorna um template/prompt detalhado que voce deve usar para "
        "gerar o conteudo final."
    )
    parameters = ContentParams

    async def execute(self, params: ContentParams) -> str:
        """
        Retorna um prompt estruturado para geracao de conteudo.

        Nota: esta tool NAO chama o LLM diretamente. Ela prepara o
        template de geracao que o agente usara para produzir conteudo.
        O design assim permite que o agente tenha controle total sobre
        o processo de geracao.
        """
        template = self._load_template(params.content_type)
        keywords_str = ", ".join(params.keywords) if params.keywords else "nao especificadas"

        if template:
            # Substituir variaveis no template
            filled = template.replace("{{topic}}", params.topic)
            filled = filled.replace("{{keywords}}", keywords_str)
            filled = filled.replace("{{tone}}", params.tone)
            filled = filled.replace("{{language}}", params.language)

            if params.additional_instructions:
                filled += f"\n\n## Instrucoes Adicionais:\n{params.additional_instructions}"

            result = {
                "status": "template_ready",
                "content_type": params.content_type,
                "topic": params.topic,
                "keywords": params.keywords,
                "tone": params.tone,
                "language": params.language,
                "prompt_template": filled,
                "instructions": (
                    "Use este template para gerar o conteudo. "
                    "Responda diretamente ao usuario com o conteudo gerado, "
                    "formatado em Markdown."
                ),
            }
        else:
            # Template nao encontrado, gerar instrucoes genericas
            result = {
                "status": "generic_instructions",
                "content_type": params.content_type,
                "topic": params.topic,
                "keywords": params.keywords,
                "tone": params.tone,
                "language": params.language,
                "instructions": self._build_generic_instructions(params),
            }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def _load_template(self, content_type: str) -> Optional[str]:
        """Carrega o template de prompt do disco."""
        template_map = {
            "blog": "blog.md",
            "landing-page": "landing-page.md",
            "institutional": "institutional.md",
        }

        filename = template_map.get(content_type)
        if not filename:
            return None

        template_path = TEMPLATES_DIR / filename
        if not template_path.exists():
            logger.warning(f"Template nao encontrado: {template_path}")
            return None

        return template_path.read_text(encoding="utf-8")

    def _build_generic_instructions(self, params: ContentParams) -> str:
        """Gera instrucoes genericas quando nao ha template."""
        return (
            f"Gere conteudo do tipo '{params.content_type}' sobre '{params.topic}'.\n"
            f"Keywords alvo: {', '.join(params.keywords) if params.keywords else 'N/A'}\n"
            f"Tom: {params.tone}\n"
            f"Idioma: {params.language}\n\n"
            f"Requisitos SEO:\n"
            f"- Title tag otimizado (50-60 chars)\n"
            f"- Meta description (150-160 chars)\n"
            f"- Headings H1, H2, H3 estruturados\n"
            f"- Keywords distribuidas naturalmente\n"
            f"- Paragrafos curtos e listas\n"
            f"- CTA no final"
        )
