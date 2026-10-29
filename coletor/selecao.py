"""Quais notícias vão para o site: as mais recentes de cada cidade, de cada estado, do país e do mundo.

Usado pela exportação (dados/noticias.json) e pela análise por regras, que rotula tudo o que vai para o site.
"""

POR_CIDADE = 8
POR_ESTADO = 8
POR_PAIS = 30
POR_MUNDO = 20
POR_CHECAGENS = 30

_DATA = "COALESCE(publicado_em, coletado_em)"


def _por_grupo(conexao, onde, grupo, limite):
    return conexao.execute(
        f"""SELECT * FROM (
              SELECT *, ROW_NUMBER() OVER (PARTITION BY {grupo} ORDER BY {_DATA} DESC) AS posicao
              FROM noticias WHERE {onde})
            WHERE posicao <= ? ORDER BY {_DATA} DESC""",
        (limite,),
    ).fetchall()


def _mais_recentes(conexao, onde, limite):
    return conexao.execute(f"SELECT * FROM noticias WHERE {onde} ORDER BY {_DATA} DESC LIMIT ?", (limite,)).fetchall()


def listas(conexao):
    """{"cidade": [...], "estado": [...], "pais": [...], "mundo": [...], "checagens": [...]} com as linhas do banco."""
    return {
        # Inclui notícias nacionais que citam a cidade: elas aparecem na aba País e na aba Cidade
        "cidade": _por_grupo(conexao, "uso = 'noticias' AND cidade IS NOT NULL", "cidade, uf", POR_CIDADE),
        "estado": _por_grupo(conexao, "uso = 'noticias' AND escala = 'estado' AND uf IS NOT NULL", "uf", POR_ESTADO),
        "pais": _mais_recentes(conexao, "uso = 'noticias' AND escala = 'pais'", POR_PAIS),
        "mundo": _mais_recentes(conexao, "uso = 'noticias' AND escala = 'mundo'", POR_MUNDO),
        "checagens": _mais_recentes(conexao, "uso = 'checagens'", POR_CHECAGENS),
    }


def noticias_do_site(conexao):
    """Todas as notícias que aparecem no site, sem repetir, das mais novas para as mais antigas."""
    vistas, saida = set(), []
    t = listas(conexao)
    for linha in sorted(t["cidade"] + t["estado"] + t["pais"] + t["mundo"],
                        key=lambda l: l["publicado_em"] or l["coletado_em"] or "", reverse=True):
        if linha["link"] not in vistas:
            vistas.add(linha["link"])
            saida.append(linha)
    return saida
