// O Farol — interface do painel de verificação (painel.html)

(function (m, agentes, casos, config) {
  var TEMAS = { local: 'Local', saude: 'Saúde', seguranca: 'Segurança', politica: 'Política', eleicoes: 'Eleições', economia: 'Economia', internacional: 'Internacional' };
  var POSICAO_PADRAO = { confirma: 'Confirma', diverge: 'Diverge' };
  var calmo = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var ESPERA = calmo ? 0 : 450;

  var lista = document.getElementById('lista-casos');
  var area = document.getElementById('caso');
  var atual = null;

  // Cria elementos sem innerHTML: os textos dos casos são dados, nunca marcação
  function el(tag, props) {
    var no = document.createElement(tag);
    props = props || {};
    if (props.classe) no.className = props.classe;
    if (props.texto != null) no.textContent = props.texto;
    Object.keys(props.attrs || {}).forEach(function (k) { no.setAttribute(k, props.attrs[k]); });
    for (var i = 2; i < arguments.length; i++) {
      var filho = arguments[i];
      if (filho == null || filho === false) continue;
      if (Array.isArray(filho)) filho.forEach(function (f) { if (f) no.appendChild(f); });
      else no.appendChild(typeof filho === 'string' ? document.createTextNode(filho) : filho);
    }
    return no;
  }

  function rotulo(id) {
    return el('span', { classe: 'rotulo rotulo--' + id, texto: m.ROTULOS[id] });
  }

  function listaDeTextos(itens, classe) {
    return el('ul', { classe: classe }, itens.map(function (t) { return el('li', { texto: t }); }));
  }

  function esperar(ms) {
    return new Promise(function (ok) { setTimeout(ok, ms); });
  }

  // Lista de casos
  casos.forEach(function (caso) {
    var botao = el('button', { classe: 'casos__botao', attrs: { type: 'button', 'data-caso': caso.id } },
      el('span', { classe: 'casos__tema', texto: TEMAS[caso.tema] + (caso.tipo === 'opiniao' ? ' · opinião' : '') }),
      el('span', { classe: 'casos__titulo', texto: caso.titulo }));
    botao.addEventListener('click', function () {
      selecionar(caso);
      // Em tela estreita a lista fica acima do caso: leva o leitor até o caso escolhido
      if (window.matchMedia && window.matchMedia('(max-width: 960px)').matches) {
        area.scrollIntoView({ behavior: calmo ? 'auto' : 'smooth', block: 'start' });
      }
    });
    lista.appendChild(el('li', null, botao));
  });

  function ficha(caso) {
    var o = caso.original;
    var a = caso.atribuicao;
    var atrib = [a.autor ? 'autor identificado' : 'sem autor', a.dataPublicacao ? 'data de publicação' : 'sem data de publicação', a.dataAtualizacao ? 'data de atualização' : 'sem data de atualização'];
    var checagens = caso.checagens.length
      ? caso.checagens.map(function (c) { return c.organizacao + (c.signatariaIFCN ? ' (signatária IFCN)' : ' (não signatária)') + ': ' + c.veredito + ', ' + c.data; }).join(' · ')
      : 'Nenhuma';

    function linha(termo, valor) {
      return [el('dt', { texto: termo }), el('dd', { texto: valor })];
    }

    return el('dl', { classe: 'ficha' },
      linha('Veículo original', o.nome + ' · linha declarada: ' + o.linha + ' · nota ' + (o.notaVeiculo == null ? 'em avaliação' : o.notaVeiculo)),
      linha('Fonte primária', caso.fontePrimaria ? caso.fontePrimaria.descricao : 'Nenhuma citada'),
      linha('Atribuição', atrib.join(', ')),
      linha('Checagens', checagens),
      linha('Alertas', caso.alertas.length ? caso.alertas.map(function (x) { return m.ALERTAS[x]; }).join(', ') : 'Nenhum'));
  }

  function tabelaCoberturas(caso) {
    if (!caso.coberturas.length) return el('p', { classe: 'caso__vazio', texto: 'Nenhum outro veículo publicou sobre este fato.' });
    var linhas = caso.coberturas.map(function (c) {
      var posicao = c.confirma ? POSICAO_PADRAO.confirma : POSICAO_PADRAO.diverge + ': ' + c.versao;
      return el('tr', null,
        el('td', { texto: c.veiculo }), el('td', { texto: c.grupo }), el('td', { texto: c.linha }),
        el('td', { texto: c.apuracaoPropria ? 'Sim' : 'Não (reprodução)' }), el('td', { texto: posicao }));
    });
    return el('div', { classe: 'tabela-rolagem' },
      el('table', { classe: 'tabela' },
        el('caption', { texto: 'Como outros veículos cobriram o fato' }),
        el('thead', null, el('tr', null, ['Veículo', 'Grupo', 'Linha declarada', 'Apuração própria', 'Posição'].map(function (t) { return el('th', { texto: t, attrs: { scope: 'col' } }); }))),
        el('tbody', null, linhas)));
  }

  function selecionar(caso) {
    atual = caso;
    if (window.history && history.replaceState) history.replaceState(null, '', '#caso-' + caso.id);
    Array.prototype.forEach.call(lista.querySelectorAll('.casos__botao'), function (b) {
      b.setAttribute('aria-current', b.getAttribute('data-caso') === caso.id ? 'true' : 'false');
    });

    var modo = el('select', { attrs: { id: 'modo' } },
      el('option', { texto: 'Demonstração (regras locais)', attrs: { value: 'demonstracao' } }),
      el('option', { texto: 'Modelos de IA (requer servidor)', attrs: { value: 'remoto' } }));
    var botao = el('button', { classe: 'botao botao--escuro', texto: 'Analisar com o painel', attrs: { type: 'button' } });
    var resultado = el('div', { classe: 'resultado', attrs: { id: 'resultado' } });
    botao.addEventListener('click', function () { analisar(caso, modo.value, botao, resultado); });

    area.replaceChildren(
      el('p', { classe: 'caso__meta', texto: 'Caso fictício · ' + TEMAS[caso.tema] }),
      el('h2', { classe: 'caso__titulo', texto: caso.titulo }),
      el('p', { classe: 'caso__afirmacao' }, el('strong', { texto: 'Afirmação central: ' }), caso.afirmacao),
      el('blockquote', { classe: 'caso__trecho', texto: caso.trecho }),
      ficha(caso),
      tabelaCoberturas(caso),
      el('div', { classe: 'caso__acoes' },
        el('label', { classe: 'caso__modo', attrs: { for: 'modo' } }, 'Agentes', modo),
        botao),
      resultado);
  }

  function cartaoAgente(agente) {
    var modelo = config.modelos[agente.id];
    return el('article', { classe: 'agente agente--aguardando', attrs: { 'data-agente': agente.id } },
      el('h4', { texto: agente.nome }),
      el('p', { classe: 'agente__papel', texto: agente.papel }),
      el('p', { classe: 'agente__modelo', texto: modelo.modelo + (modelo.empresa !== 'O Farol' ? ' · ' + modelo.empresa : '') }),
      el('p', { classe: 'agente__estado', texto: 'Aguardando…' }));
  }

  function preencherAgente(cartao, p) {
    cartao.className = 'agente';
    var conteudo = [
      el('p', { classe: 'agente__sugestao' }, rotulo(p.rotuloSugerido), el('span', { classe: 'agente__confianca', texto: 'confiança ' + Math.round(p.confianca * 100) + '%' })),
      listaDeTextos(p.motivos, 'agente__motivos')
    ];
    if (p.provas.length) {
      conteudo.push(el('p', { classe: 'agente__rotulo-provas', texto: 'Provas citadas' }), listaDeTextos(p.provas, 'agente__provas'));
    }
    cartao.querySelector('.agente__estado').replaceWith.apply(cartao.querySelector('.agente__estado'), conteudo);
  }

  function tabelaPontuacao(pontuacao) {
    var linhas = pontuacao.itens.map(function (i) {
      var barra = i.max > 0
        ? el('span', { classe: 'barra', attrs: { 'aria-hidden': 'true' } }, el('span', { classe: 'barra__preenchida', attrs: { style: 'width:' + Math.round(i.pontos / i.max * 100) + '%' } }))
        : null;
      return el('tr', null,
        el('th', { texto: i.sinal, attrs: { scope: 'row' } }),
        el('td', { texto: i.detalhe }),
        el('td', { classe: 'tabela__pontos' }, (i.pontos > 0 ? '+' : i.pontos < 0 ? '−' : '') + Math.abs(i.pontos) + (i.max > 0 ? ' de ' + i.max : ''), barra));
    });
    linhas.push(el('tr', { classe: 'tabela__total' },
      el('th', { texto: 'Total', attrs: { scope: 'row' } }), el('td'), el('td', { classe: 'tabela__pontos', texto: pontuacao.total + ' de 100' })));
    return el('div', { classe: 'tabela-rolagem' },
      el('table', { classe: 'tabela' },
        el('caption', { texto: 'Pontuação pela metodologia' }),
        el('thead', null, el('tr', null, ['Sinal', 'O que encontramos', 'Pontos'].map(function (t) { return el('th', { texto: t, attrs: { scope: 'col' } }); }))),
        el('tbody', null, linhas)));
  }

  function nomeAgente(id) {
    return agentes.LISTA.filter(function (a) { return a.id === id; })[0].nome;
  }

  function caixaDecisao(caso, decisao, pareceres) {
    var relator = decisao.destino === 'relator';
    var consenso = decisao.consenso
      ? 'Os quatro agentes concordaram.'
      : 'Os agentes divergiram: ' + pareceres.map(function (p) {
        return nomeAgente(p.agente) + ' sugeriu ' + m.ROTULOS[p.rotuloSugerido];
      }).join('; ') + '.';

    return el('section', { classe: 'decisao decisao--' + decisao.destino, attrs: { 'aria-labelledby': 'decisao-titulo' } },
      el('h3', { texto: 'Decisão do painel', attrs: { id: 'decisao-titulo' } }),
      el('p', { classe: 'decisao__rotulo' }, rotulo(decisao.rotulo)),
      listaDeTextos(decisao.motivos, 'decisao__motivos'),
      el('p', { classe: 'decisao__consenso', texto: consenso }),
      el('div', { classe: 'decisao__destino' },
        el('strong', { texto: relator ? 'Decidido pelo Relator de IA' : 'Aplicado automaticamente' }),
        decisao.motivosDestino.length
          ? listaDeTextos(decisao.motivosDestino)
          : el('p', { texto: 'Todos os agentes concordaram, e o Auditor de regras aceitou as provas.' })),
      el('p', { classe: 'decisao__contestar' },
        'Discorda desta avaliação? ', el('a', { texto: 'Conteste com as suas provas', attrs: { href: 'contestar.html#caso-' + caso.id } }), '.'));
  }

  function analisar(caso, modo, botao, resultado) {
    botao.disabled = true;
    var cartoes = agentes.LISTA.map(cartaoAgente);
    resultado.replaceChildren(
      el('h3', { classe: 'resultado__titulo', texto: 'Pareceres dos agentes' }),
      el('div', { classe: 'agentes' }, cartoes));

    var pareceres = [];
    var cadeia = Promise.resolve();
    agentes.LISTA.forEach(function (agente, i) {
      cadeia = cadeia.then(function () {
        cartoes[i].querySelector('.agente__estado').textContent = 'Analisando…';
        return Promise.all([agentes.obterParecer(agente, caso, modo), esperar(ESPERA)]);
      }).then(function (r) {
        pareceres.push(r[0]);
        preencherAgente(cartoes[i], r[0]);
      });
    });

    cadeia.then(function () {
      if (atual !== caso) return;
      var decisao = agentes.decidir(caso, pareceres);
      resultado.appendChild(tabelaPontuacao(decisao.pontuacao));
      resultado.appendChild(caixaDecisao(caso, decisao, pareceres));
    }).catch(function (erro) {
      resultado.appendChild(el('p', { classe: 'aviso aviso--erro' },
        el('strong', { texto: 'Não foi possível consultar os modelos. ' }),
        erro.message + ' Use o modo demonstração enquanto o servidor não estiver configurado.'));
    }).then(function () { botao.disabled = false; });
  }

  // Abre o caso indicado no endereço (ex.: painel.html#caso-escolas), vindo da página inicial
  var pedido = casos.filter(function (c) { return location.hash === '#caso-' + c.id; })[0];
  selecionar(pedido || casos[0]);
  if (pedido) area.scrollIntoView();
})(Farol.metodologia, Farol.agentes, Farol.casos, Farol.config);
