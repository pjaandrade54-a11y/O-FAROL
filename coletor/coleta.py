"""Coleta: passa pelos feeds dos veículos ativos e guarda só as notícias novas."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from . import feeds as leitor
from .cadastro import escala_do_feed


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_confiavel(publicado_em, momento):
    """Alguns feeds publicam datas no futuro; nesse caso vale a hora da coleta."""
    limite = (datetime.fromisoformat(momento) + timedelta(minutes=15)).isoformat(timespec="seconds")
    if publicado_em and publicado_em > limite:
        return momento
    return publicado_em


def cidades_citadas(item, veiculo, cidades):
    """Cidades monitoradas citadas no título ou resumo, na ordem em que aparecem. Veículos estaduais e
    locais só contam cidades do seu estado; cidades de nome ambíguo só contam em veículos do mesmo estado.
    O nome mais longo vence: "Juazeiro do Norte" não conta também como "Juazeiro"."""
    texto = f"{item['titulo']} {item['resumo']}"
    achadas = []
    for c in cidades:  # já vêm das de nome mais longo para as mais curtas
        mesmo_estado = c["uf"] == veiculo.get("uf")
        if (veiculo["abrangencia"] in ("estadual", "local") or c.get("ambigua")) and not mesmo_estado:
            continue
        padrao = re.compile(r"\b" + re.escape(c["nome"]) + r"\b", re.IGNORECASE)
        posicao = padrao.search(texto)
        if posicao:
            achadas.append((posicao.start(), c))
            texto = padrao.sub(lambda m: " " * len(m.group(0)), texto)  # não deixa um nome menor casar dentro dele
    return [c for _, c in sorted(achadas, key=lambda x: x[0])]


def cidade_citada(item, veiculo, cidades):
    """A primeira cidade monitorada citada, ou None."""
    achadas = cidades_citadas(item, veiculo, cidades)
    return achadas[0] if achadas else None


def coletar(conexao, veiculos, so_veiculo=None, aviso=print, cidades=(), simultaneos=12):
    resumo = {"feeds": 0, "novas": 0, "sem_mudanca": 0, "erros": 0}
    pedidos = []
    for v in veiculos:
        if not v.get("ativo", True) or (so_veiculo and v["id"] != so_veiculo):
            continue
        for feed in v["feeds"]:
            estado = conexao.execute("SELECT etag, modificado FROM feeds WHERE url = ?", (feed["url"],)).fetchone()
            pedidos.append((v, feed, estado["etag"] if estado else None, estado["modificado"] if estado else None))

    # Baixa vários feeds ao mesmo tempo (um site lento não segura os outros); grava um de cada vez
    def baixar(pedido):
        v, feed, etag, modificado = pedido
        try:
            return pedido, leitor.baixar(feed["url"], etag, modificado), None
        except leitor.ErroFeed as e:
            return pedido, None, e

    with ThreadPoolExecutor(max_workers=simultaneos) as grupo:
        for (v, feed, _, _), resposta, erro in grupo.map(baixar, pedidos):
            resumo["feeds"] += 1
            url = feed["url"]
            try:
                if erro:
                    raise erro
                if resposta.status == 304:
                    resumo["sem_mudanca"] += 1
                    aviso(f"  {v['nome']}: nada novo desde a última coleta")
                else:
                    itens = leitor.ler(resposta.conteudo)
                    novas = guardar(conexao, v, feed, itens, cidades)
                    resumo["novas"] += novas
                    aviso(f"  {v['nome']}: {novas} novas de {len(itens)} no feed")
                _registrar(conexao, url, v["id"], resposta.etag, resposta.modificado, "ok", None)
            except leitor.ErroFeed as e:
                resumo["erros"] += 1
                _registrar(conexao, url, v["id"], None, None, "erro", str(e))
                aviso(f"  {v['nome']}: ERRO, {e} ({url})")
            conexao.commit()
    return resumo


def guardar(conexao, veiculo, feed, itens, cidades=()):
    """Insere as notícias; um link já guardado é ignorado. Devolve quantas eram novas."""
    momento = agora()
    escala_padrao = escala_do_feed(veiculo, feed)
    uso = feed.get("uso", "noticias")
    novas = 0
    for item in itens:
        escala, uf, cidade = escala_padrao, veiculo.get("uf"), veiculo.get("cidade")
        lista = [{"nome": cidade, "uf": uf}] if cidade else []
        if uso == "noticias" and escala in ("estado", "pais"):
            citadas = cidades_citadas(item, veiculo, cidades)
            if citadas:
                # Notícia estadual sobre a cidade vai para a aba Cidade; a nacional fica na aba País. As duas
                # aparecem na aba Cidade de todas as cidades citadas
                uf, cidade = citadas[0]["uf"], citadas[0]["nome"]
                lista = [{"nome": c["nome"], "uf": c["uf"]} for c in citadas]
                if escala == "estado":
                    escala = "cidade"
        cursor = conexao.execute(
            """INSERT OR IGNORE INTO noticias
               (veiculo_id, titulo, link, guid, resumo, autor, publicado_em, coletado_em, escala, uso, uf, cidade, cidades)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (veiculo["id"], item["titulo"], item["link"], item["guid"], item["resumo"], item["autor"],
             data_confiavel(item["publicado_em"], momento), momento, escala, uso, uf, cidade,
             json.dumps(lista, ensure_ascii=False) if lista else None),
        )
        novas += cursor.rowcount
    return novas


def remover_antigas(conexao, dias=30):
    """Apaga notícias coletadas há mais de `dias` dias, para o banco não crescer sem limite."""
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(timespec="seconds")
    removidas = conexao.execute("DELETE FROM noticias WHERE coletado_em < ?", (limite,)).rowcount
    conexao.commit()
    return removidas


def _registrar(conexao, url, veiculo_id, etag, modificado, status, erro):
    ok = status == "ok"
    conexao.execute(
        """INSERT INTO feeds (url, veiculo_id, etag, modificado, ultima_coleta, ultimo_status, ultimo_erro, falhas_seguidas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(url) DO UPDATE SET
             veiculo_id = excluded.veiculo_id,
             etag = COALESCE(excluded.etag, feeds.etag),
             modificado = COALESCE(excluded.modificado, feeds.modificado),
             ultima_coleta = excluded.ultima_coleta,
             ultimo_status = excluded.ultimo_status,
             ultimo_erro = excluded.ultimo_erro,
             falhas_seguidas = CASE WHEN ? THEN 0 ELSE feeds.falhas_seguidas + 1 END""",
        (url, veiculo_id, etag, modificado, agora(), status, erro, 0 if ok else 1, ok),
    )
