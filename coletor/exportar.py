"""Exporta as notícias mais recentes para dados/noticias.json, que o site pode ler direto.

Um arquivo estático basta para o site: não é preciso servidor ligado o tempo todo.
"""

import json
import os

from . import selecao
from .cadastro import RAIZ
from .coleta import agora
from .conselho import carregar_analises

ARQUIVO = RAIZ / "dados" / "noticias.json"
ESCALAS = ("cidade", "estado", "pais", "mundo")


def exportar(conexao, veiculos, arquivo=ARQUIVO, cidades=()):
    nomes = {v["id"]: v["nome"] for v in veiculos}
    analises = carregar_analises(conexao)
    saida = {
        "gerado_em": agora(),
        "veiculos": [
            {"id": v["id"], "nome": v["nome"], "tipo": v["tipo"], "abrangencia": v["abrangencia"], "uf": v.get("uf")}
            for v in veiculos if v.get("ativo", True)
        ],
        # Cidades que o leitor pode escolher (com coordenadas, para "Usar minha localização")
        "cidades": [{k: c[k] for k in ("nome", "uf", "lat", "lon") if k in c}
                    for c in sorted(cidades, key=lambda c: (c["nome"], c["uf"]))],
        "escalas": {},
        "checagens": [],
    }

    def item(linha):
        return {
            "id": linha["id"],
            "titulo": linha["titulo"],
            "link": linha["link"],
            "resumo": linha["resumo"],
            "veiculo_id": linha["veiculo_id"],
            "veiculo": nomes.get(linha["veiculo_id"], linha["veiculo_id"]),
            "publicado_em": linha["publicado_em"],
            "uf": linha["uf"],
            "cidade": linha["cidade"],
            "analise": analises.get(linha["link"]),
        }

    t = selecao.listas(conexao)
    for escala in ESCALAS:
        saida["escalas"][escala] = [item(l) for l in t[escala]]
    saida["checagens"] = [item(l) for l in t["checagens"]]

    temporario = arquivo.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8", newline="\n") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    os.replace(temporario, arquivo)

    contagem = {escala: len(lista) for escala, lista in saida["escalas"].items()}
    contagem["checagens"] = len(saida["checagens"])
    return contagem
