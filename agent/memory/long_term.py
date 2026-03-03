"""
Long-Term Memory - armazenamento persistente com SQLite.

Tabelas:
- facts: fatos aprendidos sobre o usuario, sites, preferencias
- tasks: tarefas em andamento e concluidas
- conversations: resumos de conversas passadas

O banco e criado automaticamente em data/memory.db na primeira execucao.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("aurora.memory.longterm")


class LongTermMemory:
    """
    Armazenamento persistente do agente usando SQLite.

    Persiste entre sessoes e permite que o agente lembre
    de informacoes de interacoes anteriores.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

        # Garante que o diretorio existe
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Obtem conexao com o banco (lazy)."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self) -> None:
        """Cria as tabelas se nao existirem."""
        conn = self._get_conn()

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary TEXT NOT NULL,
                topics TEXT,
                message_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
            CREATE INDEX IF NOT EXISTS idx_facts_content ON facts(content);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            """
        )
        conn.commit()

        logger.info(f"Long-term memory inicializada: {self._db_path}")

    # --- Facts ---

    async def save_fact(
        self, content: str, category: str = "general"
    ) -> int:
        """Salva um fato na memoria de longo prazo."""
        conn = self._get_conn()
        now = datetime.now().isoformat()

        # Verifica se ja existe fato similar (evita duplicatas)
        existing = conn.execute(
            "SELECT id FROM facts WHERE content = ? AND category = ?",
            (content, category),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE facts SET updated_at = ?, relevance_score = relevance_score + 0.1 WHERE id = ?",
                (now, existing["id"]),
            )
            conn.commit()
            logger.debug(f"Fato atualizado (id={existing['id']}): {content[:50]}")
            return existing["id"]

        cursor = conn.execute(
            "INSERT INTO facts (content, category, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (content, category, now, now),
        )
        conn.commit()

        fact_id = cursor.lastrowid
        logger.info(f"Fato salvo (id={fact_id}): {content[:50]}")
        return fact_id

    async def search_facts(self, query: str, limit: int = 10) -> list[dict]:
        """Busca fatos por termo (busca textual simples)."""
        conn = self._get_conn()

        # Busca por conteudo (LIKE) - em producao, usar embeddings
        rows = conn.execute(
            """
            SELECT id, content, category, created_at, relevance_score
            FROM facts
            WHERE content LIKE ?
            ORDER BY relevance_score DESC, updated_at DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()

        return [dict(row) for row in rows]

    async def list_facts(
        self, category: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        """Lista fatos salvos, opcionalmente filtrados por categoria."""
        conn = self._get_conn()

        if category:
            rows = conn.execute(
                "SELECT id, content, category, created_at FROM facts WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, content, category, created_at FROM facts ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    async def delete_fact(self, fact_id: int) -> None:
        """Remove um fato pelo ID."""
        conn = self._get_conn()
        conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()

    # --- Tasks ---

    async def save_task(self, description: str, metadata: Optional[dict] = None) -> int:
        """Salva uma tarefa pendente."""
        conn = self._get_conn()
        now = datetime.now().isoformat()

        cursor = conn.execute(
            "INSERT INTO tasks (description, status, created_at, metadata) VALUES (?, 'pending', ?, ?)",
            (description, now, json.dumps(metadata) if metadata else None),
        )
        conn.commit()

        task_id = cursor.lastrowid
        logger.info(f"Tarefa salva (id={task_id}): {description[:50]}")
        return task_id

    async def list_tasks(self, status: str = "pending") -> list[dict]:
        """Lista tarefas por status."""
        conn = self._get_conn()

        rows = conn.execute(
            "SELECT id, description, status, created_at, completed_at FROM tasks WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()

        return [dict(row) for row in rows]

    async def complete_task(self, task_id: int) -> None:
        """Marca uma tarefa como concluida."""
        conn = self._get_conn()
        now = datetime.now().isoformat()

        conn.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        conn.commit()
        logger.info(f"Tarefa concluida: id={task_id}")

    # --- Conversations ---

    async def save_conversation_summary(
        self, summary: str, topics: list[str], message_count: int
    ) -> int:
        """Salva o resumo de uma conversa."""
        conn = self._get_conn()
        now = datetime.now().isoformat()

        cursor = conn.execute(
            "INSERT INTO conversations (summary, topics, message_count, created_at) VALUES (?, ?, ?, ?)",
            (summary, json.dumps(topics), message_count, now),
        )
        conn.commit()

        conv_id = cursor.lastrowid
        logger.info(f"Conversa salva (id={conv_id}): {message_count} mensagens")
        return conv_id

    async def get_recent_conversations(self, limit: int = 5) -> list[dict]:
        """Retorna resumos de conversas recentes."""
        conn = self._get_conn()

        rows = conn.execute(
            "SELECT id, summary, topics, message_count, created_at FROM conversations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            try:
                d["topics"] = json.loads(d["topics"]) if d["topics"] else []
            except (json.JSONDecodeError, TypeError):
                d["topics"] = []
            results.append(d)

        return results

    # --- General ---

    async def get_relevant_context(self, query: str = "", limit: int = 10) -> str:
        """
        Recupera contexto relevante para injetar no system prompt.

        Combina fatos, tarefas pendentes e conversas recentes em
        um bloco de texto para contexto.
        """
        sections: list[str] = []

        # Fatos relevantes
        if query:
            facts = await self.search_facts(query, limit=5)
        else:
            facts = await self.list_facts(limit=10)

        if facts:
            fact_lines = ["### Fatos Conhecidos"]
            for f in facts:
                fact_lines.append(f"- [{f['category']}] {f['content']}")
            sections.append("\n".join(fact_lines))

        # Tarefas pendentes
        tasks = await self.list_tasks("pending")
        if tasks:
            task_lines = ["### Tarefas Pendentes"]
            for t in tasks:
                task_lines.append(f"- [#{t['id']}] {t['description']}")
            sections.append("\n".join(task_lines))

        # Conversas recentes
        conversations = await self.get_recent_conversations(limit=3)
        if conversations:
            conv_lines = ["### Conversas Recentes"]
            for c in conversations:
                topics = ", ".join(c["topics"]) if c["topics"] else "geral"
                conv_lines.append(f"- {c['created_at'][:10]}: {c['summary'][:100]} (temas: {topics})")
            sections.append("\n".join(conv_lines))

        return "\n\n".join(sections) if sections else ""

    def close(self) -> None:
        """Fecha a conexao com o banco."""
        if self._conn:
            self._conn.close()
            self._conn = None
