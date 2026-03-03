"""
Configuracoes centralizadas do projeto VR SEO Aurora.
Carrega variaveis de ambiente e define defaults.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


# Diretorios base
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


class AnthropicSettings(BaseSettings):
    """Configuracoes do provedor Anthropic Claude."""

    api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    model: str = Field(default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL")
    max_tokens: int = Field(default=4096, alias="ANTHROPIC_MAX_TOKENS")


class GoogleSettings(BaseSettings):
    """Configuracoes do Google OAuth2 e APIs."""

    client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    redirect_uri: str = Field(
        default="http://localhost:3456/callback", alias="GOOGLE_REDIRECT_URI"
    )
    scopes: list[str] = [
        "https://www.googleapis.com/auth/webmasters.readonly",
        "https://www.googleapis.com/auth/analytics.readonly",
    ]
    token_path: Optional[str] = None
    callback_port: int = 3456


class CrawlerSettings(BaseSettings):
    """Configuracoes do crawler de sites."""

    max_depth: int = Field(default=2, alias="MAX_CRAWL_DEPTH")
    max_pages: int = Field(default=50, alias="MAX_CRAWL_PAGES")
    timeout: int = 10000  # ms
    user_agent: str = "VR-SEO-Aurora/2.0"
    concurrency: int = 5


class ContentSettings(BaseSettings):
    """Configuracoes de geracao de conteudo."""

    default_language: str = Field(default="pt-BR", alias="DEFAULT_LANGUAGE")
    default_tone: str = Field(default="professional", alias="DEFAULT_TONE")


class MemorySettings(BaseSettings):
    """Configuracoes do sistema de memoria."""

    db_path: str = str(DATA_DIR / "memory.db")
    max_working_memory_messages: int = 50
    max_context_tokens: int = 100000
    consolidation_threshold: int = 30  # messages before auto-summarization


class Settings(BaseSettings):
    """Configuracoes globais do projeto."""

    anthropic: AnthropicSettings = AnthropicSettings()
    google: GoogleSettings = GoogleSettings()
    crawler: CrawlerSettings = CrawlerSettings()
    content: ContentSettings = ContentSettings()
    memory: MemorySettings = MemorySettings()

    log_level: str = Field(default="info", alias="LOG_LEVEL")
    output_dir: str = Field(default=str(OUTPUT_DIR), alias="OUTPUT_DIR")
    persona_path: str = str(CONFIG_DIR / "persona.yaml")

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Factory que retorna a instancia de settings, carregando .env se existir."""
    from dotenv import load_dotenv

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    return Settings()
