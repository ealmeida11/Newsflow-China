"""
Exporta artigos do banco para HTML.
Uso:
  python export_articles_html.py [--source globaltimes]           # todas as notícias coletadas
  python export_articles_html.py --source globaltimes --newsflow  # newsflow: principais + MORE últimas 24h
"""

import argparse
import html
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from db import get_connection, DB_PATH, get_newsflow_articles, get_last_scraped_at

# Horários exibidos no relatório em horário de Brasília
TZ_BR = ZoneInfo("America/Sao_Paulo")
from translate_news import translate_newsflow_rows


def _fmt_iso_datetime(iso: str | None) -> str:
    """Formata ISO datetime para exibição em Brasília: 18/02/2026 às 16:23."""
    if not iso:
        return ""
    try:
        s = iso.strip()[:19]
        if "T" in s:
            dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        else:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc).astimezone(TZ_BR)
        return dt.strftime("%d/%m/%Y às %H:%M")
    except (ValueError, TypeError):
        return iso[:16] if iso else ""


def _fmt_iso_date_only(iso: str | None) -> str:
    """Formata ISO para só data: 18/02/2026."""
    if not iso:
        return ""
    try:
        s = iso.strip()[:10]
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso[:10] if iso else ""


def _relative_time(iso: str | None) -> str:
    """Exibe hora em Brasília: '16:38' no mesmo dia, 'ontem 14:30' ou '17/02 10:00'."""
    if not iso:
        return ""
    try:
        s = iso.strip()[:19]
        if "T" in s:
            dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        else:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc).astimezone(TZ_BR)
        today = datetime.now(TZ_BR).date()
        if dt.date() == today:
            return dt.strftime("%H:%M")
        from datetime import timedelta
        if dt.date() == today - timedelta(days=1):
            return "ontem " + dt.strftime("%H:%M")
        return dt.strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return iso[:16] if iso else ""


def build_newsflow_html(
    source: str,
    hours: int,
    rows: list,
    last_scraped: str | None,
    generated_at: datetime,
    *,
    translated: bool = False,
) -> str:
    """Constrói HTML completo do newsflow diário (uma lista: últimas X horas)."""
    generated_at_br = generated_at.astimezone(TZ_BR) if generated_at.tzinfo else generated_at.replace(tzinfo=timezone.utc).astimezone(TZ_BR)
    generated_str = generated_at_br.strftime("%d/%m/%Y às %H:%M")
    last_update_str = _fmt_iso_datetime(last_scraped) if last_scraped else "—"

    html_escape = html.escape
    block = []

    block.append("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Newsflow China — Visão diária</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=DM+Serif+Display&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #fafafa;
      --surface: #ffffff;
      --text: #1a1a1a;
      --text-muted: #5c5c5c;
      --border: #e5e5e5;
      --accent: #0d47a1;
      --accent-soft: #e3f2fd;
      --principal-bg: #f5f5f5;
      --radius: 8px;
      --shadow: 0 1px 3px rgba(0,0,0,.06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
      font-size: 15px;
      line-height: 1.5;
      color: var(--text);
      background: var(--bg);
      min-height: 100vh;
    }
    .wrap { max-width: 720px; margin: 0 auto; padding: 24px 20px 48px; }
    .header {
      background: var(--surface);
      border-radius: var(--radius);
      padding: 24px 28px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
    }
    .header h1 {
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.75rem;
      font-weight: 400;
      margin: 0 0 8px 0;
      color: var(--text);
      letter-spacing: -0.02em;
    }
    .header .sub {
      font-size: 0.8125rem;
      color: var(--text-muted);
      margin-bottom: 16px;
    }
    .meta-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 20px 24px;
      font-size: 0.8125rem;
      color: var(--text-muted);
      padding-top: 16px;
      border-top: 1px solid var(--border);
    }
    .meta-bar strong { color: var(--text); font-weight: 500; }
    .stats {
      display: flex;
      gap: 16px;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    .stat {
      background: var(--accent-soft);
      color: var(--accent);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 500;
    }
    .section-title {
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.125rem;
      font-weight: 400;
      margin: 28px 0 12px 0;
      color: var(--text);
      letter-spacing: -0.01em;
    }
    .section-title:first-of-type { margin-top: 0; }
    .section-desc { font-size: 0.8125rem; color: var(--text-muted); margin: 0 0 16px 0; }
    .card {
      background: var(--surface);
      border-radius: var(--radius);
      padding: 18px 20px;
      margin-bottom: 12px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      transition: border-color .15s, box-shadow .15s;
    }
    .card:hover { border-color: #ccc; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
    .card.principal { background: var(--principal-bg); border-left: 3px solid var(--accent); }
    .card h2 {
      font-size: 1rem;
      font-weight: 600;
      margin: 0 0 8px 0;
      line-height: 1.35;
    }
    .card h2 a {
      color: var(--text);
      text-decoration: none;
    }
    .card h2 a:hover { color: var(--accent); text-decoration: underline; }
    .card .meta {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-bottom: 8px;
    }
    .card .meta span + span::before { content: " · "; color: var(--border); }
    .card .summary {
      font-size: 0.875rem;
      color: var(--text-muted);
      margin: 0;
      line-height: 1.45;
    }
    .card .summary:empty { display: none; }
    .footer {
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
      font-size: 0.75rem;
      color: var(--text-muted);
      text-align: center;
    }
    @media (max-width: 600px) {
      .wrap { padding: 16px 14px 32px; }
      .header { padding: 20px 18px; }
      .header h1 { font-size: 1.5rem; }
      .card { padding: 14px 16px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header class="header">
      <h1>Newsflow China</h1>
      <p class="sub">Visão diária — Global Times, seção China</p>
""" + (
      '      <p class="sub" style="color:var(--accent);font-weight:500;">Tradução automática para português (EN/ZH → PT)</p>\n'
      if translated else ""
    ) + """      <div class="stats">
        <span class="stat">""" + str(len(rows)) + """ últimas """ + str(hours) + """ h</span>
      </div>
      <div class="meta-bar">
        <span><strong>Última atualização dos dados:</strong> """ + html_escape(last_update_str) + (" (Brasília)" if last_update_str != "—" else "") + """</span>
        <span><strong>Janela:</strong> últimas """ + str(hours) + """ horas</span>
        <span><strong>Relatório gerado em:</strong> """ + html_escape(generated_str) + """ (Brasília)</span>
      </div>
    </header>
""")

    block.append("""
    <section aria-label="Últimas """ + str(hours) + """ horas">
      <h2 class="section-title">Últimas """ + str(hours) + """ horas</h2>
      <p class="section-desc">Notícias com data/hora nas últimas """ + str(hours) + """ horas.</p>
""")
    for r in rows:
        _, url, title_text, summary, category, published_at, author, _ = r
        title_s = html_escape((title_text or "").strip())
        summary_s = html_escape((summary or "").strip())
        if len(summary_s) > 320:
            summary_s = summary_s[:320] + "…"
        url_s = html_escape(url or "")
        time_str = _relative_time(published_at) or _fmt_iso_datetime(published_at)
        meta_parts = filter(None, [time_str, author, category])
        meta_s = " · ".join(meta_parts)
        block.append(f"""
      <article class="card">
        <h2><a href="{url_s}" target="_blank" rel="noopener">{title_s}</a></h2>
        <p class="meta"><span>{html_escape(meta_s)}</span></p>
        <p class="summary">{summary_s}</p>
      </article>""")
    block.append("    </section>")

    block.append("""
    <footer class="footer">
      Newsflow China · Relatório gerado em """ + html_escape(generated_str) + """ (Brasília) · Dados: Global Times (china/index)
    </footer>
  </div>
</body>
</html>""")
    return "\n".join(block)


def build_newsflow_html_all(
    sources_list: list[tuple[str, str]],
    hours: int,
    generated_at: datetime,
    *,
    translate: bool = True,
) -> tuple[str, int]:
    """
    Constrói HTML do newsflow para múltiplas fontes.
    sources_list: [(source_id, display_name), ...]
    Retorna (html, total_notícias).
    """
    generated_at_br = generated_at.astimezone(TZ_BR) if generated_at.tzinfo else generated_at.replace(tzinfo=timezone.utc).astimezone(TZ_BR)
    generated_str = generated_at_br.strftime("%d/%m/%Y às %H:%M")
    html_escape = html.escape

    # Coleta dados por fonte (e traduz se pedido)
    if translate and sources_list:
        print("Traduzindo títulos e resumos para português...")
    sections_data: list[tuple[str, str, list, str | None]] = []
    total_count = 0
    for source_id, display_name in sources_list:
        rows = get_newsflow_articles(source_id, hours=hours)
        if translate and rows:
            rows = translate_newsflow_rows(rows)
        last_scraped = get_last_scraped_at(source_id)
        sections_data.append((display_name, source_id, rows, last_scraped))
        total_count += len(rows)

    source_names = ", ".join(html_escape(name) for name, _, _, _ in sections_data)
    # Texto curto para meta: "Global Times, Xinhua e SCMP"
    sources_short = ", ".join(
        (name.split("—")[0].strip() if "—" in name else name.replace(" China-Biz", "").strip())
        for name, _, _, _ in sections_data
    )
    if len(sections_data) > 1:
        parts = sources_short.split(", ")
        sources_short = ", ".join(parts[:-1]) + " e " + parts[-1]

    block = []
    block.append("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Newsflow China — Visão diária</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=DM+Serif+Display&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #fafafa;
      --surface: #ffffff;
      --text: #1a1a1a;
      --text-muted: #5c5c5c;
      --border: #e5e5e5;
      --accent: #0d47a1;
      --accent-soft: #e3f2fd;
      --principal-bg: #f5f5f5;
      --radius: 8px;
      --shadow: 0 1px 3px rgba(0,0,0,.06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
      font-size: 15px;
      line-height: 1.5;
      color: var(--text);
      background: var(--bg);
      min-height: 100vh;
    }
    .wrap { max-width: 720px; margin: 0 auto; padding: 24px 20px 48px; }
    .header {
      background: var(--surface);
      border-radius: var(--radius);
      padding: 24px 28px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
    }
    .header h1 {
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.75rem;
      font-weight: 400;
      margin: 0 0 8px 0;
      color: var(--text);
      letter-spacing: -0.02em;
    }
    .header .sub {
      font-size: 0.8125rem;
      color: var(--text-muted);
      margin-bottom: 16px;
    }
    .meta-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 20px 24px;
      font-size: 0.8125rem;
      color: var(--text-muted);
      padding-top: 16px;
      border-top: 1px solid var(--border);
    }
    .meta-bar strong { color: var(--text); font-weight: 500; }
    .stats { display: flex; gap: 16px; margin-top: 12px; flex-wrap: wrap; }
    .stat {
      background: var(--accent-soft);
      color: var(--accent);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 500;
    }
    .source-section { margin-top: 32px; }
    .section-title {
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.125rem;
      font-weight: 400;
      margin: 28px 0 12px 0;
      color: var(--text);
      letter-spacing: -0.01em;
    }
    .section-title:first-of-type { margin-top: 0; }
    .section-desc { font-size: 0.8125rem; color: var(--text-muted); margin: 0 0 16px 0; }
    .card {
      background: var(--surface);
      border-radius: var(--radius);
      padding: 18px 20px;
      margin-bottom: 12px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
      transition: border-color .15s, box-shadow .15s;
    }
    .card:hover { border-color: #ccc; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
    .card.principal { background: var(--principal-bg); border-left: 3px solid var(--accent); }
    .card h2 { font-size: 1rem; font-weight: 600; margin: 0 0 8px 0; line-height: 1.35; }
    .card h2 a { color: var(--text); text-decoration: none; }
    .card h2 a:hover { color: var(--accent); text-decoration: underline; }
    .card .meta { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px; }
    .card .summary { font-size: 0.875rem; color: var(--text-muted); margin: 0; line-height: 1.45; }
    .card .summary:empty { display: none; }
    .footer {
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
      font-size: 0.75rem;
      color: var(--text-muted);
      text-align: center;
    }
    @media (max-width: 600px) {
      .wrap { padding: 16px 14px 32px; }
      .header { padding: 20px 18px; }
      .header h1 { font-size: 1.5rem; }
      .card { padding: 14px 16px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header class="header">
      <h1>Newsflow China</h1>
""" + (
      '      <p class="sub" style="color:var(--accent);font-weight:500;">Tradução automática para português (EN/ZH → PT)</p>\n'
      if translate else ""
    ) + """      <div class="stats">
        <span class="stat">""" + str(total_count) + """ notícias no total</span>
        <span class="stat">Janela: últimas """ + str(hours) + """ h</span>
      </div>
      <div class="meta-bar">
        <span><strong>Fontes:</strong> """ + html_escape(sources_short) + """</span>
        <span><strong>Atualizado em</strong> """ + html_escape(generated_str) + """</span>
      </div>
    </header>
""")

    for display_name, source_id, rows, last_scraped in sections_data:
        block.append(f"""
    <section class="source-section" aria-label=\"""" + html_escape(display_name) + """\">
      <h2 class="section-title">""" + html_escape(display_name) + """</h2>
      <p class="section-desc">""" + html_escape(_fmt_iso_datetime(last_scraped) if last_scraped else "—") + """ (última atualização)</p>
      <h3 class=\"section-title\" style=\"font-size:1rem;margin-top:16px;\">Últimas """ + str(hours) + """ horas</h3>
""")
        for r in rows:
            _, url, title_text, summary, category, published_at, author, _ = r
            title_s = html_escape((title_text or "").strip())
            summary_s = html_escape((summary or "").strip())
            if len(summary_s) > 320:
                summary_s = summary_s[:320] + "…"
            url_s = html_escape(url or "")
            time_str = _relative_time(published_at) or _fmt_iso_datetime(published_at)
            meta_parts = filter(None, [time_str, author, category])
            meta_s = " · ".join(meta_parts)
            block.append(f"""      <article class="card">
        <h2><a href="{url_s}" target="_blank" rel="noopener">{title_s}</a></h2>
        <p class="meta"><span>{html_escape(meta_s)}</span></p>
        <p class="summary">{summary_s}</p>
      </article>
""")
        block.append("    </section>")

    block.append("""
    <footer class="footer">
      Newsflow China · Atualizado em """ + html_escape(generated_str) + """ · Fontes: """ + source_names + """
    </footer>
  </div>
</body>
</html>""")
    return "\n".join(block), total_count


def export_newsflow_all(
    sources_list: list[tuple[str, str]],
    hours: int = 24,
    translate: bool = True,
) -> None:
    """Gera newsflow_diario.html com todas as fontes em sources_list [(source_id, display_name), ...]."""
    generated_at = datetime.now(timezone.utc)
    html_content, total = build_newsflow_html_all(sources_list, hours, generated_at, translate=translate)
    out_path = Path(DB_PATH).parent / "newsflow_diario.html"
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Exportado: {out_path} ({total} notícias)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="Filtrar por source (ex: globaltimes)")
    ap.add_argument("--newsflow", action="store_true", help="Modo newsflow: últimas X horas por fonte")
    ap.add_argument("--translate", action="store_true", help="Traduzir títulos e resumos para português (padrão no newsflow)")
    ap.add_argument("--no-translate", action="store_true", dest="no_translate", help="Não traduzir no newsflow")
    ap.add_argument("--hours", type=int, default=24, help="Janela em horas para MORE no newsflow (default 24)")
    args = ap.parse_args()
    source = args.source or "globaltimes"
    generated_at = datetime.now(timezone.utc)  # armazenado em UTC; exibição em Brasília

    if args.newsflow:
        rows = get_newsflow_articles(source, hours=args.hours)
        do_translate = not args.no_translate
        if do_translate and rows:
            print("Traduzindo títulos e resumos para português...")
            rows = translate_newsflow_rows(rows)
        last_scraped = get_last_scraped_at(source)
        html_content = build_newsflow_html(
            source, args.hours, rows, last_scraped, generated_at, translated=do_translate
        )
        out_path = Path(DB_PATH).parent / "newsflow_diario.html"
        out_path.write_text(html_content, encoding="utf-8")
        print(f"Exportado: {out_path} ({len(rows)} notícias)")
        return

    # Export simples (todas as notícias)
    conn = get_connection()
    rows = conn.execute(
        "SELECT source, url, title, summary, category, published_at, author FROM articles WHERE source = ? ORDER BY id DESC",
        (source,),
    ).fetchall()
    conn.close()
    out_path = Path(DB_PATH).parent / "noticias_coletadas.html"
    lines = [
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Notícias Coletadas</title>",
        "<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:900px;}",
        ".article{border-bottom:1px solid #eee;padding:1rem 0;} .article h3{margin:0 0 .5rem;}",
        ".meta{color:#666;font-size:.9rem;} a{color:#06c;}</style></head><body>",
        f"<h1>Notícias Coletadas ({len(rows)} itens)</h1>",
    ]
    for r in rows:
        source_, url, title_text, summary, category, published_at, author = r
        title_s = html.escape((title_text or "").strip())
        summary_s = html.escape((summary or "").strip())[:300]
        if (summary or "") and len(summary or "") > 300:
            summary_s += "..."
        url_s = html.escape(url or "")
        meta = " | ".join(filter(None, [
            published_at[:19].replace("T", " ") if published_at else None,
            author,
            category,
            source,
        ]))
        lines.append(
            f"<div class='article'>"
            f"<h3><a href='{url_s}' target='_blank' rel='noopener'>{title_s}</a></h3>"
            f"<p class='meta'>{html.escape(meta)}</p>"
            f"<p>{summary_s}</p>"
            f"</div>"
        )
    lines.append("</body></html>")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exportado: {out_path} ({len(rows)} notícias)")


if __name__ == "__main__":
    main()
