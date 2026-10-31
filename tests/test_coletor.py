"""Testes do coletor. Rode na pasta do projeto: python -m unittest discover -s tests"""

import json
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

    def test_nacional_que_cita_cidade_fica_no_pais_com_a_cidade_marcada(self):
        conexao = banco.abrir(":memory:")
        veiculo = cadastro.novo_veiculo("nacional", "Nacional", "https://exemplo.org", "portal", "nacional",
                                        [{"url": "https://exemplo.org/feed"}])
        item = {"titulo": "Chuva forte alaga ruas de Recife", "link": "https://exemplo.org/r", "guid": "r",
                "resumo": "", "autor": None, "publicado_em": None}
        coleta.guardar(conexao, veiculo, veiculo["feeds"][0], [item], [{"nome": "Recife", "uf": "PE"}])
        self.assertEqual(tuple(conexao.execute("SELECT escala, cidade, uf FROM noticias").fetchone()), ("pais", "Recife", "PE"))

    def test_cidade_ambigua_so_conta_no_mesmo_estado(self):
        natal = {"nome": "Natal", "uf": "RN", "ambigua": True}
        item = {"titulo": "Shoppings abrem mais cedo no Natal", "resumo": ""}
        self.assertIsNone(coleta.cidade_citada(item, {"abrangencia": "nacional", "uf": None}, [natal]))
        self.assertEqual(coleta.cidade_citada(item, {"abrangencia": "estadual", "uf": "RN"}, [natal]), natal)

    def test_nome_mais_longo_tem_prioridade(self):
        cidades = cadastro.carregar_cidades()
        item = {"titulo": "Romaria movimenta Juazeiro do Norte", "resumo": ""}
        self.assertEqual(coleta.cidade_citada(item, {"abrangencia": "nacional", "uf": None}, cidades)["nome"],
                         "Juazeiro do Norte")

    def test_noticia_com_duas_cidades_guarda_as_duas(self):
        conexao = banco.abrir(":memory:")
        veiculo = cadastro.novo_veiculo("g1-pe", "g1 PE", "https://exemplo.org", "portal", "estadual",
                                        [{"url": "https://exemplo.org/feed"}], uf="PE")
        item = {"titulo": "Chuva alaga ruas de Olinda e Recife", "link": "https://exemplo.org/c", "guid": "c",
                "resumo": "", "autor": None, "publicado_em": None}
        coleta.guardar(conexao, veiculo, veiculo["feeds"][0], [item], cadastro.carregar_cidades())
        linha = conexao.execute("SELECT escala, cidade, cidades FROM noticias").fetchone()
        self.assertEqual((linha["escala"], linha["cidade"]), ("cidade", "Olinda"))
        self.assertEqual([c["nome"] for c in json.loads(linha["cidades"])], ["Olinda", "Recife"])

    def test_nome_menor_nao_casa_dentro_do_maior(self):
        cidades = [{"nome": "Juazeiro do Norte", "uf": "CE"}, {"nome": "Juazeiro", "uf": "BA"}]
        item = {"titulo": "Romaria movimenta Juazeiro do Norte", "resumo": ""}
        achadas = coleta.cidades_citadas(item, {"abrangencia": "nacional", "uf": None}, cidades)
        self.assertEqual([c["nome"] for c in achadas], ["Juazeiro do Norte"])

    def test_banco_antigo_ganha_a_coluna_cidades(self):
        import sqlite3, tempfile, pathlib
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = pathlib.Path(pasta) / "farol.db"
            antigo = sqlite3.connect(arquivo)
            antigo.execute("CREATE TABLE noticias (id INTEGER PRIMARY KEY, veiculo_id TEXT NOT NULL, titulo TEXT NOT NULL, "
                           "link TEXT NOT NULL UNIQUE, guid TEXT, resumo TEXT, autor TEXT, publicado_em TEXT, "
                           "coletado_em TEXT NOT NULL, escala TEXT NOT NULL, uso TEXT NOT NULL DEFAULT 'noticias', "
                           "uf TEXT, cidade TEXT)")
            antigo.commit()
            antigo.close()
            conexao = banco.abrir(arquivo)
            self.assertIn("cidades", [c["name"] for c in conexao.execute("PRAGMA table_info(noticias)")])
            conexao.close()

    def test_cidade_nao_casa_parte_de_palavra(self):
        veiculo = {"abrangencia": "estadual", "uf": "SE"}
        item = {"titulo": "Aracajuanos lotam a praia", "resumo": ""}
        self.assertIsNone(coleta.cidade_citada(item, veiculo, [{"nome": "Aracaju", "uf": "SE"}]))


if __name__ == "__main__":
    unittest.main()


class TestImagens(unittest.TestCase):
    def test_media_content_do_feed(self):
        rss = b"""<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><item>
          <title>Com foto</title><link>https://exemplo.org/f</link>
          <media:content url="http://img.exemplo.org/a.jpg" medium="image"/>
        </item></channel></rss>"""
        self.assertEqual(feeds.ler(rss)[0]["imagem"], "https://img.exemplo.org/a.jpg")

    def test_enclosure_e_img_no_texto(self):
        rss = b"""<rss><channel>
          <item><title>A</title><link>https://exemplo.org/a</link>
            <enclosure url="https://img.exemplo.org/b.png" type="image/png"/></item>
          <item><title>B</title><link>https://exemplo.org/b</link>
            <description>&lt;img src="//img.exemplo.org/c.webp"&gt; texto</description></item>
          <item><title>C</title><link>https://exemplo.org/c</link><description>sem foto</description></item>
        </channel></rss>"""
        self.assertEqual([i["imagem"] for i in feeds.ler(rss)],
                         ["https://img.exemplo.org/b.png", "https://img.exemplo.org/c.webp", None])

    def test_imagem_da_pagina(self):
        from coletor import imagens
        pagina = """<head><meta name="twitter:image" content="https://x.org/t.jpg">
          <meta content="https://x.org/og.jpg?a=1&amp;b=2" property="og:image"></head>"""
        self.assertEqual(imagens.imagem_da_pagina(pagina), "https://x.org/og.jpg?a=1&b=2")
        self.assertIsNone(imagens.imagem_da_pagina("<head><title>nada</title></head>"))

    def test_completar_marca_paginas_sem_foto(self):
        from coletor import imagens
        conexao = banco.abrir(":memory:")
        veiculo = {"id": "v", "abrangencia": "nacional", "uf": None}
        for n in "abc":
            coleta.guardar(conexao, veiculo, {"escala": "pais"}, [{"titulo": n, "link": f"https://e.org/{n}", "guid": n,
                                                                    "resumo": "", "autor": None, "publicado_em": None}])
        paginas = {"https://e.org/a": '<meta property="og:image" content="https://e.org/a.jpg">',
                   "https://e.org/b": "<p>sem foto</p>", "https://e.org/c": None}
        achadas = imagens.completar(conexao, list(paginas), baixar=paginas.get)
        self.assertEqual(achadas, 1)
        fotos = dict(conexao.execute("SELECT link, imagem FROM noticias"))
        self.assertEqual(fotos, {"https://e.org/a": "https://e.org/a.jpg", "https://e.org/b": "", "https://e.org/c": None})


class TestFeedsComDefeito(unittest.TestCase):
    def test_espaco_antes_e_entidades_html(self):
        rss = b"""
  <?xml version="1.0"?><rss><channel><item><title>Rond&ocirc;nia &amp; Acre & cia</title>
  <link>https://e.org/a</link></item></channel></rss>"""
        self.assertEqual(feeds.ler(rss)[0]["titulo"], "Rondônia & Acre & cia")

    def test_item_quebrado_nao_derruba_o_feed(self):
        rss = b"""<rss><channel>
          <item><title>Boa</title><link>https://e.org/a</link><dc:creator>Ana</dc:creator></item>
          <item><title>Quebrada<b></title><link>https://e.org/b</link></item>
        </channel></rss>"""
        itens = feeds.ler(rss)
        self.assertEqual([i["titulo"] for i in itens], ["Boa"])
        self.assertEqual(itens[0]["autor"], "Ana")
