"""
Tradução de título e resumo para português (EN/ZH → PT).
Usa deep-translator (Google) com cache e pequeno delay para evitar rate limit.
"""

from __future__ import annotations

import time
from typing import Optional

# Cache: texto original -> texto traduzido (evita repetir mesma frase)
_cache: dict[str, str] = {}


def _translate(text: str, target: str = "pt") -> str:
    if not text or not (t := text.strip()):
        return text or ""
    if t in _cache:
        return _cache[t]
    try:
        from deep_translator import GoogleTranslator
        out = GoogleTranslator(source="auto", target=target).translate(t)
        if out and out.strip():
            _cache[t] = out.strip()
            return _cache[t]
    except Exception:
        pass
    _cache[t] = t
    return t


def translate_to_portuguese(text: Optional[str]) -> str:
    """Traduz um texto para português. Retorna o original em caso de erro ou vazio."""
    if text is None:
        return ""
    return _translate(text)


def translate_article_row(row: tuple, delay_seconds: float = 0.2) -> tuple:
    """
    Recebe uma linha (source, url, title, summary, category, published_at, author, is_principal)
    e retorna a mesma estrutura com title e summary traduzidos para português.
    """
    source, url, title, summary, category, published_at, author, is_principal = row
    title_pt = translate_to_portuguese(title)
    time.sleep(delay_seconds)
    summary_pt = translate_to_portuguese(summary) if summary else ""
    time.sleep(delay_seconds)
    return (source, url, title_pt, summary_pt, category, published_at, author, is_principal)


def translate_newsflow_rows(rows: list[tuple], delay_seconds: float = 0.2) -> list[tuple]:
    """Traduz título e summary de cada linha para português. Mantém cache entre chamadas."""
    out = []
    for i, r in enumerate(rows):
        out.append(translate_article_row(r, delay_seconds=delay_seconds))
        if (i + 1) % 5 == 0:
            time.sleep(0.5)  # pausa extra a cada 5 para evitar limite
    return out
