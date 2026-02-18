# Newsflow China

Monitor de notícias sobre China para economistas: coleta de múltiplas fontes, tradução para português e relatório HTML (últimas 24h).

## Fontes

- **Global Times** — seção China
- **Xinhua** — China-Biz
- **SCMP** — China

## Uso

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar coleta de todas as fontes e gerar o relatório
python NewsFlow-app.py
```

Gera `newsflow_diario.html` na pasta do projeto (horários em Brasília, tradução EN/ZH → PT).

## Estrutura

| Arquivo / pasta      | Função |
|----------------------|--------|
| `NewsFlow-app.py`    | Ponto único: coleta todas as fontes e atualiza o HTML |
| `db.py`              | SQLite (artigos, newsflow) |
| `config.py`          | Caminho do banco, User-Agent |
| `export_articles_html.py` | Geração do HTML multi-fonte e tradução |
| `translate_news.py`  | Tradução para português (deep-translator) |
| `list_articles.py`  | Listar artigos no terminal (debug) |
| `sources/`           | Um módulo por fonte: `globaltimes.py`, `xinhua_chinabiz.py`, `scmp_china.py` |

## Requisitos

- Python 3.9+
- `requests`, `beautifulsoup4`, `deep-translator`
