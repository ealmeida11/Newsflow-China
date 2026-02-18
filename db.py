"""
Banco de dados SQLite para armazenar notícias de todas as fontes.
Permite consultar notícias antigas no futuro.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection():
    """Retorna conexão com o banco (path criado se não existir)."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Cria a tabela de artigos se não existir."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                category TEXT,
                published_at TEXT,
                author TEXT,
                scraped_at TEXT NOT NULL,
                is_principal INTEGER NOT NULL DEFAULT 0,
                UNIQUE(source, url)
            )
        """)
        # Migração: adicionar is_principal se a tabela já existia sem a coluna
        cur = conn.execute("PRAGMA table_info(articles)")
        cols = [row[1] for row in cur.fetchall()]
        if "is_principal" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN is_principal INTEGER NOT NULL DEFAULT 0")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_is_principal ON articles(is_principal)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)"
        )
        conn.commit()
    finally:
        conn.close()


def _iso(dt: datetime | None) -> str | None:
    """Converte datetime para string ISO ou None."""
    if dt is None:
        return None
    return dt.isoformat()


def upsert_article(
    source: str,
    url: str,
    title: str,
    summary: str | None = None,
    category: str | None = None,
    published_at: datetime | None = None,
    author: str | None = None,
) -> None:
    """Insere ou atualiza um artigo (por source + url)."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO articles (source, url, title, summary, category, published_at, author, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, url) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                category = excluded.category,
                published_at = excluded.published_at,
                author = excluded.author,
                scraped_at = excluded.scraped_at
            """,
            (
                source,
                url,
                title,
                summary or None,
                category or None,
                _iso(published_at),
                author or None,
                _iso(datetime.utcnow()),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_articles_batch(source: str, articles: list[dict]) -> int:
    """Insere ou atualiza uma lista de artigos. Retorna quantidade processada."""
    conn = get_connection()
    scraped_at = _iso(datetime.utcnow())
    count = 0
    try:
        for a in articles:
            is_principal = 1 if a.get("is_principal") else 0
            conn.execute(
                """
                INSERT INTO articles (source, url, title, summary, category, published_at, author, scraped_at, is_principal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, url) DO UPDATE SET
                    title = excluded.title,
                    summary = excluded.summary,
                    category = excluded.category,
                    published_at = excluded.published_at,
                    author = excluded.author,
                    scraped_at = excluded.scraped_at,
                    is_principal = CASE WHEN excluded.is_principal = 1 THEN 1 ELSE is_principal END
                """,
                (
                    source,
                    a["url"],
                    a["title"],
                    a.get("summary"),
                    a.get("category"),
                    _iso(a.get("published_at")) if isinstance(a.get("published_at"), datetime) else a.get("published_at"),
                    a.get("author"),
                    scraped_at,
                    is_principal,
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def get_last_scraped_at(source: str) -> str | None:
    """Retorna a data/hora da última coleta (scraped_at) para o source."""
    conn = get_connection()
    row = conn.execute(
        "SELECT max(scraped_at) FROM articles WHERE source = ?",
        (source,),
    ).fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def get_newsflow_articles(source: str, hours: int = 24) -> list[tuple]:
    """
    Retorna artigos do newsflow: todas as notícias do source com published_at
    nas últimas `hours` horas, ordenadas por data decrescente (uma única lista, sem "destaques").
    """
    from datetime import datetime, timezone, timedelta

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT source, url, title, summary, category, published_at, author, is_principal
        FROM articles
        WHERE source = ?
        ORDER BY published_at DESC NULLS LAST, id DESC
        """,
        (source,),
    ).fetchall()
    conn.close()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = []
    for r in rows:
        source_, url, title, summary, category, published_at, author, is_principal = r
        if not published_at:
            continue
        try:
            s = published_at.strip()[:19]
            if "T" in s:
                dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
            else:
                dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                result.append(r)
        except (ValueError, TypeError):
            pass
    return result
