"""Agentes do conselho de IA na API do Google Gemini, no plano gratuito.

Precisa de GEMINI_API_KEY (criada em aistudio.google.com, sem cartão). A cota gratuita é por minuto
e por dia; quando acaba, a execução para e as notícias restantes ficam para a próxima rodada.
Só a biblioteca padrão do Python.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

from .conselho import ESQUEMA_PARECER, ErroModelo
from .modelo_github import _extrair_json

API = "https://generativelanguage.googleapis.com/v1beta"
VARIAVEIS = {"acusacao": "GEMINI_MODELO_ACUSACAO", "defesa": "GEMINI_MODELO_DEFESA",
             "auditor-fontes": "GEMINI_MODELO_FONTES"}
# A cota gratuita limita pedidos por minuto: uma pausa curta entre chamadas evita estourar
PAUSA_ENTRE_CHAMADAS = 6


class CotaEsgotada(ErroModelo):
    parar = True


def _chave():
    return (os.environ.get("GEMINI_API_KEY") or "").strip()


def _pedir(caminho, corpo=None, timeout=180):
    pedido = urllib.request.Request(f"{API}/{caminho}", method="POST" if corpo is not None else "GET",
                                    data=json.dumps(corpo).encode() if corpo is not None else None,
                                    headers={"x-goog-api-key": _chave(), "Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        return json.loads(r.read())


def _detalhe(e):
    return e.read().decode("utf-8", "replace")[:300]


def _chave_recusada(codigo, detalhe):
    return codigo in (401, 403) or "API key" in detalhe or "API_KEY" in detalhe


def _erro_http(e, detalhe, contexto):
    if e.code == 429:
        return CotaEsgotada(f"cota gratuita do Gemini esgotada ({contexto}); "
                            "as notícias restantes ficam para a próxima rodada")
    if _chave_recusada(e.code, detalhe):
        erro = ErroModelo(f"o Google recusou a chave GEMINI_API_KEY ({e.code}): {detalhe}")
        erro.parar = True
        return erro
    return ErroModelo(f"o Gemini respondeu {e.code} ({contexto}): {detalhe}")


def listar_modelos():
    """Nomes dos modelos que geram texto com esta chave, como "gemini-2.5-flash"."""
    nomes, pagina = [], ""
    for _ in range(5):
        try:
            dados = _pedir("models?pageSize=200" + (f"&pageToken={pagina}" if pagina else ""))
        except urllib.error.HTTPError as e:
            raise _erro_http(e, _detalhe(e), "lista de modelos") from e
        except urllib.error.URLError as e:
            raise ErroModelo(f"sem conexão com a API do Gemini ({e.reason})") from e
        for m in dados.get("models", []):
            if "generateContent" in (m.get("supportedGenerationMethods") or []):
                nomes.append(m["name"].removeprefix("models/"))
        pagina = dados.get("nextPageToken")
        if not pagina:
            break
    return nomes


def _versao(nome):
    achado = re.match(r"gemini-(\d+(?:\.\d+)?)", nome)
    return float(achado.group(1)) if achado else 0.0


def _mais_novo(nomes, tipo):
    """O Gemini mais novo de um tipo ("flash" ou "flash-lite"), preferindo versões estáveis."""
    def serve(n):
        partes = n.split("-")
        if not n.startswith("gemini-") or any(x in n for x in ("image", "tts", "audio", "live", "embedding", "vision")):
            return False
        return (tipo == "flash-lite" and "flash-lite" in n) or (tipo == "flash" and "flash" in partes and "lite" not in partes)
    candidatos = [n for n in nomes if serve(n)]
    estaveis = [n for n in candidatos if not any(x in n for x in ("preview", "exp"))]
    lista = estaveis or candidatos
    # Entre versões iguais, o nome mais curto costuma ser o apelido estável ("gemini-2.5-flash")
    return max(lista, key=lambda n: (_versao(n), -len(n))) if lista else None


def escolher_modelos(nomes, aviso=print):
    """Modelo de cada agente: variável do repositório ou o Gemini mais novo da lista.
    A Defesa usa um modelo diferente da Acusação (o Flash-Lite), para não errarem do mesmo jeito."""
    flash = _mais_novo(nomes, "flash")
    lite = _mais_novo(nomes, "flash-lite") or flash
    padrao = {"acusacao": flash, "defesa": lite, "auditor-fontes": flash}
    escolhidos = {}
    for agente, variavel in VARIAVEIS.items():
        escolhidos[agente] = (os.environ.get(variavel) or "").strip() or padrao[agente]
        if not escolhidos[agente]:
            raise ErroModelo("nenhum modelo Gemini Flash disponível para esta chave")
        aviso(f"  {agente}: {escolhidos[agente]}")
    return escolhidos


class AgenteGemini:
    def __init__(self, modelo):
        self.modelo = modelo
        self.tokens = [0, 0]
        # Esquema JSON estrito quando o modelo aceita; se não, só "responda em JSON" com o esquema no texto
        self.esquema_estrito = True

    def _corpo(self, sistema, conteudo):
        config = {"responseMimeType": "application/json"}
        if self.esquema_estrito:
            config["responseJsonSchema"] = ESQUEMA_PARECER
        else:
            sistema += ("\n\nResponda só com um objeto JSON neste esquema:\n"
                        + json.dumps(ESQUEMA_PARECER, ensure_ascii=False))
        return {"systemInstruction": {"parts": [{"text": sistema}]},
                "contents": [{"role": "user", "parts": [{"text": conteudo}]}],
                "generationConfig": config}

    def parecer(self, sistema, conteudo):
        time.sleep(PAUSA_ENTRE_CHAMADAS)
        while True:
            try:
                r = _pedir(f"models/{self.modelo}:generateContent", self._corpo(sistema, conteudo))
                break
            except urllib.error.HTTPError as e:
                detalhe = _detalhe(e)
                if e.code == 400 and self.esquema_estrito and not _chave_recusada(e.code, detalhe):
                    self.esquema_estrito = False  # tenta sem o esquema estrito
                    continue
                raise _erro_http(e, detalhe, self.modelo) from e
            except urllib.error.URLError as e:
                erro = ErroModelo(f"sem conexão com a API do Gemini ({e.reason})")
                erro.parar = True
                raise erro from e

        uso = r.get("usageMetadata") or {}
        self.tokens[0] += uso.get("promptTokenCount") or 0
        self.tokens[1] += uso.get("candidatesTokenCount") or 0
        candidatos = r.get("candidates") or []
        if not candidatos:
            motivo = (r.get("promptFeedback") or {}).get("blockReason") or "sem resposta"
            raise ErroModelo(f"o Gemini não respondeu ({motivo})")
        c = candidatos[0]
        if c.get("finishReason") == "MAX_TOKENS":
            raise ErroModelo("resposta cortada pelo limite de tamanho")
        if c.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION"):
            raise ErroModelo(f"o Gemini recusou analisar esta notícia ({c['finishReason']})")
        texto = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", []) if not p.get("thought"))
        try:
            return _extrair_json(texto), f"{r.get('modelVersion') or self.modelo} · Google"
        except json.JSONDecodeError as e:
            raise ErroModelo(f"{self.modelo} devolveu um parecer fora do formato") from e
