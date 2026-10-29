"""Banco SQLite (um arquivo só, sem servidor) com as notícias e o estado de cada feed."""

import sqlite3

from .cadastro import RAIZ

ARQUIVO = RAIZ / "dados" / "farol.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS noticias (
  id INTEGER PRIMARY KEY,
  veiculo_id TEXT NOT NULL,
  titulo TEXT NOT NULL,
  link TEXT NOT NULL UNIQUE,
  guid TEXT,
  resumo TEXT,
  autor TEXT,
  publicado_em TEXT,
  coletado_em TEXT NOT NULL,
  escala TEXT NOT NULL,
  uso TEXT NOT NULL DEFAULT 'noticias',
  uf TEXT,
  cidade TEXT,
  cidades TEXT
);
CREATE INDEX IF NOT EXISTS noticias_escala_data ON noticias (uso, escala, publicado_em DESC);

CREATE TABLE IF NOT EXISTS feeds (
  url TEXT PRIMARY KEY,
  veiculo_id TEXT NOT NULL,
  etag TEXT,
  modificado TEXT,
  ultima_coleta TEXT,
  ultimo_status TEXT,
  ultimo_erro TEXT,
  falhas_seguidas INTEGER NOT NULL DEFAULT 0
);

-- Pareceres do conselho de IA, um por notícia (pelo link, que sobrevive a uma recoleta)
CREATE TABLE IF NOT EXISTS analises (
  link TEXT PRIMARY KEY,
  analisado_em TEXT NOT NULL,
  rotulo TEXT NOT NULL,
  destino TEXT NOT NULL,
  dados TEXT NOT NULL,
  issue INTEGER
);
"""


def abrir(arquivo=ARQUIVO):
    if arquivo != ":memory:":
        arquivo.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(arquivo)
    conexao.row_factory = sqlite3.Row
    conexao.executescript(ESQUEMA)
    # Banco criado antes da coluna "cidades" (todas as cidades citadas, em JSON): acrescenta a coluna
    colunas = {c["name"] for c in conexao.execute("PRAGMA table_info(noticias)")}
    if "cidades" not in colunas:
        conexao.execute("ALTER TABLE noticias ADD COLUMN cidades TEXT")
    return conexao
