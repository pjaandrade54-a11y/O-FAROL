"""Foto das notícias do site que vieram sem foto no feed: lê a página da matéria e usa a imagem
de compartilhamento que o próprio veículo declarou (og:image ou twitter:image).

Cada página é lida uma vez só: sem foto, a notícia fica marcada com "" e não é procurada de novo.
"""

import html
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import feeds

LIMITE_BYTES = 600_000
META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
ATRIBUTO = re.compile(r"""([a-z:_-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
NOMES = ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src")


def imagem_da_pagina(texto):
    """A imagem de compartilhamento declarada nas tags <meta> da página, ou None."""
    achadas = {}
    for tag in META.findall(texto):
        atributos = {a.lower(): (v1 or v2) for a, v1, v2 in ATRIBUTO.findall(tag)}
        nome = (atributos.get("property") or atributos.get("name") or "").lower()
        if nome in NOMES and atributos.get("content"):
            achadas.setdefault(nome, html.unescape(atributos["content"].strip()))
    for nome in NOMES:
        url = achadas.get(nome, "")
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http://"):
            url = "https://" + url[7:]
        if url.startswith("https://") and len(url) < 1000:
            return url
    return None


def _baixar_pagina(link, tempo_limite=8):
    pedido = urllib.request.Request(link, headers={"User-Agent": feeds.AGENTE, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(pedido, timeout=tempo_limite, context=feeds._TLS) as r:
            # As tags <meta> ficam no começo da página; não precisa baixar tudo
            return r.read(LIMITE_BYTES).decode(r.headers.get_content_charset() or "utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def completar(conexao, links, limite=150, simultaneos=12, baixar=_baixar_pagina):
    """Procura a foto das notícias (pelos links) que ainda não têm, das mais novas para as mais antigas.
    Devolve quantas fotos achou."""
    if not links:
        return 0
    marcas = ",".join("?" * len(links))
    faltam = [l["link"] for l in conexao.execute(
        f"SELECT link FROM noticias WHERE imagem IS NULL AND link IN ({marcas}) "
        "ORDER BY COALESCE(publicado_em, coletado_em) DESC LIMIT ?", (*links, limite))]

    def procurar(link):
        pagina = baixar(link)
        return link, (imagem_da_pagina(pagina) if pagina else None), pagina is not None

    achadas = 0
    with ThreadPoolExecutor(max_workers=simultaneos) as grupo:
        for link, imagem, respondeu in grupo.map(procurar, faltam):
            if imagem:
                achadas += 1
            if imagem or respondeu:  # site fora do ar: tenta de novo na próxima execução
                conexao.execute("UPDATE noticias SET imagem = ? WHERE link = ?", (imagem or "", link))
    conexao.commit()
    return achadas
