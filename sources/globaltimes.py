"""
Coletor do Global Times - seção China.
URL: https://www.globaltimes.cn/china/index.html

Extrai por artigo: título, URL, resumo, tema/categoria, data e hora, autor.
Para artigos do topo (form1, form2, etc.) que não têm data na listagem, entra na página
do artigo e obtém a data de <span class="pub_time">Published: Feb 17, 2026 10:37 AM</span>.
"""

import re
import time
import logging
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import USER_AGENT

logger = logging.getLogger(__name__)

BASE_URL = "https://www.globaltimes.cn"
CHINA_INDEX_URL = "https://www.globaltimes.cn/china/index.html"
FETCH_ARTICLE_DELAY = 0.4  # segundos entre requests às páginas de artigo


def _parse_source_time(text: str) -> tuple[str | None, datetime | None]:
    """
    Parse 'By Author  |  2026/2/18 21:38:48' -> (author, datetime).
    """
    if not text or not text.strip():
        return None, None
    text = text.strip()
    parts = re.split(r"\s*\|\s*", text, maxsplit=1)
    author = None
    if parts:
        author = parts[0].strip()
        if author.lower().startswith("by "):
            author = author[3:].strip()
        if author.lower().startswith("by "):
            author = author[3:].strip()
    pub_dt = None
    if len(parts) > 1:
        date_str = parts[1].strip()
        try:
            pub_dt = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            try:
                pub_dt = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
            except ValueError:
                pass
    return author or None, pub_dt


def _normalize_url(href: str) -> str:
    if not href:
        return ""
    return urljoin(BASE_URL, href.strip()).split("?")[0]


def fetch_china_index() -> str:
    """Baixa o HTML da página China do Global Times."""
    r = requests.get(
        CHINA_INDEX_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def fetch_article_page(url: str) -> str:
    """Baixa o HTML de uma página de artigo (para obter pub_time)."""
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_pub_time_from_article(html: str) -> datetime | None:
    """
    Extrai data/hora de <span class="pub_time">Published: Feb 17, 2026 10:37 AM</span>.
    Retorna None se não encontrar ou falhar o parse.
    """
    soup = BeautifulSoup(html, "html.parser")
    span = soup.find("span", class_="pub_time")
    if not span:
        return None
    text = span.get_text(strip=True)
    if not text:
        return None
    # "Published: Feb 17, 2026 10:37 AM"
    prefix = "Published: "
    if text.startswith(prefix):
        text = text[len(prefix) :].strip()
    try:
        return datetime.strptime(text, "%b %d, %Y %I:%M %p")
    except ValueError:
        try:
            return datetime.strptime(text, "%B %d, %Y %I:%M %p")  # February
        except ValueError:
            return None


def fill_published_at_for_principals(articles: list[dict]) -> None:
    """
    Para cada artigo com is_principal=True e sem published_at, acessa a URL do artigo,
    extrai pub_time e preenche published_at. Altera a lista in-place.
    """
    for a in articles:
        if not a.get("is_principal") or a.get("published_at") is not None:
            continue
        url = a.get("url")
        if not url:
            continue
        try:
            time.sleep(FETCH_ARTICLE_DELAY)
            html = fetch_article_page(url)
            pub_dt = parse_pub_time_from_article(html)
            if pub_dt is not None:
                a["published_at"] = pub_dt
                logger.debug("pub_time %s -> %s", url[:50], pub_dt)
        except Exception as e:
            logger.warning("Falha ao obter pub_time de %s: %s", url[:60], e)


def parse_china_index(html: str) -> list[dict]:
    """
    Extrai da página China todos os artigos com:
    title, url, summary, category, published_at, author.
    Coleta TODAS as seções visíveis na página.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles: list[dict] = []
    seen_urls: set[str] = set()

    def add(url: str, title: str, summary: str | None = None, category: str | None = None, published_at: datetime | None = None, author: str | None = None, is_principal: bool = False):
        url = _normalize_url(url)
        if not url or not title or url in seen_urls:
            return
        seen_urls.add(url)
        articles.append({
            "url": url,
            "title": title.strip(),
            "summary": summary.strip() if summary else None,
            "category": category.strip() if category else None,
            "published_at": published_at,
            "author": author.strip() if author else None,
            "is_principal": is_principal,
        })

    # Notícias principais (fora da MORE): form1, form2, form3, form4, mid_elem, content_bottom
    # Essas vêm primeiro no newsflow e não têm filtro de 24h.

    # 1) FORM1 - Feature principal (topo esquerdo)
    for form1 in soup.find_all("div", class_="china_article_form1"):
        link = form1.find("a", class_="new_title_ml") or form1.find("a", href=re.compile(r"/page/"))
        if link:
            title = link.get_text(strip=True)
            url = link.get("href")
            p = form1.find("p")
            summary = p.get_text(strip=True) if p else None
            if title and url:
                add(url, title, summary=summary, is_principal=True)

    # 2) FORM2 - Artigo com imagem (abaixo do form1)
    for form2 in soup.find_all("div", class_="china_article_form2"):
        link = form2.find("a", class_="new_title_ms") or form2.find("a", href=re.compile(r"/page/"))
        if link:
            title = link.get_text(strip=True)
            url = link.get("href")
            desc = form2.find("div", class_="form2_desc")
            summary = desc.find("p").get_text(strip=True) if desc and desc.find("p") else None
            if title and url:
                add(url, title, summary=summary, is_principal=True)

    # 3) FORM3 - Artigo simples (abaixo do form2)
    for form3 in soup.find_all("div", class_="china_article_form3"):
        link = form3.find("a", class_="new_title_ms") or form3.find("a", href=re.compile(r"/page/"))
        if link:
            title = link.get_text(strip=True)
            url = link.get("href")
            p = form3.find("p")
            summary = p.get_text(strip=True) if p else None
            if title and url:
                add(url, title, summary=summary, is_principal=True)

    # 4) FORM4 + MID_ELEM - Seções com categoria (MILITARY, CHINA GRAPHIC, DIPLOMACY)
    china_content = soup.find("div", class_="china_content")
    if china_content:
        current_category = None
        for elem in china_content.find_all(["div"], recursive=True):
            classes = elem.get("class", [])
            if "column_title" in classes:
                a = elem.find("a")
                if a:
                    current_category = a.get_text(strip=True)
                continue
            if "china_article_form4" in classes:
                title_link = elem.find("a", class_="new_title_ms")
                if not title_link:
                    title_link = elem.find("a", href=re.compile(r"/page/"))
                if title_link and title_link.get("href"):
                    title = title_link.get_text(strip=True)
                    if not title:
                        title = (title_link.get("title") or "").strip()
                    if title:
                        p = elem.find("p")
                        summary = p.get_text(strip=True) if p else None
                        add(title_link.get("href"), title, summary=summary, category=current_category, is_principal=True)
            elif "mid_elem" in classes:
                mid_title = elem.find("div", class_="mid_title")
                link = mid_title.find("a") if mid_title else elem.find("a", href=re.compile(r"/page/"))
                if link and link.get("href"):
                    title = link.get_text(strip=True)
                    url = link.get("href")
                    mid_desc = elem.find("div", class_="mid_desc")
                    summary = mid_desc.get_text(strip=True) if mid_desc else None
                    if title:
                        add(url, title, summary=summary, category=current_category, is_principal=True)

    # 5) CONTENT_BOTTOM - Lista de artigos menores (4 itens)
    content_bottom = soup.find("div", class_="content_bottom")
    if content_bottom:
        for li in content_bottom.find_all("li"):
            link = li.find("a", class_="new_title_ss") or li.find("a", href=re.compile(r"/page/"))
            if link and link.get("href"):
                title = link.get_text(strip=True)
                if title:
                    add(link.get("href"), title, is_principal=True)

    # 6) LIST_CONTENT (MORE) - Lista com autor e data; no newsflow só últimas 24h
    list_content = soup.find("div", class_="list_content")
    if list_content:
        level01 = list_content.find("div", class_="level01_list")
        ul = (level01.find("ul") if level01 else list_content.find("ul")) or list_content
        for li in ul.find_all("li"):
            info = li.find("div", class_="list_info")
            if not info:
                continue
            link = info.find("a", class_="new_title_ms") or info.find("a", href=re.compile(r"/page/"))
            if not link:
                continue
            title = link.get_text(strip=True)
            url = link.get("href")
            p = info.find("p")
            summary = p.get_text(strip=True) if p else None
            source_time = info.find("div", class_="source_time")
            author, published_at = None, None
            if source_time:
                author, published_at = _parse_source_time(source_time.get_text())
            if title and url:
                add(url, title, summary=summary, published_at=published_at, author=author, is_principal=False)

    logger.info("Global Times China: parsed %d articles from all sections", len(articles))

    # Preencher published_at dos principais entrando na página de cada um (pub_time)
    principals_without_date = [a for a in articles if a.get("is_principal") and a.get("published_at") is None]
    if principals_without_date:
        logger.info("Buscando data de publicação em %d artigos (página do link)...", len(principals_without_date))
        fill_published_at_for_principals(articles)

    return articles


def collect_globaltimes_china() -> list[dict]:
    """Baixa a página China do Global Times e retorna lista de artigos (com published_at quando possível)."""
    html = fetch_china_index()
    return parse_china_index(html)
