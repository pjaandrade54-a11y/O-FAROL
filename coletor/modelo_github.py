"""Agentes do conselho de IA nos modelos gratuitos do GitHub Models.

Usa o GITHUB_TOKEN que o GitHub Actions já fornece (permissão "models: read"), sem chave nem cartão.
A cota gratuita é diária e por modelo; quando ela acaba, a execução para e as notícias restantes
ficam para o dia seguinte. Só a biblioteca padrão do Python.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

from .conselho import ESQUEMA_PARECER, ErroModelo

CATALOGO = "https://models.github.ai/catalog/models"
# Endereços de inferência, na ordem em que são tentados. O segundo é o endereço antigo do GitHub Models,
# que usa o nome do modelo sem a empresa ("gpt-4.1" em vez de "openai/gpt-4.1").
ENDERECOS = [
    ("https://models.github.ai/inference/chat/completions", lambda modelo: modelo),
    ("https://models.inference.ai.azure.com/chat/completions", lambda modelo: modelo.split("/", 1)[-1]),
]

# Preferência de cada agente. Acusação e Defesa em empresas diferentes, para não errarem do mesmo jeito.
# Se nenhum da lista estiver no catálogo, o agente usa outro modelo do catálogo (veja escolher_modelos).
PREFERENCIAS = {
    "acusacao": ["openai/gpt-4.1", "openai/gpt-4o"],
    "defesa": ["meta/llama-4-maverick-17b-128e-instruct-fp8", "mistral-ai/mistral-medium-2505",
               "deepseek/deepseek-v3-0324", "meta/meta-llama-3.1-405b-instruct"],
    "auditor-fontes": ["openai/gpt-4.1-mini", "openai/gpt-4o-mini"],
}
VARIAVEIS = {"acusacao": "GITHUB_MODELO_ACUSACAO", "defesa": "GITHUB_MODELO_DEFESA",
             "auditor-fontes": "GITHUB_MODELO_FONTES"}

# A cota gratuita também limita pedidos por minuto: uma pausa curta entre chamadas evita estourar
PAUSA_ENTRE_CHAMADAS = 6


class RespostaInvalida(ErroModelo):
    """O endereço respondeu, mas sem JSON: provavelmente não é (mais) o endereço do serviço."""


class CotaEsgotada(ErroModelo):
    """A cota gratuita do dia (ou do minuto) acabou: não adianta continuar nesta execução."""

    parar = True


def _token():
    return (os.environ.get("GITHUB_TOKEN") or "").strip()


def _pedir(url, corpo=None, timeout=180):
    pedido = urllib.request.Request(url, method="POST" if corpo is not None else "GET",
                                    data=json.dumps(corpo).encode() if corpo is not None else None, headers={
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        corpo = r.read()
        tipo = r.headers.get("Content-Type", "")
    try:
        return json.loads(corpo)
    except json.JSONDecodeError as e:
        trecho = corpo[:80].decode("utf-8", "replace").strip()
        raise RespostaInvalida(f"{url} respondeu {tipo or 'sem tipo'} sem JSON: {trecho!r}") from e


def catalogo(aviso=print):
    """Modelos disponíveis (dicionários com id e publisher). Se o catálogo falhar, devolve lista vazia
    e os agentes usam o primeiro modelo da lista de preferência de cada um."""
    pedido = urllib.request.Request(CATALOGO, headers={"Authorization": f"Bearer {_token()}",
                                                      "Accept": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            corpo = r.read()
            tipo = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        aviso(f"  Aviso: o catálogo do GitHub Models respondeu {e.code}; usando os modelos padrão.")
        return []
    except urllib.error.URLError as e:
        raise ErroModelo(f"sem conexão com o GitHub Models ({e.reason})") from e
    try:
        dados = json.loads(corpo)
    except json.JSONDecodeError:
        trecho = corpo[:120].decode("utf-8", "replace").replace("\n", " ")
        aviso(f"  Aviso: o catálogo do GitHub Models não veio em JSON ({tipo or 'sem tipo'}: {trecho!r}); "
              "usando os modelos padrão.")
        return []
    if isinstance(dados, dict):
        dados = dados.get("models") or dados.get("data") or []
    return [m for m in dados if isinstance(m, dict) and m.get("id")]


def escolher_modelos(modelos, aviso=print):
    """Modelo de cada agente: variável do repositório, depois a lista de preferência, depois o catálogo."""
    ids = {m["id"] for m in modelos}
    texto = [m for m in modelos if "text" in (m.get("supported_output_modalities") or ["text"])]
    escolhidos = {}
    for agente, preferidos in PREFERENCIAS.items():
        pedido = (os.environ.get(VARIAVEIS[agente]) or "").strip()
        if pedido:
            escolhidos[agente] = pedido
            continue
        achado = next((p for p in preferidos if p in ids), None) if ids else preferidos[0]
        if not achado:
            # Fora da lista: um modelo de texto, de empresa diferente da Acusação no caso da Defesa
            empresa_acusacao = escolhidos.get("acusacao", "").split("/")[0]
            candidatos = [m["id"] for m in texto
                          if agente != "defesa" or m.get("publisher", m["id"].split("/")[0]).lower() != empresa_acusacao]
            achado = candidatos[0] if candidatos else None
        if not achado:
            raise ErroModelo("nenhum modelo de texto disponível no GitHub Models")
        escolhidos[agente] = achado
    for agente, modelo in escolhidos.items():
        aviso(f"  {agente}: {modelo}")
    return escolhidos


def _extrair_json(texto):
    """Alguns modelos cercam o JSON com ```json ou texto; pega o primeiro objeto."""
    texto = (texto or "").strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        achado = re.search(r"\{.*\}", texto, re.S)
        if achado:
            return json.loads(achado.group(0))
        raise


class AgenteGitHub:
    def __init__(self, modelo):
        self.modelo = modelo
        self.tokens = [0, 0]
        # Nem todo modelo aceita esquema JSON estrito; o formato que funcionar fica guardado
        self.formatos = [
            {"type": "json_schema", "json_schema": {"name": "parecer", "schema": ESQUEMA_PARECER, "strict": True}},
            {"type": "json_object"},
            None,
        ]

    def _chamar(self, sistema, conteudo, formato):
        if formato is None or formato["type"] != "json_schema":
            sistema += ("\n\nResponda só com um objeto JSON neste esquema, sem texto antes ou depois:\n"
                        + json.dumps(ESQUEMA_PARECER, ensure_ascii=False))
        url, nome = ENDERECOS[0]
        corpo = {"model": nome(self.modelo),
                 "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": conteudo}]}
        if formato:
            corpo["response_format"] = formato
        return _pedir(url, corpo)

    def parecer(self, sistema, conteudo):
        time.sleep(PAUSA_ENTRE_CHAMADAS)
        while True:
            formato = self.formatos[0]
            try:
                r = self._chamar(sistema, conteudo, formato)
                break
            except urllib.error.HTTPError as e:
                detalhe = e.read().decode("utf-8", "replace")[:300]
                if e.code == 429:
                    raise CotaEsgotada(f"cota gratuita do GitHub Models esgotada para {self.modelo}; "
                                       "as notícias restantes ficam para a próxima rodada") from e
                if e.code in (401, 403):
                    raise ErroModelo(f"o GitHub Models recusou o acesso ({e.code}); "
                                     "confira a permissão models: read no fluxo") from e
                if e.code in (400, 422) and len(self.formatos) > 1:
                    self.formatos.pop(0)  # tenta um formato de resposta mais simples
                    continue
                raise ErroModelo(f"o GitHub Models respondeu {e.code} para {self.modelo}: {detalhe}") from e
            except RespostaInvalida as e:
                # Endereço que não serve: passa para o próximo, para todos os agentes
                if len(ENDERECOS) > 1:
                    print(f"  Aviso: {e}; tentando {ENDERECOS[1][0]}")
                    ENDERECOS.pop(0)
                    continue
                e.parar = True
                raise
            except urllib.error.URLError as e:
                raise ErroModelo(f"sem conexão com o GitHub Models ({e.reason})") from e

        uso = r.get("usage") or {}
        self.tokens[0] += uso.get("prompt_tokens") or 0
        self.tokens[1] += uso.get("completion_tokens") or 0
        escolha = (r.get("choices") or [{}])[0]
        mensagem = escolha.get("message") or {}
        if mensagem.get("refusal"):
            raise ErroModelo("o modelo recusou analisar esta notícia")
        if escolha.get("finish_reason") == "length":
            raise ErroModelo("resposta cortada pelo limite de tamanho")
        try:
            return _extrair_json(mensagem.get("content")), f"{r.get('model') or self.modelo} · GitHub Models"
        except json.JSONDecodeError as e:
            raise ErroModelo(f"{self.modelo} devolveu um parecer fora do formato") from e
