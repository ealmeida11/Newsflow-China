"""
Coletor Xinhua English - China-Biz.
URL: https://english.news.cn/list/china-business.htm

Extrai por item: título, URL e data/hora de publicação (span.time).
Um script consolidado por fonte: fetch, parse e lista de artigos no formato do banco.
"""

import logging
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import USER_AGENT

logger = logging.getLogger(__name__)

LIST_URL = "https://english.news.cn/list/china-business.htm"
BASE_URL_FOR_LINKS = "https://english.news.cn/list/china-business.htm"
CATEGORY = "China-Biz"
SOURCE_ID = "xinhua_chinabiz"


def _parse_published_time(text: str) -> datetime | None:
    """Converte '2026-02-18 16:20:00' em datetime."""
    if not text or not text.strip():
        return None
    text = text.strip()
    try:
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(text[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            return None


def _normalize_url(href: str) -> str:
    if not href:
        return ""
    return urljoin(BASE_URL_FOR_LINKS, href.strip()).split("?")[0]


def fetch_china_biz_list() -> str:
    """Baixa o HTML da lista China-Biz."""
    r = requests.get(
        LIST_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_china_biz_list(html: str) -> list[dict]:
    """
    Extrai da página China-Biz os itens com:
    title, url, summary (None), category, published_at, author (None).
    Cada entrada é um <a target="_blank"> com título e um <span class="time"> na mesma ordem.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles: list[dict] = []

    link_nodes = [
        a
        for a in soup.find_all("a", href=True, target="_blank")
        if a.get_text(strip=True) and a.get_text(strip=True) != "More"
    ]
    time_nodes = soup.find_all("span", class_="time")
    time_texts = [n.get_text(strip=True) for n in time_nodes]

    for i, a in enumerate(link_nodes):
        href = a.get("href", "").strip()
        title = a.get_text(strip=True)
        if not title or not href:
            continue
        url = _normalize_url(href)
        published_at = _parse_published_time(time_texts[i]) if i < len(time_texts) else None
        articles.append({
            "url": url,
            "title": title,
            "summary": None,
            "category": CATEGORY,
            "published_at": published_at,
            "author": None,
            "is_principal": False,
        })

    logger.info("Xinhua China-Biz: parsed %d articles", len(articles))
    return articles


def collect_xinhua_chinabiz() -> list[dict]:
    """Baixa a lista China-Biz e retorna artigos no formato do banco."""
    html = fetch_china_biz_list()
    return parse_china_biz_list(html)
