"""
Coletor South China Morning Post - China.
URL: https://www.scmp.com/news/china

Extrai: título e link de span[data-qa="ContentHeadline-Headline"] (parent <a>),
resumo de h3[data-qa="ContentSummary-ContainerWithTag"],
categoria de a[data-qa="BaseLink-renderAnchor-StyledAnchor"],
data/hora de time[data-qa="ContentActionBar-handleRenderDisplayDateTime-time"].
Quando o texto do time for relativo ("1 hour ago", "X minutes ago"), usa o horário atual
de Hong Kong no momento da coleta para calcular a data/hora.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from config import USER_AGENT

logger = logging.getLogger(__name__)

BASE_URL = "https://www.scmp.com"
LIST_URL = "https://www.scmp.com/news/china"
TZ_HONG_KONG = ZoneInfo("Asia/Hong_Kong")


def _normalize_url(href: str) -> str:
    if not href:
        return ""
    return urljoin(BASE_URL, href.strip()).split("?")[0]


def _parse_datetime_attr(dt_iso: str | None) -> datetime | None:
    """Converte datetime ISO (ex: 2026-02-18T19:12:50.000Z) em datetime UTC."""
    if not dt_iso or not dt_iso.strip():
        return None
    s = dt_iso.strip()[:23].replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(dt_iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _parse_relative_time(text: str, now_hk: datetime) -> datetime | None:
    """
    Converte texto relativo ('1 hour ago', '45 minutes ago', '2 days ago')
    usando now_hk (horário atual em Hong Kong). Retorna datetime em UTC.
    """
    if not text or not text.strip():
        return None
    text = text.strip().lower()
    # "X minute(s) ago", "X hour(s) ago", "X day(s) ago"
    m = re.match(r"(\d+)\s*(minute|hour|day)s?\s+ago", text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "minute":
        delta = timedelta(minutes=n)
    elif unit == "hour":
        delta = timedelta(hours=n)
    else:
        delta = timedelta(days=n)
    # now_hk is already in HK time (naive or aware); treat as HK and convert to UTC
    if now_hk.tzinfo is None:
        now_hk = now_hk.replace(tzinfo=TZ_HONG_KONG)
    else:
        now_hk = now_hk.astimezone(TZ_HONG_KONG)
    pub_hk = now_hk - delta
    return pub_hk.astimezone(timezone.utc)


def _published_at_from_time_el(time_el, now_hk: datetime) -> datetime | None:
    """Obtém published_at a partir do elemento <time>: preferir datetime; senão, texto relativo (HK)."""
    dt_iso = time_el.get("datetime")
    if dt_iso:
        return _parse_datetime_attr(dt_iso)
    text = time_el.get_text(strip=True)
    return _parse_relative_time(text, now_hk)


def fetch_china_page() -> str:
    """Baixa o HTML da página China do SCMP."""
    r = requests.get(
        LIST_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_china_page(html: str) -> list[dict]:
    """
    Extrai artigos: título, url, summary, category, published_at.
    Headlines em span[data-qa="ContentHeadline-Headline"], resumo em h3[data-qa="ContentSummary-ContainerWithTag"],
    categoria em a[data-qa="BaseLink-renderAnchor-StyledAnchor"], time em time[data-qa="ContentActionBar-handleRenderDisplayDateTime-time"].
    Emparelha por índice; quando o texto do time for relativo, usa horário de Hong Kong no momento da coleta.
    """
    soup = BeautifulSoup(html, "html.parser")
    now_hk = datetime.now(TZ_HONG_KONG)

    headlines = soup.find_all("span", attrs={"data-qa": "ContentHeadline-Headline"})
    time_els = soup.find_all("time", attrs={"data-qa": "ContentActionBar-handleRenderDisplayDateTime-time"})

    articles = []
    n = min(len(headlines), len(time_els))
    seen_urls = set()

    for i in range(n):
        span = headlines[i]
        time_el = time_els[i]
        a = span.find_parent("a")
        if not a or not a.get("href"):
            continue
        href = a.get("href", "").strip()
        title = span.get_text(strip=True)
        if not title:
            continue
        url = _normalize_url(href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        published_at = _published_at_from_time_el(time_el, now_hk)
        if published_at and published_at.tzinfo:
            # Guardar em UTC como naive ISO para o banco (compatível com o resto do pipeline)
            published_at = published_at.astimezone(timezone.utc).replace(tzinfo=None)
        
        # Buscar resumo e categoria no mesmo container pai do link
        container = a.find_parent() if a else None
        summary = None
        category = "China"
        if container:
            summary_el = container.find("h3", attrs={"data-qa": "ContentSummary-ContainerWithTag"})
            if summary_el:
                summary = summary_el.get_text(strip=True)
            cat_link = container.find("a", attrs={"data-qa": "BaseLink-renderAnchor-StyledAnchor"})
            if cat_link:
                category = cat_link.get_text(strip=True) or "China"
        
        articles.append({
            "url": url,
            "title": title,
            "summary": summary,
            "category": category,
            "published_at": published_at,
            "author": None,
            "is_principal": False,
        })

    logger.info("SCMP China: parsed %d articles", len(articles))
    return articles


def collect_scmp_china() -> list[dict]:
    """Baixa a página China do SCMP e retorna artigos no formato do banco."""
    html = fetch_china_page()
    return parse_china_page(html)
