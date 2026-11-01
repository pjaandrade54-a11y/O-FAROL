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
        # Textos idênticos: força máxima, mas provável reprodução (× 0,6); portal e rádio são tipos diferentes (× 1,15)
        base = 1 - (1 - 0.75 * 0.6) * (1 - 0.85 * 0.6)
        chances = base / (1 - base) * calculo.FATOR_TIPOS_DIFERENTES
        self.assertAlmostEqual(r["confianca"], chances / (1 + chances), places=6)

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


class TestSinais(unittest.TestCase):
    def base(self, **campos):
        return {"titulo": "", "resumo": "", "autor": None, "publicado_em": "2026-11-01T10:00:00", **campos}

    def fatores(self, **campos):
        return [f for _, f in calculo.sinais_da_noticia(self.base(**campos))]

    def test_fonte_oficial_e_autor_aumentam(self):
        self.assertEqual(self.fatores(titulo="Defesa Civil alerta para chuva forte em Aracaju", autor="Ana"),
                         [calculo.FATOR_FONTE_OFICIAL, calculo.FATOR_AUTOR])

    def test_sensacionalismo_e_atribuicao_vaga_diminuem(self):
        fatores = self.fatores(titulo="URGENTE: vídeo chocante circula nas redes!")
        self.assertIn(calculo.FATOR_ATRIBUICAO_VAGA, fatores)
        self.assertEqual(fatores.count(calculo.FATOR_SENSACIONALISMO), 2)  # no máximo dois

    def test_siglas_e_video_nao_sao_caixa_alta(self):
        self.assertEqual(self.fatores(titulo="VÍDEO: STF julga ação do PL sobre a PEC"), [calculo.FATOR_FONTE_OFICIAL])

    def test_sem_data(self):
        self.assertEqual(self.fatores(titulo="Feira de artesanato abre", publicado_em=None), [calculo.FATOR_SEM_DATA])

    def test_ajuste_bayesiano(self):
        self.assertEqual(calculo.ajustar(0, [("x", 2)]), 0)
        self.assertAlmostEqual(calculo.ajustar(0.5, [("x", 1.5)]), 0.6)
        self.assertAlmostEqual(calculo.ajustar(0.5, [("x", 0.75), ("y", 0.75)]), 0.36)

    def test_sensacionalismo_pode_impedir_confirmada(self):
        c = corpus(ORIGINAL, linha("1", "b", "Homem e mulher são mortos e seis ficam feridos em ataque a tiros em Cariacica"),
                   linha("2", "c", "Ataque a tiros em Cariacica deixa dois mortos e seis feridos"))
        calmo = calculo.classificar(ORIGINAL, c, VEICULOS)
        gritado = dict(ORIGINAL, titulo="URGENTE! Ataque a tiros deixa dois mortos e seis feridos em Cariacica")
        c2 = corpus(gritado, linha("1", "b", "Homem e mulher são mortos e seis ficam feridos em ataque a tiros em Cariacica"),
                    linha("2", "c", "Ataque a tiros em Cariacica deixa dois mortos e seis feridos"))
        alarmado = calculo.classificar(gritado, c2, VEICULOS)
        self.assertLess(alarmado["confianca"], calmo["confianca"])
        self.assertTrue(any("caixa alta" in m or "exclamação" in m for m in alarmado["motivos"][-1:]))


if __name__ == "__main__":
    unittest.main()
