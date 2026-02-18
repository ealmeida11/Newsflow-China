# Configuração do projeto
import os

# Caminho do banco SQLite (raiz do projeto)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news.db")

# User-Agent para requests (evitar bloqueio)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
