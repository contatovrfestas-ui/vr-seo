# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VR SEO Aurora** is an autonomous AI agent for SEO, built following the Aurora pattern.
The project has two layers:
- **Python (Aurora agent)**: The new autonomous agent system in `agent/` + `main.py`
- **Node.js (legacy tools)**: The original SEO tools in `src/` (still usable, being migrated)

## Architecture

### Aurora Agent (Python)
```
main.py                     # Entry point - interactive chat loop
agent/
  core.py                   # ReAct loop (think -> tool -> observe -> repeat)
  identity.py               # Persona system (loads config/persona.yaml)
  llm.py                    # LLM client abstraction (Anthropic Claude)
  planner.py                # Multi-step task planning
  memory/
    working.py              # Current conversation context
    long_term.py            # SQLite persistent storage
    manager.py              # Memory orchestration layer
  tools/
    base.py                 # BaseTool abstract class
    registry.py             # Tool registration and dispatch
    seo_audit.py            # Full SEO audit tool
    content_generator.py    # SEO content generation
    web_crawler.py          # Site crawler
    meta_tags_analyzer.py   # Meta tags analysis
    schema_generator.py     # JSON-LD schema markup
    google_search_console.py# Google Search Console API
    google_analytics.py     # Google Analytics GA4 API
    datetime_tool.py        # Date/time utilities
    memory_tool.py          # Agent memory operations
config/
  settings.py               # Pydantic settings (loads .env)
  persona.yaml              # Agent identity configuration
data/
  memory.db                 # SQLite long-term memory (auto-created)
```

### Legacy Node.js
```
index.js                    # Original CLI entry point
src/agents/                 # Content + Audit agents
src/cli/                    # Commander CLI
src/integrations/google/    # Google OAuth2 + APIs
src/services/               # Claude client, config, logger
src/utils/                  # HTTP, validators, file I/O
src/formatters/             # Markdown, JSON, HTML output
```

## Commands

### Python Agent
- **Install dependencies:** `pip install -r requirements.txt`
- **Run agent:** `python main.py`
- **Run with debug logging:** `python main.py --log-level DEBUG`

### Node.js Legacy
- **Install:** `npm install`
- **Run CLI:** `node index.js`

## Key Design Decisions

- **Tool pattern**: Every tool is a class inheriting `BaseTool` with Pydantic `parameters` schema. Adding a tool = one file + register in `registry.py`.
- **Memory**: SQLite-based persistence (facts, tasks, conversations). Working memory auto-consolidates when threshold is exceeded.
- **Provider agnostic LLM**: `llm.py` wraps Anthropic but is designed for easy provider swap.
- **Language**: Code in English, user-facing content in pt-BR.

## Git

- **Remote:** `origin` points to `https://github.com/contatovrfestas-ui/vr-festas-agent.git`
- **Main branch:** `main`
