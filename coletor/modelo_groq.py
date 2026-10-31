"""Agentes do conselho de IA no plano gratuito do Groq (console.groq.com).

A chave gratuita (GROQ_API_KEY, nos Secrets do repositório) não pede cartão. A cota é por modelo, por
minuto e por dia; quando ela acaba, a execução para e as notícias restantes ficam para a próxima rodada.
A API segue o formato da OpenAI. Só a biblioteca padrão do Python.
"""

import json
import os
import time
import urllib.error
import urllib.request

from .conselho import ESQUEMA_PARECER, ErroModelo
from .modelo_github import _extrair_json

API = "https://api.groq.com/openai/v1"

# Preferência de cada agente; modelos de empresas diferentes, para não errarem do mesmo jeito.
# Se nenhum da lista estiver no catálogo da chave, o agente usa outro modelo de texto do catálogo.
PREFERENCIAS = {
    "acusacao": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile"],
    "defesa": ["meta-llama/llama-4-maverick-17b-128e-instruct", "llama-3.3-70b-versatile",
               "meta-llama/llama-4-scout-17b-16e-instruct"],
    "auditor-fontes": ["moonshotai/kimi-k2-instruct-0905", "moonshotai/kimi-k2-instruct", "openai/gpt-oss-20b"],
    "relator": ["openai/gpt-oss-120b", "moonshotai/kimi-k2-instruct-0905", "llama-3.3-70b-versatile"],
}
VARIAVEIS = {"acusacao": "GROQ_MODELO_ACUSACAO", "defesa": "GROQ_MODELO_DEFESA",
             "auditor-fontes": "GROQ_MODELO_FONTES", "relator": "GROQ_MODELO_RELATOR"}
# Modelos do catálogo que não servem para escrever pareceres (áudio, moderação)
NAO_TEXTO = ("whisper", "tts", "guard", "playai", "distil", "orpheus")

PAUSA_ENTRE_CHAMADAS = 3
ESPERA_MAXIMA = 60  # segundos: um limite por minuto se espera; um limite do dia encerra a execução


class CotaEsgotada(ErroModelo):
    """A cota gratuita do dia acabou: não adianta continuar nesta execução."""

    parar = True


def _chave():
    return (os.environ.get("GROQ_API_KEY") or "").strip()


def _pedir(caminho, corpo=None, timeout=120):
    pedido = urllib.request.Request(
        API + caminho, method="POST" if corpo is not None else "GET",
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"Authorization": f"Bearer {_chave()}", "Content-Type": "application/json",
                 "User-Agent": "OFarolColetor/0.1"})
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        return json.loads(r.read())


def catalogo():
    """Modelos ativos da chave (lista de dicionários com id e owned_by)."""
    try:
        dados = _pedir("/models", timeout=30)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ErroModelo(f"o Groq recusou a chave ({e.code}); confira GROQ_API_KEY nos Secrets") from e
        raise ErroModelo(f"o catálogo do Groq respondeu {e.code}") from e
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        raise ErroModelo(f"sem conexão com o Groq ({e})") from e
    return [m for m in dados.get("data", []) if isinstance(m, dict) and m.get("id") and m.get("active", True)]


def escolher_modelos(modelos, aviso=print):
    """Modelo de cada agente: variável do repositório, depois a lista de preferência, depois o catálogo."""
    ids = {m["id"] for m in modelos}
    texto = [m for m in modelos if not any(p in m["id"].lower() for p in NAO_TEXTO)]
    escolhidos = {}
    for agente, preferidos in PREFERENCIAS.items():
        pedido = (os.environ.get(VARIAVEIS[agente]) or "").strip()
        achado = pedido or next((p for p in preferidos if p in ids), None)
        if not achado:
            empresa_acusacao = escolhidos.get("acusacao", "").split("/")[0]
            candidatos = [m["id"] for m in texto if agente != "defesa" or m["id"].split("/")[0] != empresa_acusacao]
            achado = candidatos[0] if candidatos else None
        if not achado:
            raise ErroModelo("nenhum modelo de texto disponível no Groq para esta chave")
        escolhidos[agente] = achado
        aviso(f"  {agente}: {achado}")
    return escolhidos


class AgenteGroq:
    def __init__(self, modelo):
        self.modelo = modelo
        self.tokens = [0, 0]
        # Nem todo modelo aceita esquema JSON estrito; o formato que funcionar fica guardado
        self.formatos = [
            {"type": "json_schema", "json_schema": {"name": "parecer", "schema": ESQUEMA_PARECER, "strict": True}},
            {"type": "json_object"},
        ]

    def _chamar(self, sistema, conteudo):
        formato = self.formatos[0]
        if formato["type"] != "json_schema":
            sistema += ("\n\nResponda só com um objeto JSON neste esquema, sem texto antes ou depois:\n"
                        + json.dumps(ESQUEMA_PARECER, ensure_ascii=False))
        return _pedir("/chat/completions", {
            "model": self.modelo, "temperature": 0.2, "response_format": formato,
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": conteudo}]})

    def parecer(self, sistema, conteudo):
        time.sleep(PAUSA_ENTRE_CHAMADAS)
        esperas = 0
        while True:
            try:
                r = self._chamar(sistema, conteudo)
                break
            except urllib.error.HTTPError as e:
                detalhe = e.read().decode("utf-8", "replace")[:300]
                if e.code == 429:
                    espera = _segundos(e.headers.get("retry-after"))
                    if espera is not None and espera <= ESPERA_MAXIMA and esperas < 3:
                        esperas += 1
                        time.sleep(espera + 1)
                        continue
                    raise CotaEsgotada(f"cota gratuita do Groq esgotada para {self.modelo}; "
                                       "as notícias restantes ficam para a próxima rodada") from e
                if e.code in (401, 403):
                    erro = ErroModelo(f"o Groq recusou a chave ({e.code}); confira GROQ_API_KEY nos Secrets")
                    erro.parar = True
                    raise erro from e
                if e.code == 400 and len(self.formatos) > 1 and "json" in detalhe.lower():
                    self.formatos.pop(0)  # tenta um formato de resposta mais simples
                    continue
                raise ErroModelo(f"o Groq respondeu {e.code} para {self.modelo}: {detalhe}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                raise ErroModelo(f"sem conexão com o Groq ({getattr(e, 'reason', e)})") from e

        uso = r.get("usage") or {}
        self.tokens[0] += uso.get("prompt_tokens") or 0
        self.tokens[1] += uso.get("completion_tokens") or 0
        escolha = (r.get("choices") or [{}])[0]
        mensagem = escolha.get("message") or {}
        if escolha.get("finish_reason") == "length":
            raise ErroModelo("resposta cortada pelo limite de tamanho")
        try:
            return _extrair_json(mensagem.get("content")), f"{r.get('model') or self.modelo} · Groq"
        except json.JSONDecodeError as e:
            raise ErroModelo(f"{self.modelo} devolveu um parecer fora do formato") from e


def _segundos(texto):
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None
