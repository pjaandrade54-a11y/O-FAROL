// O Farol — "Últimas notícias" da página inicial.
// Lê as notícias reais exportadas pelo coletor (dados/noticias.json), com o rótulo do conselho de IA
// quando a notícia já foi analisada. Se o arquivo não carregar (por exemplo, com o HTML aberto direto
// do disco), mostra os casos de exemplo do painel. Com a página aberta, busca notícias novas sozinha.

(function (m, agentes, casos) {
  var ESCALAS = ['cidade', 'estado', 'pais', 'mundo'];
  var POR_ABA = 5;
  var RECARREGAR_MS = 5 * 60 * 1000; // a coleta roda a cada 30 minutos; olhar a cada 5 pega a nova logo
  var ultimaBusca = 0;
  var legenda = document.getElementById('painel-legenda');

  function el(tag, classe, texto) {
    var no = document.createElement(tag);
    if (classe) no.className = classe;
    if (texto != null) no.textContent = texto;
    return no;
  }

  function linkEntendaRotulos() {
    var a = el('a', null, 'Entenda os rótulos');
    a.href = 'metodologia.html#rotulos';
    return a;
  }

  function tempoDesde(iso) {
    var minutos = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
    if (minutos < 60) return 'há ' + minutos + ' min';
    var horas = Math.floor(minutos / 60);
    if (horas < 24) return 'há ' + horas + ' h';
    var dias = Math.floor(horas / 24);
    return dias === 1 ? 'há 1 dia' : 'há ' + dias + ' dias';
  }

  function preencher(porEscala, montar) {
    ESCALAS.forEach(function (escala) {
      var lista = document.getElementById('lista-' + escala);
      if (!lista) return;
      var itens = (porEscala[escala] || []).slice(0, POR_ABA);
      lista.replaceChildren();
      if (!itens.length) {
        var vazio = el('li', 'noticia');
        vazio.appendChild(el('p', 'noticia__vazia', 'Nenhuma notícia nesta aba ainda.'));
        lista.appendChild(vazio);
        return;
      }
      itens.forEach(function (item) { lista.appendChild(montar(item, escala)); });
    });
  }

  // Notícias reais: o link leva ao site do veículo; o painel ainda não analisa estas notícias
  function noticiaReal(n, escala) {
    var nomes = { cidade: 'Cidade · ' + (n.cidade || ''), estado: 'Estado · ' + (n.uf || ''), pais: 'País', mundo: 'Mundo' };
    var li = el('li', 'noticia');
    li.appendChild(el('p', 'noticia__escala', nomes[escala]));

    var titulo = el('h3');
    if (/^https?:\/\//i.test(n.link)) {
      var link = el('a', null, n.titulo);
      link.href = n.link;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      titulo.appendChild(link);
    } else {
      titulo.textContent = n.titulo;
    }
    li.appendChild(titulo);

    var a = n.analise;
    var meta = el('p', 'noticia__meta');
    if (a && m.ROTULOS[a.rotulo]) {
      var selo = a.destino === 'conselho' ? ' · provisório' : a.destino === 'humano' ? ' · conselho' : '';
      meta.appendChild(el('span', 'rotulo rotulo--' + a.rotulo, m.ROTULOS[a.rotulo] + selo));
    } else {
      meta.appendChild(el('span', 'rotulo rotulo--aguardando', 'Aguardando análise'));
    }
    meta.appendChild(document.createTextNode(n.veiculo + (n.publicado_em ? ' · ' + tempoDesde(n.publicado_em) : '')));
    li.appendChild(meta);
    if (a && m.ROTULOS[a.rotulo]) li.appendChild(detalhesAnalise(a));
    return li;
  }

  function linkExterno(texto, href) {
    if (!/^https?:\/\//i.test(href || '')) return document.createTextNode(texto);
    var link = el('a', null, texto);
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    return link;
  }

  function lista(classe, textos) {
    var ul = el('ul', classe);
    textos.forEach(function (t) { ul.appendChild(el('li', null, t)); });
    return ul;
  }

  // "Por que este rótulo?": a decisão, cada parecer e as provas citadas, com link para a fonte
  function detalhesAnalise(a) {
    var caixa = el('details', 'analise');
    caixa.appendChild(el('summary', null, 'Por que este rótulo?'));
    caixa.appendChild(lista('analise__motivos', a.motivos.concat(a.motivosDestino || [])));
    if (a.destino === 'conselho') {
      caixa.appendChild(el('p', 'analise__nota', 'Rótulo provisório: o caso foi enviado ao conselho humano.'));
    }
    a.pareceres.forEach(function (p) {
      var bloco = el('div', 'analise__parecer');
      var titulo = el('p', 'analise__agente');
      titulo.appendChild(el('strong', null, p.nome));
      titulo.appendChild(document.createTextNode(' · ' + p.modelo + ': ' + (m.ROTULOS[p.rotuloSugerido] || 'sem rótulo') +
        (typeof p.confianca === 'number' ? ', confiança ' + Math.round(p.confianca * 100) + '%' : '')));
      bloco.appendChild(titulo);
      bloco.appendChild(lista('analise__lista', p.motivos));
      if (p.provas.length) {
        var provas = el('ul', 'analise__lista analise__provas');
        p.provas.forEach(function (prova) {
          var li = el('li');
          li.appendChild(linkExterno(prova.veiculo, prova.link));
          li.appendChild(document.createTextNode(': ' + prova.explicacao));
          provas.appendChild(li);
        });
        bloco.appendChild(provas);
      }
      if (p.descartado.length) {
        bloco.appendChild(lista('analise__lista analise__descartado', p.descartado.map(function (x) {
          return 'Descartado pelo Auditor de regras: ' + x;
        })));
      }
      caixa.appendChild(bloco);
    });
    return caixa;
  }

  // Casos de exemplo: o rótulo vem do painel e o link abre a análise
  function noticiaExemplo(caso) {
    var pareceres = agentes.LISTA.map(function (a) { return a.analisar(caso); });
    var decisao = agentes.decidir(caso, pareceres);
    var nomes = { cidade: 'Cidade · Vila Serena', estado: 'Estado', pais: 'País', mundo: 'Mundo' };

    var li = el('li', 'noticia');
    li.appendChild(el('p', 'noticia__escala', nomes[caso.escala]));
    var titulo = el('h3');
    var link = el('a', null, caso.titulo);
    link.href = 'painel.html#caso-' + caso.id;
    titulo.appendChild(link);
    li.appendChild(titulo);

    var meta = el('p', 'noticia__meta');
    meta.appendChild(el('span', 'rotulo rotulo--' + decisao.rotulo,
      m.ROTULOS[decisao.rotulo] + (decisao.destino === 'conselho' ? ' · provisório' : '')));
    var horas = caso.minutos < 60 ? 'há ' + caso.minutos + ' min' : 'há ' + Math.floor(caso.minutos / 60) + ' h';
    meta.appendChild(document.createTextNode(caso.original.nome + ' · ' + horas));
    li.appendChild(meta);
    return li;
  }

  function mostrarReais(dados) {
    preencher(dados.escalas, noticiaReal);

    var visiveis = ESCALAS.reduce(function (t, e) { return t.concat((dados.escalas[e] || []).slice(0, POR_ABA)); }, []);
    var analisadas = visiveis.filter(function (n) { return n.analise; }).length;
    var data = new Date(dados.gerado_em);
    var atualizado = data.toLocaleString('pt-BR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    var analise = analisadas === visiveis.length ? 'Todas já foram analisadas. '
      : analisadas ? analisadas + ' de ' + visiveis.length + ' já foram analisadas; as demais aguardam a próxima rodada. '
      : 'Estas notícias ainda não foram analisadas. ';
    legenda.replaceChildren(
      document.createTextNode('Notícias reais de ' + dados.veiculos.length + ' veículos, coletadas em ' + atualizado +
        '. Os títulos levam ao site de cada veículo. ' + analise),
      linkEntendaRotulos());
    document.querySelectorAll('[data-atualizado]').forEach(function (no) {
      no.textContent = ' · atualizado às ' + data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    });

    var titulo = document.getElementById('fontes-titulo');
    var lista = document.getElementById('lista-veiculos');
    if (titulo && lista) {
      titulo.textContent = 'Veículos acompanhados';
      lista.replaceChildren.apply(lista, dados.veiculos.map(function (v) { return el('li', null, v.nome); }));
    }
  }

  function mostrarExemplos() {
    var porEscala = {};
    casos.slice().sort(function (a, b) { return a.minutos - b.minutos; }).forEach(function (c) {
      (porEscala[c.escala] = porEscala[c.escala] || []).push(c);
    });
    preencher(porEscala, noticiaExemplo);
    legenda.replaceChildren(
      document.createTextNode('Notícias de exemplo (fictícias). Clique em uma para ver a análise do painel. '),
      linkEntendaRotulos());
  }

  var temReais = false;

  function buscar() {
    ultimaBusca = Date.now();
    return fetch('dados/noticias.json', { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('noticias.json respondeu ' + r.status);
        return r.json();
      })
      .then(function (dados) {
        temReais = true;
        mostrarReais(dados);
      })
      .catch(function () {
        // Numa atualização que falha (sem internet, por exemplo), as notícias já na tela ficam
        if (!temReais) mostrarExemplos();
      });
  }

  // Não troca a lista enquanto o leitor está com uma explicação aberta
  function atualizarSePossivel() {
    if (document.hidden || Date.now() - ultimaBusca < RECARREGAR_MS) return;
    if (document.querySelector('.painel details[open]')) return;
    buscar();
  }

  buscar();
  setInterval(atualizarSePossivel, 60 * 1000);
  document.addEventListener('visibilitychange', atualizarSePossivel);
})(Farol.metodologia, Farol.agentes, Farol.casos);
