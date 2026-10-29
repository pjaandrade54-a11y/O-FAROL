"""Casos do conselho humano como issues do GitHub, com a etiqueta "conselho".

O GitHub avisa por e-mail quem acompanha o repositório, então cada caso novo chega ao conselho sem
servidor de e-mail. Para decidir, o conselho põe no caso uma etiqueta com o rótulo final e fecha o caso;
a coleta seguinte lê a decisão e atualiza o site. Usa GITHUB_TOKEN e GITHUB_REPOSITORY, que o
GitHub Actions já fornece.
"""

import json
import os
import re
import urllib.error
import urllib.request

from .conselho import ROTULOS, texto_para_conselho

ETIQUETA = "conselho"
MARCA = re.compile(r"<!-- farol-link: (\S+) -->")


class ErroGitHub(RuntimeError):
    pass


def configurado():
    return bool(os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY"))


def _pedir(metodo, caminho, corpo=None):
    url = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{caminho}"
    pedido = urllib.request.Request(url, method=metodo, data=json.dumps(corpo).encode() if corpo else None, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raise ErroGitHub(f"GitHub respondeu {e.code} em {caminho}") from e
    except urllib.error.URLError as e:
        raise ErroGitHub(f"sem conexão com o GitHub ({e.reason})") from e


def casos_existentes(paginas=5):
    """{link da notícia: {"numero", "aberto", "rotulo"}} dos casos já abertos, para não repetir."""
    casos = {}
    for pagina in range(1, paginas + 1):
        lote = _pedir("GET", f"/issues?labels={ETIQUETA}&state=all&per_page=100&page={pagina}")
        for issue in lote:
            achado = MARCA.search(issue.get("body") or "")
            if not achado:
                continue
            etiquetas = [e["name"] for e in issue.get("labels", [])]
            rotulo = next((e for e in etiquetas if e in ROTULOS), None)
            casos.setdefault(achado.group(1), {"numero": issue["number"], "aberto": issue["state"] == "open", "rotulo": rotulo})
        if len(lote) < 100:
            break
    return casos


def garantir_etiquetas():
    """Cria a etiqueta "conselho" e uma etiqueta por rótulo, para o conselho marcar a decisão."""
    existentes = {e["name"] for e in _pedir("GET", "/labels?per_page=100")}
    novas = {ETIQUETA: ("1b2a5e", "Caso enviado ao conselho humano")}
    novas.update({r: ("d4c5a3", f"Decisão do conselho: {nome}") for r, nome in ROTULOS.items()})
    for nome, (cor, descricao) in novas.items():
        if nome not in existentes:
            _pedir("POST", "/labels", {"name": nome, "color": cor, "description": descricao})


def abrir_caso(analise):
    titulo = f"[Conselho] {analise['noticia']['titulo'][:200]}"
    issue = _pedir("POST", "/issues", {"title": titulo, "body": texto_para_conselho(analise), "labels": [ETIQUETA]})
    return issue["number"]


def decisoes(casos):
    """Casos fechados com um rótulo como etiqueta: {link: (número, rótulo)}."""
    return {link: (c["numero"], c["rotulo"]) for link, c in casos.items() if not c["aberto"] and c["rotulo"]}
