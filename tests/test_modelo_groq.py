"""Testes do Groq, sem chamar a API de verdade."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from coletor import conselho, modelo_groq

PARECER = {"rotuloSugerido": "em-apuracao", "confianca": 0.5, "tema": "local", "afirmacao": "x",
           "motivos": ["m"], "provas": [], "manipulacao": False}
CATALOGO = [{"id": "openai/gpt-oss-120b"}, {"id": "llama-3.3-70b-versatile"}, {"id": "whisper-large-v3"}]


def resposta(conteudo):
    return {"model": "openai/gpt-oss-120b", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "choices": [{"finish_reason": "stop", "message": {"content": conteudo}}]}


def erro_http(codigo, cabecalhos=None, corpo=b"{}"):
    return urllib.error.HTTPError("https://api.groq.com", codigo, "erro", cabecalhos or {}, io.BytesIO(corpo))


class TestModeloGroq(unittest.TestCase):
    def setUp(self):
        mock.patch.object(modelo_groq, "PAUSA_ENTRE_CHAMADAS", 0).start()
        mock.patch("time.sleep").start()
        self.addCleanup(mock.patch.stopall)

    def test_escolhe_modelos_do_catalogo(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            modelos = modelo_groq.escolher_modelos(CATALOGO, aviso=lambda *_: None)
        self.assertEqual(modelos["acusacao"], "openai/gpt-oss-120b")
        self.assertEqual(modelos["defesa"], "llama-3.3-70b-versatile")
        self.assertEqual(modelos["relator"], "openai/gpt-oss-120b")
        self.assertNotIn("whisper-large-v3", modelos.values())

    def test_limite_por_minuto_espera_e_tenta_de_novo(self):
        respostas = [erro_http(429, {"retry-after": "7"}), resposta(json.dumps(PARECER))]
        with mock.patch.object(modelo_groq, "_pedir", side_effect=respostas):
            agente = modelo_groq.AgenteGroq("openai/gpt-oss-120b")
            parecer, modelo = agente.parecer("sistema", "conteudo")
        self.assertEqual(parecer["rotuloSugerido"], "em-apuracao")
        self.assertIn("Groq", modelo)
        self.assertEqual(agente.tokens, [10, 5])

    def test_limite_do_dia_para_a_execucao(self):
        with mock.patch.object(modelo_groq, "_pedir", side_effect=erro_http(429, {"retry-after": "3600"})):
            with self.assertRaises(conselho.ErroModelo) as erro:
                modelo_groq.AgenteGroq("openai/gpt-oss-120b").parecer("sistema", "conteudo")
        self.assertTrue(erro.exception.parar)

    def test_cai_para_json_object_quando_o_esquema_nao_e_aceito(self):
        respostas = [erro_http(400, corpo=b'{"error":"json_schema not supported"}'), resposta(json.dumps(PARECER))]
        with mock.patch.object(modelo_groq, "_pedir", side_effect=respostas) as pedir:
            modelo_groq.AgenteGroq("llama-3.3-70b-versatile").parecer("sistema", "conteudo")
        self.assertEqual(pedir.call_args.args[1]["response_format"], {"type": "json_object"})
        self.assertIn("JSON", pedir.call_args.args[1]["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
