"""Testes do coletor. Rode na pasta do projeto: python -m unittest discover -s tests"""

import unittest

from coletor import banco, cadastro, coleta, feeds

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Gazeta Teste</title>
    <item>
      <title>Prefeitura anuncia &amp; reforma</title>
      <link>https://exemplo.org/a</link>
      <description>&lt;p&gt;Texto com &lt;b&gt;HTML&lt;/b&gt; escapado.&lt;/p&gt;</description>
      <pubDate>Tue, 27 Oct 2026 14:30:00 -0300</pubDate>
      <dc:creator>Ana Souza</dc:creator>
    </item>
    <item>
      <title>Sem link é descartada</title>
    </item>
  </channel>
</rss>""".encode("utf-8")

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Notícia em Atom</title>
    <link rel="alternate" href="https://exemplo.org/b"/>
    <id>tag:exemplo.org,2026:b</id>
    <updated>2026-10-27T17:30:00Z</updated>
    <summary>Resumo simples.</summary>
    <author><name>Bruno Lima</name></author>
  </entry>
</feed>""".encode("utf-8")


class TestFeeds(unittest.TestCase):
    def test_rss(self):
        itens = feeds.ler(RSS)
        self.assertEqual(len(itens), 1)
        item = itens[0]
        self.assertEqual(item["titulo"], "Prefeitura anuncia & reforma")
        self.assertEqual(item["resumo"], "Texto com HTML escapado.")
        self.assertEqual(item["autor"], "Ana Souza")
        self.assertEqual(item["publicado_em"], "2026-10-27T17:30:00+00:00")

    def test_atom(self):
        item = feeds.ler(ATOM)[0]
        self.assertEqual(item["link"], "https://exemplo.org/b")
        self.assertEqual(item["guid"], "tag:exemplo.org,2026:b")
        self.assertEqual(item["autor"], "Bruno Lima")
        self.assertEqual(item["publicado_em"], "2026-10-27T17:30:00+00:00")

    def test_xml_invalido(self):
        with self.assertRaises(feeds.ErroFeed):
            feeds.ler(b"<rss><item>")

    def test_resumo_corta_em_palavra(self):
        texto = "palavra " * 100
        resumo = feeds.resumir(texto, limite=50)
        self.assertTrue(resumo.endswith("…"))
        self.assertLessEqual(len(resumo), 51)
        self.assertNotIn("palavr…", resumo)

    def test_data_invalida(self):
        self.assertIsNone(feeds.data_iso("ontem à tarde"))

    def test_link_redirecionado_e_utm(self):
        self.assertEqual(
            feeds.normalizar_link("https://redir.folha.com.br/redir/online/rss091/*https://www1.folha.uol.com.br/a.shtml"),
            "https://www1.folha.uol.com.br/a.shtml")
        self.assertEqual(feeds.normalizar_link("https://exemplo.org/a?id=3&utm_source=rss"), "https://exemplo.org/a?id=3")

    def test_espaco_dentro_de_parenteses(self):
        self.assertEqual(feeds.limpar("Lula (<b>PT</b>) disse"), "Lula (PT) disse")

    def test_data_no_futuro_vira_hora_da_coleta(self):
        momento = "2026-10-28T21:00:00+00:00"
        self.assertEqual(coleta.data_confiavel("2026-10-29T02:00:00+00:00", momento), momento)
        self.assertEqual(coleta.data_confiavel("2026-10-28T20:00:00+00:00", momento), "2026-10-28T20:00:00+00:00")


class TestCadastro(unittest.TestCase):
    def veiculo(self, **mudancas):
        v = cadastro.novo_veiculo("gazeta-teste", "Gazeta Teste", "https://exemplo.org", "jornal", "local",
                                  [{"url": "https://exemplo.org/feed"}], uf="PE", cidade="Recife")
        v.update(mudancas)
        return v

    def test_valido(self):
        self.assertEqual(cadastro.validar([self.veiculo()]), [])

    def test_local_sem_cidade(self):
        erros = cadastro.validar([self.veiculo(cidade=None)])
        self.assertTrue(any("cidade" in e for e in erros))

    def test_id_repetido_e_feed_invalido(self):
        erros = cadastro.validar([self.veiculo(), self.veiculo(feeds=[{"url": "exemplo.org/feed"}])])
        self.assertTrue(any("repetido" in e for e in erros))
        self.assertTrue(any("feed com endereço inválido" in e for e in erros))

    def test_escala_do_feed(self):
        v = self.veiculo()
        self.assertEqual(cadastro.escala_do_feed(v, {"url": "x"}), "cidade")
        self.assertEqual(cadastro.escala_do_feed(v, {"url": "x", "escala": "mundo"}), "mundo")

    def test_cadastro_do_projeto_e_valido(self):
        cadastro.carregar()


class TestColeta(unittest.TestCase):
    def test_guardar_ignora_repetidas(self):
        conexao = banco.abrir(":memory:")
        veiculo = cadastro.novo_veiculo("gazeta-teste", "Gazeta Teste", "https://exemplo.org", "jornal", "local",
                                        [{"url": "https://exemplo.org/feed"}], uf="PE", cidade="Recife")
        itens = feeds.ler(RSS)
        self.assertEqual(coleta.guardar(conexao, veiculo, veiculo["feeds"][0], itens), 1)
        self.assertEqual(coleta.guardar(conexao, veiculo, veiculo["feeds"][0], itens), 0)
        linha = conexao.execute("SELECT escala, cidade, uf FROM noticias").fetchone()
        self.assertEqual(tuple(linha), ("cidade", "Recife", "PE"))

    def test_noticia_estadual_que_cita_a_cidade_vai_para_a_aba_cidade(self):
        conexao = banco.abrir(":memory:")
        veiculo = cadastro.novo_veiculo("portal-se", "Portal SE", "https://exemplo.org", "portal", "estadual",
                                        [{"url": "https://exemplo.org/feed"}], uf="SE")
        cidades = [{"nome": "Aracaju", "uf": "SE"}, {"nome": "Recife", "uf": "PE"}]
        itens = [
            {"titulo": "Obra na orla de Aracaju começa hoje", "link": "https://exemplo.org/1", "guid": "1",
             "resumo": "", "autor": None, "publicado_em": None},
            {"titulo": "Chuva atinge o interior", "link": "https://exemplo.org/2", "guid": "2",
             "resumo": "Defesa Civil de Recife ajuda", "autor": None, "publicado_em": None},
        ]
        coleta.guardar(conexao, veiculo, veiculo["feeds"][0], itens, cidades)
        linhas = [tuple(l) for l in conexao.execute("SELECT link, escala, cidade FROM noticias ORDER BY link")]
        self.assertEqual(linhas, [("https://exemplo.org/1", "cidade", "Aracaju"), ("https://exemplo.org/2", "estado", None)])

    def test_remover_antigas(self):
        conexao = banco.abrir(":memory:")
        for link, coletado in (("https://exemplo.org/velha", "2020-01-01T00:00:00+00:00"),
                               ("https://exemplo.org/nova", coleta.agora())):
            conexao.execute("INSERT INTO noticias (veiculo_id, titulo, link, coletado_em, escala) VALUES ('x', 't', ?, ?, 'pais')",
                            (link, coletado))
        self.assertEqual(coleta.remover_antigas(conexao, dias=30), 1)
        self.assertEqual([l[0] for l in conexao.execute("SELECT link FROM noticias")], ["https://exemplo.org/nova"])

    def test_cidade_nao_casa_parte_de_palavra(self):
        veiculo = {"abrangencia": "estadual", "uf": "SE"}
        item = {"titulo": "Aracajuanos lotam a praia", "resumo": ""}
        self.assertIsNone(coleta.cidade_citada(item, veiculo, [{"nome": "Aracaju", "uf": "SE"}]))


if __name__ == "__main__":
    unittest.main()
