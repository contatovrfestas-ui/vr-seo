"""
Registro central de ferramentas do agente.

Responsavel por:
- Registrar e armazenar tools
- Despachar chamadas de tool por nome
- Gerar schemas de function calling para o LLM
"""

from __future__ import annotations

import logging
from typing import Any, Type

from agent.tools.base import BaseTool

logger = logging.getLogger("aurora.tools")


class ToolRegistry:
    """
    Registro modular de ferramentas.

    Todas as tools sao registradas aqui e podem ser consultadas
    pelo core do agente durante o loop ReAct.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Registra uma instancia de tool.

        Args:
            tool: Instancia de uma classe que herda de BaseTool
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' ja registrada. Substituindo.")

        self._tools[tool.name] = tool
        logger.info(f"Tool registrada: {tool.name}")

    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """Registra uma tool a partir da classe (instancia automaticamente)."""
        self.register(tool_class())

    def get(self, name: str) -> BaseTool | None:
        """Busca uma tool pelo nome."""
        return self._tools.get(name)

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """
        Executa uma tool pelo nome com os parametros fornecidos.

        Args:
            name: Nome da tool
            params: Dicionario de parametros (sera validado pelo Pydantic)

        Returns:
            Resultado da execucao como string
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Erro: ferramenta '{name}' nao encontrada. Ferramentas disponiveis: {', '.join(self.list_names())}"

        return await tool.safe_execute(params)

    def list_names(self) -> list[str]:
        """Retorna lista de nomes das tools registradas."""
        return list(self._tools.keys())

    def list_tools(self) -> list[BaseTool]:
        """Retorna lista de instancias das tools registradas."""
        return list(self._tools.values())

    def get_tool_classes(self) -> list[type]:
        """
        Retorna as classes das tools registradas.
        Usado pelo LLM client para gerar schemas.
        """
        return [type(t) for t in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def create_default_registry() -> ToolRegistry:
    """
    Cria um registry com todas as tools padrao do VR SEO.

    Esta funcao e o ponto central de registro. Para adicionar uma
    nova tool, basta importar e registrar aqui.
    """
    registry = ToolRegistry()

    # Importa e registra todas as tools
    from agent.tools.seo_audit import SeoAuditTool
    from agent.tools.content_generator import ContentGeneratorTool
    from agent.tools.web_crawler import WebCrawlerTool
    from agent.tools.meta_tags_analyzer import MetaTagsAnalyzerTool
    from agent.tools.schema_generator import SchemaGeneratorTool
    from agent.tools.google_search_console import GoogleSearchConsoleTool
    from agent.tools.google_analytics import GoogleAnalyticsTool
    from agent.tools.datetime_tool import DateTimeTool
    from agent.tools.memory_tool import MemoryTool

    registry.register(SeoAuditTool())
    registry.register(ContentGeneratorTool())
    registry.register(WebCrawlerTool())
    registry.register(MetaTagsAnalyzerTool())
    registry.register(SchemaGeneratorTool())
    registry.register(GoogleSearchConsoleTool())
    registry.register(GoogleAnalyticsTool())
    registry.register(DateTimeTool())
    registry.register(MemoryTool())

    logger.info(f"Registry inicializado com {len(registry)} tools")
    return registry
