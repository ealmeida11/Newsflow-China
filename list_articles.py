"""
Lista artigos no banco (para conferir coleta).
Uso: python list_articles.py [--source globaltimes] [--limit 20]
"""

import argparse
import sys
from db import get_connection


def _safe_print(s: str) -> None:
    """Imprime string evitando erro de encoding no Windows."""
    if s is None:
        return
    out = (s.replace("\u200b", "").replace("\ufffd", "") if isinstance(s, str) else str(s))
    enc = sys.stdout.encoding or "utf-8"
    try:
        sys.stdout.buffer.write((out + "\n").encode(enc, errors="replace"))
    except (AttributeError, UnicodeEncodeError):
        print(out.encode(enc, errors="replace").decode(enc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="Filtrar por source (ex: globaltimes)")
    ap.add_argument("--limit", type=int, default=50, help="Máximo de linhas")
    args = ap.parse_args()
    conn = get_connection()
    try:
        sql = "SELECT source, url, title, summary, category, published_at, author, scraped_at FROM articles"
        params = []
        if args.source:
            sql += " WHERE source = ?"
            params.append(args.source)
        sql += " ORDER BY published_at DESC NULLS LAST, id DESC LIMIT ?"
        params.append(args.limit)
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        for i, row in enumerate(rows, 1):
            d = dict(zip(cols, row))
            title = (d["title"] or "")[:80] + ("..." if len(d["title"] or "") > 80 else "")
            summary = d["summary"] or ""
            if len(summary) > 100:
                summary = summary[:100] + "..."
            _safe_print(f"\n--- {i} ---")
            _safe_print("source: " + str(d["source"]))
            _safe_print("title: " + title)
            _safe_print("url: " + str(d["url"]))
            _safe_print("summary: " + summary)
            _safe_print("category: " + str(d["category"]))
            _safe_print("published_at: " + str(d["published_at"]))
            _safe_print("author: " + str(d["author"]))
            _safe_print("scraped_at: " + str(d["scraped_at"]))
        print(f"\nTotal exibido: {len(rows)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
