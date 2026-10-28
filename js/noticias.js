// O Farol — "Últimas notícias" da página inicial.
// Lê as notícias reais exportadas pelo coletor (dados/noticias.json). Se o arquivo não
// carregar (por exemplo, com o HTML aberto direto do disco), mostra os casos de exemplo do painel.

(function (m, agentes, casos) {
  var ESCALAS = ['cidade', 'estado', 'pais', 'mundo'];
  var POR_ABA = 5;
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

    var meta = el('p', 'noticia__meta');
    meta.appendChild(el('span', 'rotulo rotulo--aguardando', 'Aguardando análise'));
    meta.appendChild(document.createTextNode(n.veiculo + (n.publicado_em ? ' · ' + tempoDesde(n.publicado_em) : '')));
    li.appendChild(meta);
    return li;
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

    var atualizado = new Date(dados.gerado_em).toLocaleString('pt-BR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    legenda.replaceChildren(
      document.createTextNode('Notícias reais de ' + dados.veiculos.length + ' veículos, coletadas em ' + atualizado +
        '. Os títulos levam ao site de cada veículo. A análise do painel ainda não roda nestas notícias. '),
      linkEntendaRotulos());

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

  fetch('dados/noticias.json', { cache: 'no-store' })
    .then(function (r) {
      if (!r.ok) throw new Error('noticias.json respondeu ' + r.status);
      return r.json();
    })
    .then(mostrarReais)
    .catch(mostrarExemplos);
})(Farol.metodologia, Farol.agentes, Farol.casos);
