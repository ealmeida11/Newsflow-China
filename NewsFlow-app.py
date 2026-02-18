"""
NewsFlow-app: um único run que coleta todas as fontes e atualiza o HTML.

Uso: python NewsFlow-app.py

- Roda todos os coletores (Global Times China, Xinhua China-Biz, etc.)
- Grava artigos no banco SQLite
- Gera newsflow_diario.html com todas as fontes (tradução para PT por padrão)
"""

import logging
import sys

from db import init_db, insert_articles_batch
from sources.globaltimes import collect_globaltimes_china
from sources.xinhua_chinabiz import collect_xinhua_chinabiz
from sources.scmp_china import collect_scmp_china
from export_articles_html import export_newsflow_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# (source_id, display_name, collect_function)
SOURCES = [
    ("globaltimes", "Global Times — China", collect_globaltimes_china),
    ("xinhua_chinabiz", "Xinhua China-Biz", collect_xinhua_chinabiz),
    ("scmp_china", "SCMP — China", collect_scmp_china),
]


def main():
    logger.info("NewsFlow-app: iniciando coleta de todas as fontes")
    init_db()

    for source_id, display_name, collect_fn in SOURCES:
        try:
            logger.info("Coletando: %s", display_name)
            articles = collect_fn()
            if not articles:
                logger.warning("  Nenhum artigo: %s", display_name)
                continue
            n = insert_articles_batch(source_id, articles)
            logger.info("  Salvos %d artigos (%s)", n, source_id)
        except Exception as e:
            logger.exception("  Erro ao coletar %s: %s", display_name, e)

    logger.info("Gerando newsflow_diario.html (todas as fontes, tradução PT)...")
    sources_for_export = [(sid, name) for sid, name, _ in SOURCES]
    export_newsflow_all(sources_for_export, hours=24, translate=True)
    logger.info("NewsFlow-app: concluído")


if __name__ == "__main__":
    main()
