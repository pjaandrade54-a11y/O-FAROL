"""Agentes do conselho de IA que rodam no Claude (Anthropic). Precisa do pacote anthropic e de ANTHROPIC_API_KEY."""

import json
import os

import anthropic

from .conselho import ESQUEMA_PARECER, ErroModelo

MODELO_PADRAO = "claude-opus-5-5"


class AgenteClaude:
    def __init__(self, modelo=MODELO_PADRAO, esforco="medium"):
        self.modelo = modelo
        self.esforco = esforco
        # Chave colada nos Secrets às vezes vem com quebra de linha no fim, o que invalida o cabeçalho HTTP
        self.cliente = anthropic.Anthropic(api_key=(os.environ.get("ANTHROPIC_API_KEY") or "").strip(),
                                           max_retries=3, timeout=300)
        self.tokens = [0, 0]

    def parecer(self, sistema, conteudo):
        try:
            # fallbacks="default": se o modelo recusar por política, a própria API refaz o pedido em outro modelo
            r = self.cliente.beta.messages.create(
                model=self.modelo,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": self.esforco, "format": {"type": "json_schema", "schema": ESQUEMA_PARECER}},
                system=sistema,
                messages=[{"role": "user", "content": conteudo}],
            )
        except anthropic.AuthenticationError as e:
            raise ErroModelo("chave da Anthropic inválida (ANTHROPIC_API_KEY)") from e
        except anthropic.RateLimitError as e:
            raise ErroModelo("limite de uso da Anthropic atingido; tenta de novo na próxima coleta") from e
        except anthropic.APIStatusError as e:
            raise ErroModelo(f"a API da Anthropic respondeu {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ErroModelo(f"sem conexão com a API da Anthropic ({type(e.__cause__).__name__})") from e

        self.tokens[0] += r.usage.input_tokens
        self.tokens[1] += r.usage.output_tokens
        if r.stop_reason == "refusal":
            raise ErroModelo("o modelo recusou analisar esta notícia")
        if r.stop_reason == "max_tokens":
            raise ErroModelo("resposta cortada pelo limite de tamanho")
        texto = next((b.text for b in r.content if b.type == "text"), "")
        try:
            return json.loads(texto), f"{r.model} · Anthropic"
        except json.JSONDecodeError as e:
            raise ErroModelo("o modelo devolveu um parecer fora do formato") from e
