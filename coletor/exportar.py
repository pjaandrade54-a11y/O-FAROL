"""Exporta as notícias mais recentes para dados/noticias.json, que o site pode ler direto.

Um arquivo estático basta para o site: não é preciso servidor ligado o tempo todo.
"""

import json
import os

from .cadastro import RAIZ
from .coleta import agora

ARQUIVO = RAIZ / "dados" / "noticias.json"
POR_ESCALA = 30
ESCALAS = ("cidade", "estado", "pais", "mundo")


def exportar(conexao, veiculos, arquivo=ARQUIVO, por_escala=POR_ESCALA):
    nomes = {v["id"]: v["nome"] for v in veiculos}
    saida = {
        "gerado_em": agora(),
        "veiculos": [
            {"id": v["id"], "nome": v["nome"], "tipo": v["tipo"], "abrangencia": v["abrangencia"], "uf": v.get("uf")}
            for v in veiculos if v.get("ativo", True)
        ],
        "escalas": {},
        "checagens": [],
    }

    def consultar(onde, parametros):
        return conexao.execute(
            f"SELECT * FROM noticias WHERE {onde} ORDER BY COALESCE(publicado_em, coletado_em) DESC LIMIT ?",
            (*parametros, por_escala),
        ).fetchall()

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
        }

    for escala in ESCALAS:
        saida["escalas"][escala] = [item(l) for l in consultar("uso = 'noticias' AND escala = ?", (escala,))]
    saida["checagens"] = [item(l) for l in consultar("uso = 'checagens'", ())]

    temporario = arquivo.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8", newline="\n") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    os.replace(temporario, arquivo)

    contagem = {escala: len(lista) for escala, lista in saida["escalas"].items()}
    contagem["checagens"] = len(saida["checagens"])
    return contagem
