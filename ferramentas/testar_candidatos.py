"""Testa feeds candidatos antes de cadastrar: para cada veículo, tenta os endereços em ordem e
fica com o primeiro que responde, tem notícias e publicou nos últimos 14 dias.

    python ferramentas/testar_candidatos.py ferramentas/candidatos.json

Imprime uma linha RESULTADO por veículo, em JSON, para conferir no log do GitHub Actions.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from coletor import feeds  # noqa: E402

RECENTE = timedelta(days=14)


def sufixos(site):
    base = site.rstrip("/")
    return [base + s for s in ("/feed/", "/rss", "/rss.xml", "/feed")]


def testar(candidato):
    tentativas = []
    for url in candidato.get("feeds", []) + (sufixos(candidato["site"]) if candidato.get("adivinhar", True) else []):
        if url in [t[0] for t in tentativas]:
            continue
        try:
            itens = feeds.ler(feeds.baixar(url, tempo_limite=15).conteudo)
        except feeds.ErroFeed as e:
            tentativas.append((url, str(e)[:80]))
            continue
        except Exception as e:  # qualquer outro problema do site conta como falha deste endereço
            tentativas.append((url, type(e).__name__))
            continue
        datas = sorted((i["publicado_em"] for i in itens if i["publicado_em"]), reverse=True)
        if not itens:
            tentativas.append((url, "sem notícias"))
            continue
        if datas and datetime.fromisoformat(datas[0]) < datetime.now(timezone.utc) - RECENTE:
            tentativas.append((url, f"parado desde {datas[0][:10]}"))
            continue
        return {"id": candidato["id"], "ok": True, "url": url, "itens": len(itens),
                "mais_recente": datas[0] if datas else None, "exemplo": itens[0]["titulo"][:80]}
    return {"id": candidato["id"], "ok": False, "tentativas": tentativas}


def main(arquivo):
    candidatos = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=16) as grupo:
        resultados = list(grupo.map(testar, candidatos))
    for r in sorted(resultados, key=lambda r: (not r["ok"], r["id"])):
        print("RESULTADO " + json.dumps(r, ensure_ascii=False))
    print(f"{sum(r['ok'] for r in resultados)} de {len(resultados)} candidatos com feed funcionando.")


if __name__ == "__main__":
    main(sys.argv[1])
