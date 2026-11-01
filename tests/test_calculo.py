"""Testes do Cálculo de evidências (sem IA)."""

import math
import unittest

from coletor import calculo

FUNDO = ["Corinthians vence o Mirassol e sai da zona de rebaixamento", "Prefeitura abre inscrições para cursos gratuitos",
         "Governo anuncia reajuste do salário mínimo", "Chuva forte provoca alagamentos em Salvador",
         "Polícia prende suspeito de assalto em Teresina", "Flamengo empata com o Palmeiras no Maracanã"]
VEICULOS = {"a": {"id": "a", "nome": "Gazeta", "tipo": "jornal", "grupo": "G1"},
            "b": {"id": "b", "nome": "Portal B", "tipo": "portal", "grupo": "G2"},
            "c": {"id": "c", "nome": "Rádio C", "tipo": "radio", "grupo": "G3"},
            "d": {"id": "d", "nome": "Gazeta Online", "tipo": "portal", "grupo": "G1"},
            "x": {"id": "x", "nome": "Checa", "tipo": "checador", "grupo": "GX"}}


def linha(link, veiculo, titulo, uso="noticias"):
    return {"link": link, "titulo": titulo, "resumo": "", "veiculo_id": veiculo, "uso": uso,
            "publicado_em": "2026-11-01T10:00:00", "coletado_em": "2026-11-01T10:00:00"}


def corpus(*linhas):
    fundo = [linha(f"f{i}", f"z{i}", t) for i, t in enumerate(FUNDO)]
    return calculo.Corpus(fundo + list(linhas))


ORIGINAL = linha("o", "a", "Ataque a tiros deixa dois mortos e seis feridos em Cariacica")


class TestCalculo(unittest.TestCase):
    def test_dois_grupos_independentes_confirmam(self):
        c = corpus(ORIGINAL, linha("1", "b", "Homem e mulher são mortos e seis ficam feridos em ataque a tiros em Cariacica"),
                   linha("2", "c", "Ataque a tiros em Cariacica deixa dois mortos e seis feridos"))
        r = calculo.classificar(ORIGINAL, c, VEICULOS)
        self.assertEqual(r["rotulo"], "confirmada")
        self.assertGreaterEqual(r["confianca"], calculo.CONFIANCA_CONFIRMADA)

    def test_confianca_e_a_soma_de_evidencias_independentes(self):
        c = corpus(ORIGINAL, linha("1", "b", "Ataque a tiros deixa dois mortos e seis feridos em Cariacica"),
                   linha("2", "c", "Ataque a tiros deixa dois mortos e seis feridos em Cariacica"))
        r = calculo.classificar(ORIGINAL, c, VEICULOS)
        # Textos idênticos: força máxima, p = peso do tipo; C = 1 − (1 − 0,75)(1 − 0,85)
        self.assertAlmostEqual(r["confianca"], 1 - (1 - 0.75) * (1 - 0.85), places=6)

    def test_mesmo_grupo_do_original_nao_confirma(self):
        c = corpus(ORIGINAL, linha("1", "d", "Ataque a tiros deixa dois mortos e seis feridos em Cariacica"),
                   linha("2", "b", "Ataque a tiros deixa dois mortos e seis feridos em Cariacica"))
        r = calculo.classificar(ORIGINAL, c, VEICULOS)
        self.assertEqual(r["rotulo"], "em-apuracao")
        self.assertEqual(len(r["provas"]), 1)

    def test_numeros_diferentes_sao_fatos_diferentes(self):
        original = linha("o", "a", "Mega-Sena 3079 acumula e prêmio vai a R$ 42 milhões")
        c = corpus(original, linha("1", "b", "Mega-Sena 3080 acumula e prêmio vai a R$ 46 milhões"),
                   linha("2", "c", "Mega-Sena 3080: prêmio acumula e vai a R$ 46 milhões"))
        self.assertEqual(calculo.classificar(original, c, VEICULOS)["provas"], [])

    def test_checagem_parecida_impede_confirmada_e_avisa(self):
        c = corpus(ORIGINAL, linha("1", "b", "Ataque a tiros deixa dois mortos e seis feridos em Cariacica"),
                   linha("2", "c", "Ataque a tiros deixa dois mortos e seis feridos em Cariacica"),
                   linha("3", "x", "É falso que ataque a tiros deixou dois mortos e seis feridos em Cariacica", "checagens"))
        r = calculo.classificar(ORIGINAL, c, VEICULOS)
        self.assertEqual(r["rotulo"], "em-apuracao")
        self.assertTrue(r["avisos"])

    def test_opiniao_e_texto_curto(self):
        opiniao = linha("p", "a", "Coluna: o que o ataque em Cariacica nos ensina")
        curta = linha("q", "a", "Veja hoje")
        c = corpus(opiniao, curta)
        self.assertEqual(calculo.classificar(opiniao, c, VEICULOS)["rotulo"], "opiniao")
        self.assertEqual(calculo.classificar(curta, c, VEICULOS)["rotulo"], "dados-insuficientes")

    def test_vetores_tem_norma_um(self):
        c = corpus(ORIGINAL)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in c.vetor(ORIGINAL).values())), 1.0)


if __name__ == "__main__":
    unittest.main()
