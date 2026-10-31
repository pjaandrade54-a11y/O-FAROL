"""Exporta as notícias mais recentes em arquivos estáticos que o site lê direto, sem servidor:

- dados/noticias.json: país, mundo, checagens, veículos e a lista de cidades (todo leitor baixa);
- dados/estados/UF.json: as notícias das cidades e do estado (o leitor baixa só o do estado escolhido).
"""

import json
import os
from pathlib import Path

from . import selecao
from .cadastro import RAIZ, UFS
from .coleta import agora
from .conselho import carregar_analises

ARQUIVO = RAIZ / "dados" / "noticias.json"
GERAIS = ("pais", "mundo")
POR_ESTADO = ("cidade", "estado")


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
        analise = analises.get(linha["link"])
        saida_item = {
            "id": linha["id"],
            "titulo": linha["titulo"],
            "link": linha["link"],
            "resumo": linha["resumo"],
            "veiculo_id": linha["veiculo_id"],
            "veiculo": nomes.get(linha["veiculo_id"], linha["veiculo_id"]),
            "publicado_em": linha["publicado_em"],
            "uf": _da_lista(linha, "uf"),
            "cidade": _da_lista(linha, "cidade"),
            "analise": analise,
        }
        # A foto que o veículo anexou (ou a de compartilhamento da página da matéria)
        if linha["imagem"]:
            saida_item["imagem"] = linha["imagem"]
        return saida_item

    t = selecao.listas(conexao)
    for escala in GERAIS:
        saida["escalas"][escala] = [item(l) for l in t[escala]]
    saida["checagens"] = [item(l) for l in t["checagens"]]
    _gravar(arquivo, saida)

    # Um arquivo por estado, sempre os 27: um estado que ficou sem notícias não guarda as antigas
    pasta = Path(arquivo).parent / "estados"
    pasta.mkdir(exist_ok=True)
    contagem = {escala: len(saida["escalas"][escala]) for escala in GERAIS}
    contagem.update({escala: 0 for escala in POR_ESTADO})
    for uf in sorted(UFS):
        estado = {"gerado_em": saida["gerado_em"], "uf": uf, "escalas": {}}
        for escala in POR_ESTADO:
            estado["escalas"][escala] = [item(l) for l in t[escala] if _da_lista(l, "uf") == uf]
            contagem[escala] += len(estado["escalas"][escala])
        _gravar(pasta / f"{uf}.json", estado)
    contagem["checagens"] = len(saida["checagens"])
    return contagem


def _da_lista(linha, campo):
    """Na lista de cidades, cada linha vale para uma das cidades citadas (cidade_lista, uf_lista)."""
    chave = campo + "_lista"
    return linha[chave] if chave in linha.keys() else linha[campo]


def _gravar(arquivo, dados):
    arquivo = Path(arquivo)
    temporario = arquivo.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(temporario, arquivo)
