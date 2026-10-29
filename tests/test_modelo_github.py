"""Testes do agente no GitHub Models, sem rede (as chamadas HTTP são simuladas)."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from coletor import conselho, modelo_github

CATALOGO = [
    {"id": "openai/gpt-4.1", "publisher": "OpenAI"},
    {"id": "openai/gpt-4.1-mini", "publisher": "OpenAI"},
    {"id": "mistral-ai/mistral-small-2503", "publisher": "Mistral AI"},
]
PARECER = {"rotuloSugerido": "em-apuracao", "confianca": 0.5, "tema": "local", "afirmacao": "x",
           "motivos": ["m"], "provas": [], "manipulacao": False}


def erro_http(codigo):
    return urllib.error.HTTPError("https://x", codigo, "erro", {}, io.BytesIO(b"{}"))


def resposta(conteudo):
    return {"model": "openai/gpt-4.1", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "choices": [{"finish_reason": "stop", "message": {"content": conteudo}}]}


class TestModeloGitHub(unittest.TestCase):
    def setUp(self):
        mock.patch.object(modelo_github, "PAUSA_ENTRE_CHAMADAS", 0).start()
        self.addCleanup(mock.patch.stopall)

    def test_escolhe_defesa_de_outra_empresa_quando_a_preferida_falta(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            modelos = modelo_github.escolher_modelos(CATALOGO, aviso=lambda *_: None)
        self.assertEqual(modelos["acusacao"], "openai/gpt-4.1")
        self.assertEqual(modelos["auditor-fontes"], "openai/gpt-4.1-mini")
        self.assertEqual(modelos["defesa"], "mistral-ai/mistral-small-2503")

    def test_variavel_do_repositorio_tem_prioridade(self):
        with mock.patch.dict("os.environ", {"GITHUB_MODELO_DEFESA": "meta/outro"}, clear=True):
            modelos = modelo_github.escolher_modelos(CATALOGO, aviso=lambda *_: None)
        self.assertEqual(modelos["defesa"], "meta/outro")

    def test_cai_para_formato_mais_simples_e_le_json_cercado(self):
        respostas = [erro_http(400), resposta("```json\n" + json.dumps(PARECER) + "\n```")]
        with mock.patch.object(modelo_github, "_pedir", side_effect=respostas) as pedir:
            agente = modelo_github.AgenteGitHub("openai/gpt-4.1")
            parecer, modelo = agente.parecer("sistema", "conteudo")
        self.assertEqual(parecer["rotuloSugerido"], "em-apuracao")
        self.assertEqual(pedir.call_args.args[1]["response_format"], {"type": "json_object"})
        self.assertEqual(agente.tokens, [10, 5])
        self.assertIn("GitHub Models", modelo)

    def test_cota_esgotada_para_a_execucao(self):
        with mock.patch.object(modelo_github, "_pedir", side_effect=erro_http(429)):
            agente = modelo_github.AgenteGitHub("openai/gpt-4.1")
            with self.assertRaises(modelo_github.CotaEsgotada) as erro:
                agente.parecer("sistema", "conteudo")
        self.assertTrue(erro.exception.parar)
        self.assertIsInstance(erro.exception, conselho.ErroModelo)


if __name__ == "__main__":
    unittest.main()
