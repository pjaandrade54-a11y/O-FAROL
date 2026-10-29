"""Agente do conselho de IA que roda no GPT (OpenAI). Precisa do pacote openai e de OPENAI_API_KEY.

A Defesa fica numa empresa diferente da Acusação para que os dois lados não errem do mesmo jeito.
"""

import json

import openai

from .conselho import ESQUEMA_PARECER, ErroModelo

# Troque pela variável OPENAI_MODELO do repositório quando a OpenAI lançar outro modelo
MODELO_PADRAO = "gpt-6.1-terra"


class AgenteOpenAI:
    def __init__(self, modelo):
        self.modelo = modelo
        self.cliente = openai.OpenAI(max_retries=3, timeout=300)
        self.tokens = [0, 0]

    def parecer(self, sistema, conteudo):
        try:
            r = self.cliente.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "system", "content": sistema}, {"role": "user", "content": conteudo}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "parecer", "schema": ESQUEMA_PARECER, "strict": True},
                },
            )
        except openai.AuthenticationError as e:
            raise ErroModelo("chave da OpenAI inválida (OPENAI_API_KEY)") from e
        except openai.RateLimitError as e:
            raise ErroModelo("limite de uso da OpenAI atingido; tenta de novo na próxima coleta") from e
        except openai.APIStatusError as e:
            raise ErroModelo(f"a API da OpenAI respondeu {e.status_code}: {e.message}") from e
        except openai.APIConnectionError as e:
            raise ErroModelo("sem conexão com a API da OpenAI") from e

        if r.usage:
            self.tokens[0] += r.usage.prompt_tokens
            self.tokens[1] += r.usage.completion_tokens
        escolha = r.choices[0]
        if escolha.message.refusal:
            raise ErroModelo("o modelo recusou analisar esta notícia")
        if escolha.finish_reason == "length":
            raise ErroModelo("resposta cortada pelo limite de tamanho")
        try:
            return json.loads(escolha.message.content or ""), f"{r.model} · OpenAI"
        except json.JSONDecodeError as e:
            raise ErroModelo("o modelo devolveu um parecer fora do formato") from e
