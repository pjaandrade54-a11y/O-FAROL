"""Cadastro de veículos: lê, valida e grava dados/veiculos.json.

Campos de transparência e certificações começam como null, que quer dizer "ainda não verificado".
A linha editorial só é preenchida com o que o próprio veículo declara.
"""

import json
import os
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "dados" / "veiculos.json"
ARQUIVO_CIDADES = RAIZ / "dados" / "cidades.json"

TIPOS = {"agencia", "jornal", "portal", "revista", "radio", "tv", "blog", "checador"}

# Abrangência do veículo -> aba da página inicial onde as notícias dele aparecem
ABRANGENCIAS = {"local": "cidade", "estadual": "estado", "nacional": "pais", "internacional": "mundo"}
ESCALAS = set(ABRANGENCIAS.values())
USOS = {"noticias", "checagens"}

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ErroCadastro(ValueError):
    pass


def novo_veiculo(id, nome, site, tipo, abrangencia, feeds, grupo=None, uf=None, cidade=None):
    return {
        "id": id,
        "nome": nome,
        "site": site,
        "tipo": tipo,
        "abrangencia": abrangencia,
        "uf": uf,
        "cidade": cidade,
        "grupo": grupo,
        "linha_declarada": "não declarada",
        "feeds": feeds,
        "transparencia": {
            "dono": None,
            "cnpj": None,
            "expediente_publicado": None,
            "politica_correcoes": None,
            "separa_opiniao_publicidade": None,
        },
        "certificacoes": {"ifcn": None, "jti": None, "trust_project": None},
        "ativo": True,
        "observacoes": "",
    }


def validar(veiculos):
    """Devolve a lista de problemas encontrados; lista vazia quer dizer cadastro válido."""
    erros = []
    ids = set()
    for posicao, v in enumerate(veiculos, start=1):
        rotulo = v.get("id") or f"veículo {posicao}"

        def erro(msg):
            erros.append(f"{rotulo}: {msg}")

        if not SLUG.match(v.get("id") or ""):
            erro("o id deve ter só letras minúsculas, números e hífens (ex.: gazeta-aurora)")
        elif v["id"] in ids:
            erro("id repetido")
        ids.add(v.get("id"))

        if not v.get("nome"):
            erro("falta o nome")
        if v.get("tipo") not in TIPOS:
            erro("tipo deve ser um destes: " + ", ".join(sorted(TIPOS)))
        if v.get("abrangencia") not in ABRANGENCIAS:
            erro("abrangência deve ser uma destas: " + ", ".join(ABRANGENCIAS))
        if v.get("abrangencia") in ("local", "estadual") and v.get("uf") not in UFS:
            erro("veículo local ou estadual precisa da UF (ex.: PE)")
        if v.get("abrangencia") == "local" and not v.get("cidade"):
            erro("veículo local precisa da cidade")

        feeds = v.get("feeds")
        if not isinstance(feeds, list) or not feeds:
            erro("precisa de ao menos um feed")
            continue
        for f in feeds:
            url = str(f.get("url", ""))
            if not url.startswith(("https://", "http://")):
                erro(f"feed com endereço inválido: {url or '(vazio)'}")
            if f.get("escala") not in (None, *ESCALAS):
                erro(f"escala do feed deve ser uma destas: {', '.join(sorted(ESCALAS))}")
            if f.get("uso", "noticias") not in USOS:
                erro("uso do feed deve ser noticias ou checagens")
    return erros


def carregar(arquivo=ARQUIVO):
    with open(arquivo, encoding="utf-8") as f:
        veiculos = json.load(f)["veiculos"]
    erros = validar(veiculos)
    if erros:
        raise ErroCadastro("O cadastro de veículos tem problemas:\n- " + "\n- ".join(erros))
    return veiculos


def gravar(veiculos, arquivo=ARQUIVO):
    erros = validar(veiculos)
    if erros:
        raise ErroCadastro("O cadastro não foi gravado:\n- " + "\n- ".join(erros))
    arquivo = Path(arquivo)
    temporario = arquivo.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"versao": 1, "veiculos": sorted(veiculos, key=lambda v: v["id"])}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(temporario, arquivo)


def buscar(veiculos, id):
    for v in veiculos:
        if v["id"] == id:
            return v
    raise ErroCadastro(f"Nenhum veículo com o id {id}.")


def carregar_cidades(arquivo=ARQUIVO_CIDADES):
    """Cidades cujas notícias vão para a aba Cidade quando o nome aparece no título ou no resumo."""
    try:
        with open(arquivo, encoding="utf-8") as f:
            cidades = json.load(f)["cidades_monitoradas"]
    except FileNotFoundError:
        return []
    for c in cidades:
        if not c.get("nome") or c.get("uf") not in UFS:
            raise ErroCadastro(f"Cidade monitorada inválida em {Path(arquivo).name}: {c}")
    return cidades


def escala_do_feed(veiculo, feed):
    return feed.get("escala") or ABRANGENCIAS[veiculo["abrangencia"]]
