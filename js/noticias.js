// O Farol — "Últimas notícias" da página inicial e a escolha da cidade do leitor.
// Lê as notícias reais exportadas pelo coletor (dados/noticias.json), com o rótulo da análise quando a
// notícia já foi analisada. As abas Cidade e Estado mostram a cidade e o estado escolhidos pelo leitor.
// Se o arquivo não carregar (por exemplo, com o HTML aberto direto do disco), mostra os casos de exemplo
// do painel. Com a página aberta, busca notícias novas sozinha.

(function (m, agentes, casos) {
  var ESCALAS = ['cidade', 'estado', 'pais', 'mundo'];
  var POR_ABA = 5;
  var RECARREGAR_MS = 5 * 60 * 1000; // a coleta roda a cada 30 minutos; olhar a cada 5 pega a nova logo
  var ultimaBusca = 0;
  var legenda = document.getElementById('painel-legenda');
  var ultimosDados = null; // arquivo geral (país, mundo, veículos, cidades)
  var ultimoEstado = null;  // arquivo do estado escolhido (cidades e estado)
  var ESTADOS = {
    AC: 'Acre', AL: 'Alagoas', AP: 'Amapá', AM: 'Amazonas', BA: 'Bahia', CE: 'Ceará', DF: 'Distrito Federal',
    ES: 'Espírito Santo', GO: 'Goiás', MA: 'Maranhão', MT: 'Mato Grosso', MS: 'Mato Grosso do Sul',
    MG: 'Minas Gerais', PA: 'Pará', PB: 'Paraíba', PR: 'Paraná', PE: 'Pernambuco', PI: 'Piauí',
    RJ: 'Rio de Janeiro', RN: 'Rio Grande do Norte', RS: 'Rio Grande do Sul', RO: 'Rondônia', RR: 'Roraima',
    SC: 'Santa Catarina', SP: 'São Paulo', SE: 'Sergipe', TO: 'Tocantins'
  };

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

  function preencher(porEscala, montar, vazios) {
    ESCALAS.forEach(function (escala) {
      var lista = document.getElementById('lista-' + escala);
      if (!lista) return;
      var itens = (porEscala[escala] || []).slice(0, POR_ABA);
      lista.replaceChildren();
      if (!itens.length) {
        var vazio = el('li', 'noticia');
        vazio.appendChild(el('p', 'noticia__vazia', (vazios && vazios[escala]) || 'Nenhuma notícia nesta aba ainda.'));
        lista.appendChild(vazio);
        return;
      }
      itens.forEach(function (item) { lista.appendChild(montar(item, escala)); });
    });
  }

  // Notícias reais: o link leva ao site do veículo; o painel ainda não analisa estas notícias
  function noticiaReal(n, escala) {
    var nomes = { cidade: 'Cidade · ' + (n.cidade || n.uf || ''), estado: 'Estado · ' + (ESTADOS[n.uf] || n.uf || ''), pais: 'País', mundo: 'Mundo' };
    var li = el('li', 'noticia');
    // Notícia confirmada vem com a foto que o veículo anexou; se a foto não carregar, o cartão fica sem ela
    if (n.imagem && /^https:\/\//i.test(n.imagem)) {
      li.classList.add('noticia--foto');
      var foto = el('figure', 'noticia__foto');
      var img = el('img');
      img.src = n.imagem;
      img.alt = '';
      img.loading = 'lazy';
      img.decoding = 'async';
      img.referrerPolicy = 'no-referrer';
      img.addEventListener('load', function () { foto.classList.add('carregou'); });
      img.addEventListener('error', function () { li.classList.remove('noticia--foto'); foto.remove(); });
      foto.appendChild(img);
      li.appendChild(foto);
    }
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
    var acoes = el('div', 'noticia__acoes');
    if (a && m.ROTULOS[a.rotulo]) acoes.appendChild(detalhesAnalise(a));
    if (/^https?:\/\//i.test(n.link)) acoes.appendChild(botaoCompartilhar(n, a));
    li.appendChild(acoes);
    return li;
  }

  // Compartilhar no WhatsApp: título, rótulo, link do veículo e o convite para o Farol
  function botaoCompartilhar(n, a) {
    var selo = a && m.ROTULOS[a.rotulo] ? ' [' + m.ROTULOS[a.rotulo] + ' no Farol]' : '';
    var texto = n.titulo + selo + '\n' + n.veiculo + ': ' + n.link +
      '\n\nAntes de repassar, confere no Farol: ' + location.origin + location.pathname;
    var link = el('a', 'compartilhar', 'Compartilhar');
    link.href = 'https://wa.me/?text=' + encodeURIComponent(texto);
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.setAttribute('aria-label', 'Compartilhar no WhatsApp: ' + n.titulo);
    return link;
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

  // Notícias da cidade e do estado escolhidos; sem cidade escolhida, a cidade-piloto (Aracaju)
  function filtrar(dados, local) {
    var cidade = (dados.escalas.cidade || []).filter(function (n) {
      return local.nome ? n.cidade === local.nome && (!local.uf || n.uf === local.uf) : n.uf === local.uf;
    });
    var estado = (dados.escalas.estado || []).filter(function (n) { return n.uf === local.uf; });
    return { cidade: cidade, estado: estado, pais: dados.escalas.pais || [], mundo: dados.escalas.mundo || [] };
  }

  // Escolha do leitor; uma escolha guardada por versão antiga do site (só o nome) é procurada na lista
  function localAtual() {
    var local = Farol.local.lerOuPadrao();
    if (!local.uf && ultimosDados) {
      local = encontrar(local.nome || '', ultimosDados.cidades || []) || { nome: 'Aracaju', uf: 'SE' };
      Farol.local.guardar(local);
    }
    return local;
  }

  // Junta o arquivo geral com o do estado (o arquivo geral antigo, com tudo dentro, também serve)
  function combinar(geral, estado) {
    if (geral.escalas.cidade) return geral;
    var escalas = { pais: geral.escalas.pais, mundo: geral.escalas.mundo, cidade: [], estado: [] };
    if (estado) { escalas.cidade = estado.escalas.cidade || []; escalas.estado = estado.escalas.estado || []; }
    return Object.assign({}, geral, { escalas: escalas });
  }

  function buscarEstado(uf) {
    if (!uf || (ultimosDados && ultimosDados.escalas.cidade)) return Promise.resolve(null);
    return fetch('dados/estados/' + uf + '.json', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  function mostrarReais(geral) {
    ultimosDados = geral;
    var dados = combinar(geral, ultimoEstado);
    var local = localAtual();
    var porEscala = filtrar(dados, local);
    var nomeEstado = ESTADOS[local.uf] || local.uf || 'seu estado';
    preencher(porEscala, noticiaReal, {
      cidade: local.nome
        ? 'Ainda não há notícias recentes de ' + local.nome + '. Veja a aba Estado.'
        : 'Escolha uma cidade para ver as notícias dela. Enquanto isso, veja a aba Estado.',
      estado: 'Estado: ' + nomeEstado + '. Ainda não há notícias estaduais recentes.'
    });

    var visiveis = ESCALAS.reduce(function (t, e) { return t.concat(porEscala[e].slice(0, POR_ABA)); }, []);
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

    // Veículos do estado do leitor primeiro; os nacionais e internacionais, resumidos
    var titulo = document.getElementById('fontes-titulo');
    var lista = document.getElementById('lista-veiculos');
    if (titulo && lista) {
      var doEstado = dados.veiculos.filter(function (v) { return v.uf && v.uf === local.uf; });
      var gerais = dados.veiculos.filter(function (v) { return !v.uf; });
      titulo.textContent = dados.veiculos.length + ' veículos acompanhados';
      var itens = doEstado.concat(gerais.slice(0, 10)).map(function (v) { return el('li', null, v.nome); });
      var resto = dados.veiculos.length - itens.length;
      if (resto > 0) itens.push(el('li', 'fontes__mais', 'e mais ' + resto + ' de outros estados'));
      lista.replaceChildren.apply(lista, itens);
    }
    preencherCidades(dados.cidades || []);
    document.dispatchEvent(new CustomEvent('farol:noticias', { detail: dados }));
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

  // Escolha da cidade (página inicial)
  var form = document.getElementById('form-local');
  var campo = document.getElementById('campo-local');
  var status = document.getElementById('status-local');
  var opcoes = document.getElementById('lista-cidades');

  function normalizar(texto) {
    return (texto || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  }

  function avisar(texto, erro) {
    if (!status) return;
    status.textContent = texto;
    status.classList.toggle('erro', !!erro);
  }

  function preencherCidades(cidades) {
    if (!opcoes || opcoes.childElementCount === cidades.length) return;
    opcoes.replaceChildren.apply(opcoes, cidades.map(function (c) {
      var o = document.createElement('option');
      o.value = c.nome + ' (' + c.uf + ')';
      return o;
    }));
  }

  // Aceita "Recife", "Recife (PE)", "Recife - PE", "Recife/PE", e também só o estado ("PE", "Pernambuco")
  function encontrar(texto, cidades) {
    var partes = texto.match(/^(.*?)(?:\s*[\(\-\/,]\s*([A-Za-z]{2})\)?)?\s*$/);
    var nome = normalizar(partes[1]);
    var uf = partes[2] ? partes[2].toUpperCase() : null;
    var achadas = cidades.filter(function (c) { return normalizar(c.nome) === nome && (!uf || c.uf === uf); });
    if (achadas.length) return { nome: achadas[0].nome, uf: achadas[0].uf };
    var estado = Object.keys(ESTADOS).filter(function (s) {
      return normalizar(s) === nome || normalizar(ESTADOS[s]) === nome;
    })[0];
    return estado ? { nome: null, uf: estado } : null;
  }

  function escolher(local, mensagem) {
    Farol.local.guardar(local);
    if (Farol.selecionarAba) Farol.selecionarAba(local.nome ? 0 : 1);
    avisar(mensagem);
    if (!ultimosDados) return;
    if (ultimoEstado && ultimoEstado.uf === local.uf) {
      mostrarReais(ultimosDados);
      return;
    }
    // Outro estado: baixa só o arquivo dele
    buscarEstado(local.uf).then(function (estado) {
      ultimoEstado = estado;
      mostrarReais(ultimosDados);
    });
  }

  // "trocar" no topo do painel leva ao campo da cidade
  var trocar = document.querySelector('.painel__local');
  if (trocar && campo) {
    trocar.addEventListener('click', function (e) {
      e.preventDefault();
      campo.scrollIntoView({ block: 'center', behavior: 'smooth' });
      campo.focus({ preventScroll: true });
    });
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var texto = campo.value.trim();
      if (!texto) return;
      var local = encontrar(texto, (ultimosDados && ultimosDados.cidades) || []);
      if (!local) {
        avisar('Ainda não acompanhamos “' + texto + '”. Escolha uma cidade da lista ou digite o seu estado.', true);
        return;
      }
      escolher(local, local.nome
        ? 'Mostrando as notícias de ' + local.nome + ' (' + local.uf + ').'
        : 'Mostrando as notícias do estado: ' + ESTADOS[local.uf] + '. Se a sua cidade estiver na lista, escolha-a também.');
    });
  }

  function distanciaKm(a, b) {
    var rad = Math.PI / 180;
    var x = (b.lon - a.lon) * rad * Math.cos((a.lat + b.lat) / 2 * rad);
    var y = (b.lat - a.lat) * rad;
    return Math.sqrt(x * x + y * y) * 6371;
  }

  var botaoLocalizacao = document.getElementById('usar-localizacao');
  if (botaoLocalizacao) {
    botaoLocalizacao.addEventListener('click', function () {
      if (!('geolocation' in navigator)) {
        avisar('Seu navegador não permite detectar a localização. Digite sua cidade.', true);
        return;
      }
      avisar('Detectando sua localização…');
      navigator.geolocation.getCurrentPosition(function (posicao) {
        // A localização é usada só aqui, no navegador, para achar a cidade acompanhada mais próxima
        var aqui = { lat: posicao.coords.latitude, lon: posicao.coords.longitude };
        var cidades = ((ultimosDados && ultimosDados.cidades) || []).filter(function (c) { return c.lat != null; });
        if (!cidades.length) {
          avisar('Não foi possível usar sua localização agora. Digite sua cidade.', true);
          return;
        }
        var perto = cidades.reduce(function (melhor, c) {
          var d = distanciaKm(aqui, c);
          return !melhor || d < melhor.d ? { c: c, d: d } : melhor;
        }, null);
        if (perto.d <= 40) {
          escolher({ nome: perto.c.nome, uf: perto.c.uf }, 'Você está em ' + perto.c.nome + ' (' + perto.c.uf + ') ou perto.');
        } else {
          escolher({ nome: null, uf: perto.c.uf }, 'Sua cidade ainda não está entre as acompanhadas; mostrando as notícias do estado: ' +
            ESTADOS[perto.c.uf] + '.');
        }
      }, function () {
        avisar('Não foi possível detectar sua localização. Digite sua cidade.', true);
      }, { timeout: 10000 });
    });
  }

  var temReais = false;

  function buscar() {
    ultimaBusca = Date.now();
    return fetch('dados/noticias.json', { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('noticias.json respondeu ' + r.status);
        return r.json();
      })
      .then(function (geral) {
        ultimosDados = geral;
        return buscarEstado(localAtual().uf).then(function (estado) {
          ultimoEstado = estado;
          temReais = true;
          mostrarReais(geral);
        });
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
