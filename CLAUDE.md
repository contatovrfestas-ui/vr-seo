# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**vr-seo** is a Node.js CLI platform (CommonJS modules) — an AI-powered SEO agency with autonomous agents using the Claude API. Entry point: `index.js`.

## Commands

- **Install dependencies:** `npm install`
- **Run CLI:** `node index.js` or `vr-seo` (if linked with `npm link`)
- **Run tests:** `npm test`
- **Lint:** `npm run lint`

### CLI Usage

```bash
# Content generation
node index.js content blog --topic "..." --keywords "k1,k2" [--tone professional] [--lang pt-BR]
node index.js content landing-page --topic "..." --keywords "k1,k2"
node index.js content institutional --about "..." --services "s1,s2"
node index.js content meta-tags --url "..."
node index.js content schema --url "..." --type Organization
node index.js content interactive

# SEO Audit
node index.js audit --url "https://site.com" [--depth 2] [--max-pages 50]
node index.js audit cwv --url "..."
node index.js audit links --url "..."
node index.js audit interactive

# Full pipeline
node index.js run --url "..." --full

# Google Auth
node index.js auth google login|status|revoke

# Config
node index.js config set ANTHROPIC_API_KEY "sk-..."
node index.js config list
```

## Architecture

```
src/
  cli/           # Commander CLI + Enquirer prompts
  core/          # AgentBase (EventEmitter), Orchestrator
  agents/
    content/     # ContentAgent + generators (blog, landing, institutional, meta, schema)
    audit/       # AuditAgent + analyzers (crawler, html, robots, errors, CWV, sitemap)
  integrations/  # Google OAuth2, Search Console, Analytics
  services/      # claude-client, logger (Winston), config-manager
  formatters/    # markdown, json, html output
  utils/         # http, validators, file-io
config/          # default.js
output/          # Generated reports and content
```

## Key Patterns

- All modules use `'use strict'` and CommonJS (`require`/`module.exports`)
- Agents extend `AgentBase` (EventEmitter) with `validate()`, `execute()`, `getCapabilities()`
- Config resolution: env vars → user config (~/.vr-seo/config.json) → defaults
- Claude API via `@anthropic-ai/sdk` wrapper in `services/claude-client.js`
- CJS-compatible packages: `ora@5`, `ansi-colors`, `enquirer`, `cheerio@1.0.0-rc.12`

## Git

- **Remote:** `origin` points to `https://github.com/contatovrfestas-ui/vr-festas-agent.git`
- **Main branch:** `main`
