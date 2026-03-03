"""
Classe base para todas as ferramentas do agente.

Cada tool e uma classe que herda de BaseTool e define:
- name: identificador unico
- description: descricao para o LLM entender quando usar
- parameters: modelo Pydantic com os parametros aceitos
- execute(): logica de execucao

O registry auto-gera o schema de function calling a partir do Pydantic model.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Type

from pydantic import BaseModel

logger = logging.getLogger("aurora.tools")


class BaseTool(ABC):
    """
    Classe abstrata base para todas as ferramentas.

    Para criar uma nova tool:
    1. Crie uma classe que herda de BaseTool
    2. Defina name, description, e parameters (Pydantic model)
    3. Implemente execute()
    4. Registre no ToolRegistry

    Exemplo:
        class MyParams(BaseModel):
            query: str = Field(description="Busca")

        class MyTool(BaseTool):
            name = "my_tool"
            description = "Faz algo util"
            parameters = MyParams

            async def execute(self, params: MyParams) -> str:
                return f"Resultado para: {params.query}"
    """

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[Type[BaseModel]]

    @abstractmethod
    async def execute(self, params: BaseModel) -> str:
        """
        Executa a ferramenta com os parametros validados.

        Args:
            params: Instancia do modelo Pydantic definido em `parameters`

        Returns:
            String com o resultado da execucao (sera enviado ao LLM)
        """
        ...

    async def safe_execute(self, raw_params: dict[str, Any]) -> str:
        """
        Valida os parametros e executa a tool com tratamento de erros.

        Este metodo e chamado pelo registry/core e garante que:
        1. Os parametros sao validados pelo Pydantic
        2. Erros sao capturados e retornados como string de erro
        """
        try:
            validated = self.parameters.model_validate(raw_params)
            logger.info(f"Executando tool: {self.name}")
            result = await self.execute(validated)
            logger.debug(f"Tool {self.name} concluida: {len(result)} chars")
            return result
        except Exception as e:
            error_msg = f"Erro ao executar {self.name}: {type(e).__name__}: {e}"
            logger.error(error_msg)
            return error_msg
