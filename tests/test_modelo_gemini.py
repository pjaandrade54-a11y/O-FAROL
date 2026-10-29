"""Testes do agente no Gemini, sem rede (as chamadas HTTP são simuladas)."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from coletor import modelo_gemini

NOMES = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro",
         "gemini-3.0-flash-preview-09-2026", "gemini-2.5-flash-image", "gemma-3-27b-it"]
PARECER = {"rotuloSugerido": "em-apuracao", "confianca": 0.5, "tema": "local", "afirmacao": "x",
           "motivos": ["m"], "provas": [], "manipulacao": False}


def erro_http(codigo, corpo=b"{}"):
    return urllib.error.HTTPError("https://x", codigo, "erro", {}, io.BytesIO(corpo))


def resposta(texto, motivo="STOP"):
    return {"modelVersion": "gemini-2.5-flash", "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
            "candidates": [{"finishReason": motivo, "content": {"parts": [{"text": texto}]}}]}


class TestModeloGemini(unittest.TestCase):
    def setUp(self):
        mock.patch.object(modelo_gemini, "PAUSA_ENTRE_CHAMADAS", 0).start()
        self.addCleanup(mock.patch.stopall)

    def test_escolhe_o_flash_estavel_mais_novo_e_lite_para_a_defesa(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            modelos = modelo_gemini.escolher_modelos(NOMES, aviso=lambda *_: None)
        self.assertEqual(modelos, {"acusacao": "gemini-2.5-flash", "defesa": "gemini-2.5-flash-lite",
                                   "auditor-fontes": "gemini-2.5-flash"})

    def test_variavel_do_repositorio_tem_prioridade(self):
        with mock.patch.dict("os.environ", {"GEMINI_MODELO_DEFESA": "gemini-2.5-pro"}, clear=True):
            modelos = modelo_gemini.escolher_modelos(NOMES, aviso=lambda *_: None)
        self.assertEqual(modelos["defesa"], "gemini-2.5-pro")

    def test_parecer_com_esquema(self):
        with mock.patch.object(modelo_gemini, "_pedir", return_value=resposta(json.dumps(PARECER))) as pedir:
            agente = modelo_gemini.AgenteGemini("gemini-2.5-flash")
            parecer, modelo = agente.parecer("sistema", "conteudo")
        self.assertEqual(parecer, PARECER)
        self.assertEqual(modelo, "gemini-2.5-flash · Google")
        self.assertIn("responseJsonSchema", pedir.call_args.args[1]["generationConfig"])
        self.assertEqual(agente.tokens, [10, 5])

    def test_sem_suporte_a_esquema_tenta_de_novo_sem_ele(self):
        respostas = [erro_http(400, b'{"error": "responseJsonSchema not supported"}'), resposta(json.dumps(PARECER))]
        with mock.patch.object(modelo_gemini, "_pedir", side_effect=respostas) as pedir:
            parecer, _ = modelo_gemini.AgenteGemini("gemini-2.5-flash").parecer("sistema", "conteudo")
        self.assertEqual(parecer["rotuloSugerido"], "em-apuracao")
        self.assertNotIn("responseJsonSchema", pedir.call_args.args[1]["generationConfig"])

    def test_cota_esgotada_para_a_execucao(self):
        with mock.patch.object(modelo_gemini, "_pedir", side_effect=erro_http(429)):
            with self.assertRaises(modelo_gemini.CotaEsgotada) as erro:
                modelo_gemini.AgenteGemini("gemini-2.5-flash").parecer("sistema", "conteudo")
        self.assertTrue(erro.exception.parar)

    def test_chave_recusada_para_a_execucao(self):
        corpo = b'{"error": {"message": "API key not valid. Please pass a valid API key."}}'
        with mock.patch.object(modelo_gemini, "_pedir", side_effect=erro_http(400, corpo)):
            with self.assertRaises(modelo_gemini.ErroModelo) as erro:
                modelo_gemini.AgenteGemini("gemini-2.5-flash").parecer("sistema", "conteudo")
        self.assertTrue(erro.exception.parar)
        self.assertIn("GEMINI_API_KEY", str(erro.exception))

    def test_resposta_bloqueada(self):
        with mock.patch.object(modelo_gemini, "_pedir", return_value=resposta("", "SAFETY")):
            with self.assertRaises(modelo_gemini.ErroModelo):
                modelo_gemini.AgenteGemini("gemini-2.5-flash").parecer("sistema", "conteudo")


if __name__ == "__main__":
    unittest.main()
