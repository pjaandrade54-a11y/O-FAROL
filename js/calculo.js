// O Farol — "Calcule você mesmo": o mesmo Cálculo de evidências do coletor (coletor/calculo.py), feito no
// navegador com as notícias carregadas no site. O servidor compara com todas as notícias de 72 horas; aqui a
// comparação é com as que o site publica, então os números podem diferir um pouco.

(function () {
  var LIMIAR_FATO = 0.48, SIMILARIDADE_FORTE = 0.80, CONFIANCA_CONFIRMADA = 0.70, LIMIAR_CHECAGEM = 0.50;
  var NUMEROS_DIFERENTES = 0.5, HORAS = 72, MINIMO_DE_PALAVRAS = 4, COMUM_DEMAIS = 0.05;
  var REPRODUCAO = 0.90, FATOR_REPRODUCAO = 0.6;
  var LIMIAR_OFICIAL = 0.45, LIMIAR_OFICIAL_ASSUNTO = 0.30, FATOR_DADOS_CONFEREM = 1.3, FATOR_DADOS_DIVERGEM = 0.6;
  var UNIDADES = { morto: 'mortos', morte: 'mortos', obito: 'mortos', ferido: 'feridos', preso: 'presos', prisao: 'presos',
    pessoa: 'pessoas', vitima: 'vitimas', caso: 'casos', voto: 'votos', vaga: 'vagas', ano: 'anos', dia: 'dias', hora: 'horas',
    km: 'km', tonelada: 'toneladas', '%': '%', 'por cento': '%', real: 'reais', escola: 'escolas', leito: 'leitos', casa: 'casas',
    familia: 'familias', desabrigado: 'desabrigados', desalojado: 'desalojados', municipio: 'municipios', cidade: 'municipios',
    aluno: 'alunos', estudante: 'alunos', veiculo: 'veiculos' };
  var MULTIPLICADOR = { mil: 1e3, milhao: 1e6, milhoes: 1e6, bilhao: 1e9, bilhoes: 1e9 };

  // Dados do texto: {unidade: Set de valores}, como "2 mortos", "R$ 18 milhões", "61 votos"
  function dados(n) {
    var saida = {}, texto = semAcento(((n.titulo || '') + ' ' + (n.resumo || '')).toLowerCase());
    var re = /(r\$\s*)?(\d+(?:[.,]\d+)*)\s*(milhoes|milhao|bilhoes|bilhao|mil\b)?\s*(%|por cento|[a-z]+)?/g, m;
    while ((m = re.exec(texto))) {
      var palavra = m[4], unidade = null;
      if (palavra) {
        var base = UNIDADES[palavra] ? palavra : (palavra.endsWith('s') ? palavra.slice(0, -1) : palavra);
        if (base === 'prisoe' || base === 'prisoes') base = 'prisao';
        unidade = UNIDADES[palavra] || UNIDADES[base];
      }
      if (m[1] && !unidade) unidade = 'reais';
      if (!unidade) continue;
      var valor = parseFloat(m[2].replace(/\./g, '').replace(',', '.')) * (MULTIPLICADOR[m[3]] || 1);
      (saida[unidade] = saida[unidade] || new Set()).add(valor);
    }
    return saida;
  }

  function cruzarDados(meus, deles) {
    var comuns = Object.keys(meus).filter(function (u) { return deles[u]; });
    var conferem = comuns.some(function (u) { return [...meus[u]].some(function (v) { return deles[u].has(v); }); });
    return { conferem: conferem, divergem: comuns.length > 0 && !conferem };
  }
  var FATOR = { oficial: 1.5, autor: 1.15, tipos: 1.15, vaga: 0.7, alarme: 0.75, semData: 0.9 };
  var FONTE_OFICIAL_NOME = /(^|[^\p{L}])(pol[ií]cia (militar|civil|federal|rodovi[aá]ria federal)|corpo de bombeiros|bombeiros|defesa civil|prefeitura|governo (federal|do estado|estadual)|minist[eé]rio|secretaria|tribunal|justi[cç]a eleitoral|c[aâ]mara (municipal|dos deputados)|senado|assembleia legislativa|banco central|receita federal|di[aá]rio oficial|caixa econ[oô]mica|instituto nacional)(?![\p{L}])/iu;
  var FONTE_OFICIAL_SIGLA = /\b(PM|PF|PRF|IBGE|Ipea|Inmet|Anvisa|Fiocruz|STF|STJ|TSE|TRE|TCU|TJ[A-Z]{0,2}|MPF|MP[A-Z]{2}|INSS|DOU|OMS|ONU|Ibama|ICMBio|Detran|SUS|Petrobras|Aneel|Anatel|Datafolha|Quaest)\b/;
  var ATRIBUICAO_VAGA = /(^|[^\p{L}])(fontes? (dizem|afirmam|apontam|ouvidas)|segundo rumores|rumores?|circula(m)? nas redes|viraliza|nas redes sociais|teria(m)? (sido|dito|feito)|supostamente|suposto|boato|dizem que)(?![\p{L}])/iu;
  var SENSACIONALISMO = /(^|[^\p{L}])(chocante|urgente|bomba|inacredit[aá]vel|absurdo|esc[aâ]ndalo|bizarro|voc[eê] n[aã]o vai acreditar|surpreende|revoltante|assustador|imperd[ií]vel|pol[eê]mica)(?![\p{L}])/iu;
  var CAIXA_ALTA_PERMITIDA = new Set(['VIDEO', 'VÍDEO', 'FOTOS', 'PODCAST', 'AO', 'VIVO', 'AGORA']);

  function sinaisDaNoticia(n, tiposDiferentes) {
    var titulo = n.titulo || '', texto = titulo + ' ' + (n.resumo || ''), sinais = [], m;
    if ((m = texto.match(FONTE_OFICIAL_NOME))) sinais.push(['cita fonte oficial (' + m[2] + ')', FATOR.oficial]);
    else if ((m = texto.match(FONTE_OFICIAL_SIGLA))) sinais.push(['cita fonte oficial (' + m[1] + ')', FATOR.oficial]);
    if (n.autor) sinais.push(['autor identificado', FATOR.autor]);
    if (tiposDiferentes) sinais.push(['confirmada por tipos diferentes de veículo', FATOR.tipos]);
    if ((m = texto.match(ATRIBUICAO_VAGA))) sinais.push(['atribuição vaga (“' + m[2] + '”)', FATOR.vaga]);
    var alarmes = [];
    if (titulo.indexOf('!') >= 0) alarmes.push('exclamação no título');
    if ((titulo.match(/[A-ZÀ-Ý]{5,}/g) || []).some(function (p) { return !CAIXA_ALTA_PERMITIDA.has(p); })) alarmes.push('palavra em caixa alta no título');
    if ((m = titulo.match(SENSACIONALISMO))) alarmes.push('termo sensacionalista (“' + m[2] + '”)');
    alarmes.slice(0, 2).forEach(function (a) { sinais.push([a, FATOR.alarme]); });
    if (!n.digitado && !n.publicado_em) sinais.push(['sem data de publicação', FATOR.semData]);
    return sinais;
  }

  function ajustar(base, sinais) {
    if (base <= 0) return 0;
    var b = Math.min(base, 0.999), chances = b / (1 - b);
    sinais.forEach(function (s) { chances *= s[1]; });
    return chances / (1 + chances);
  }
  var PESO_TIPO = { oficial: 0.95, agencia: 0.85, jornal: 0.9, tv: 0.9, radio: 0.85, revista: 0.85, portal: 0.75, blog: 0.55, checador: 0 };
  var PESO_PADRAO = 0.7;
  var VAZIAS = new Set(('a o as os um uma uns umas de da do das dos em na no nas nos por para pela pelo pelas pelos com sem sob ' +
    'e ou mas que se ao aos à às como mais menos sobre entre apos antes desde ainda ser sera serao foi foram ' +
    'esta este estao essa esse isso isto aquele aquela quando onde qual quais quem porque tambem muito muita ' +
    'muitos muitas outro outra outros outras mesmo mesma depois durante contra cada todo toda todos todas seu ' +
    'sua seus suas nosso nossa diz dizem afirma segundo anuncia apos ha tem teve sao veja confira saiba entenda ' +
    'video fotos ano anos dia dias hoje ontem amanha nesta neste nessa nesse pode podem vai vao deve devem ' +
    'noticia noticias apareceu primeiro post leia mais').split(' '));
  var OPINIAO_TITULO = /\b(opini[aã]o|artigo|coluna|editorial|cr[oô]nica)\b/i;
  var OPINIAO_LINK = /\/(opiniao|colunas?|colunistas?|artigos?|blogs?|editorial)\//i;
  var CHECAGEM_FALSO = /\b(fals[oa]s?|enganos[oa]s?|fake|sem provas|boato|mentira|mente|distorcid[oa]|fora de contexto|n[aã]o [eé] verdade)\b/i;
  var NOMES = { 'confirmada': 'Confirmada', 'em-apuracao': 'Em apuração', 'opiniao': 'Opinião ou análise',
    'dados-insuficientes': 'Dados insuficientes' };

  function semAcento(t) { return t.normalize('NFKD').replace(/[̀-ͯ]/g, ''); }

  function termos(texto, peso) {
    var contagem = new Map();
    (texto || '').match(/[\p{L}\p{N}_]+/gu)?.forEach(function (bruta, i) {
      var p = semAcento(bruta.toLowerCase());
      if (VAZIAS.has(p) || (p.length < 3 && !/^\d+$/.test(p))) return;
      if (p.length > 4 && p.endsWith('s') && !p.endsWith('ss')) p = p.slice(0, -1);
      var destaque = /^\d+$/.test(p) || (i > 0 && bruta[0] !== bruta[0].toLowerCase()) ? 1.5 : 1;
      contagem.set(p, (contagem.get(p) || 0) + peso * destaque);
    });
    return contagem;
  }

  function somar(a, b) { b.forEach(function (v, k) { a.set(k, (a.get(k) || 0) + v); }); return a; }

  function numeros(n) {
    var s = new Set();
    ((n.titulo || '') + ' ' + (n.resumo || '')).match(/\d[\d.,]*\d/g)?.forEach(function (x) { s.add(x.replace(/[.,]/g, '')); });
    return s;
  }

  function Corpus(noticias) {
    var brutos = noticias.map(function (n) { return somar(termos(n.titulo, 2), termos(n.resumo, 1)); });
    var df = new Map();
    brutos.forEach(function (c) { c.forEach(function (_, p) { df.set(p, (df.get(p) || 0) + 1); }); });
    var total = Math.max(1, noticias.length);
    this.idf = new Map();
    this.comum = new Set();
    var self = this;
    df.forEach(function (n, p) {
      self.idf.set(p, Math.log((total + 1) / (n + 1)) + 1);
      if (n > Math.max(5, total * COMUM_DEMAIS)) self.comum.add(p);
    });
    this.noticias = noticias;
    this.vetores = brutos.map(function (c) { return self.vetorDe(c); });
  }
  Corpus.prototype.vetorDe = function (contagem) {
    var v = new Map(), norma = 0, self = this;
    contagem.forEach(function (n, p) { if (n > 0) { var x = (1 + Math.log(n)) * (self.idf.get(p) || 1); v.set(p, x); norma += x * x; } });
    norma = Math.sqrt(norma) || 1;
    v.forEach(function (x, p) { v.set(p, x / norma); });
    return v;
  };
  Corpus.prototype.vetor = function (n) {
    var i = this.noticias.indexOf(n);
    return i >= 0 ? this.vetores[i] : this.vetorDe(somar(termos(n.titulo, 2), termos(n.resumo, 1)));
  };

  function grupo(v, id) { return (v && v.grupo) || id; }

  function classificar(alvo, corpus, veiculos) {
    if (OPINIAO_TITULO.test(alvo.titulo) || OPINIAO_LINK.test(alvo.link || '')) {
      return { rotulo: 'opiniao', confianca: null, linhas: [], motivo: 'O título ou o endereço indicam texto de opinião.' };
    }
    var va = corpus.vetor(alvo);
    var informativas = [...va.keys()].filter(function (p) { return !corpus.comum.has(p); });
    if (informativas.length < MINIMO_DE_PALAVRAS) {
      return { rotulo: 'dados-insuficientes', confianca: null, linhas: [], motivo: 'Poucas palavras para comparar.' };
    }
    var meusNumeros = numeros(alvo), quando = Date.parse(alvo.publicado_em || '') || null;
    var parecidas = [];
    corpus.noticias.forEach(function (n, i) {
      if (n === alvo || (alvo.veiculo_id && n.veiculo_id === alvo.veiculo_id) || n.link === alvo.link) return;
      var q = Date.parse(n.publicado_em || '');
      if (quando && q && Math.abs(quando - q) > HORAS * 3600 * 1000) return;
      var vb = corpus.vetores[i], s = 0;
      va.forEach(function (x, p) { s += x * (vb.get(p) || 0); });
      var deles = numeros(n), cortou = false, bruta = s;
      if (meusNumeros.size && deles.size && ![...meusNumeros].some(function (x) { return deles.has(x); })) {
        s *= NUMEROS_DIFERENTES; cortou = true;
      }
      if (s > 0.15 || bruta >= LIMIAR_OFICIAL_ASSUNTO) parecidas.push({ s: s, bruta: bruta, n: n, cortou: cortou });
    });
    parecidas.sort(function (a, b) { return b.s - a.s; });

    var original = veiculos[alvo.veiculo_id];
    var gOriginal = alvo.veiculo_id ? grupo(original, alvo.veiculo_id) : null;
    var usados = {}, linhas = [], checagem = false, produto = 1, grupos = 0, oficiais = 0, conferem = false, divergem = false;
    var meusDados = dados(alvo);
    parecidas.slice(0, 14).forEach(function (x) {
      var v = veiculos[x.n.veiculo_id] || {};
      var linha = { titulo: x.n.titulo, veiculo: v.nome || x.n.veiculo || x.n.veiculo_id, s: x.s, cortou: x.cortou, p: null, nota: '', tipo: v.tipo };
      var g = grupo(v, x.n.veiculo_id);
      if (x.n.uso === 'oficial' || v.tipo === 'oficial') {
        var cruz = cruzarDados(meusDados, dados(x.n));
        linha.s = x.bruta; linha.cortou = false;
        if (g === gOriginal) linha.nota = 'nota do próprio órgão: não confirma a si mesma';
        else if (cruz.divergem && x.bruta >= LIMIAR_OFICIAL_ASSUNTO) { divergem = true; linha.nota = 'fonte oficial com números diferentes: impede Confirmada'; }
        else if (x.bruta >= LIMIAR_OFICIAL && !usados[g]) {
          usados[g] = true;
          var f = Math.min(1, (x.bruta - LIMIAR_OFICIAL) / (SIMILARIDADE_FORTE - LIMIAR_OFICIAL));
          linha.p = PESO_TIPO.oficial * (0.6 + 0.4 * f);
          produto *= 1 - linha.p;
          oficiais++;
          if (cruz.conferem) conferem = true;
          linha.nota = 'fonte oficial sobre o mesmo fato' + (cruz.conferem ? ', os números conferem' : '');
        } else linha.nota = 'fonte oficial sobre outro assunto';
        linha.tipo = null;
        linhas.push(linha);
        return;
      }
      if (x.s < LIMIAR_FATO) {
        linha.nota = 'abaixo do limiar: outro fato';
      } else if (x.n.uso === 'checagens' || v.tipo === 'checador') {
        if (x.s >= LIMIAR_CHECAGEM && CHECAGEM_FALSO.test(x.n.titulo)) { checagem = true; linha.nota = 'checagem parecida: impede Confirmada'; }
        else linha.nota = 'checador: não conta como confirmação';
      } else if (g === gOriginal) {
        linha.nota = 'mesmo grupo de mídia do original: não conta';
      } else if (usados[g]) {
        linha.nota = 'grupo já contado';
      } else {
        usados[g] = true;
        var forca = Math.min(1, (x.s - LIMIAR_FATO) / (SIMILARIDADE_FORTE - LIMIAR_FATO));
        linha.p = (PESO_TIPO[v.tipo] != null ? PESO_TIPO[v.tipo] : PESO_PADRAO) * (0.6 + 0.4 * forca);
        linha.nota = 'confirmação independente';
        if (x.s >= REPRODUCAO) { linha.p *= FATOR_REPRODUCAO; linha.nota = 'confirmação, mas texto quase idêntico: vale 60%'; }
        produto *= 1 - linha.p;
        grupos++;
      }
      linhas.push(linha);
    });
    var base = 1 - produto;
    var tipos = new Set(linhas.filter(function (l) { return l.p != null && l.tipo; }).map(function (l) { return l.tipo; }));
    var sinais = sinaisDaNoticia(alvo, tipos.size >= 2);
    if (conferem) sinais.push(['os números conferem com a fonte oficial', FATOR_DADOS_CONFEREM]);
    if (divergem) sinais.push(['números diferentes dos da fonte oficial', FATOR_DADOS_DIVERGEM]);
    var c = ajustar(base, sinais);
    var pode = (grupos >= 2 || oficiais > 0) && !checagem && !divergem;
    var rotulo = pode && c >= CONFIANCA_CONFIRMADA ? 'confirmada' : 'em-apuracao';
    return { rotulo: rotulo, base: base, confianca: c, sinais: sinais, grupos: grupos, oficiais: oficiais, linhas: linhas,
      checagem: checagem, divergem: divergem };
  }

  // Interface
  var seletor = document.getElementById('calc-noticia');
  var campo = document.getElementById('calc-titulo');
  var saida = document.getElementById('calc-resultado');
  var estado = document.getElementById('calc-estado');
  if (!seletor || !saida) return;
  var noticias = [], veiculos = {}, corpus = null;

  function el(tag, classe, texto) { var n = document.createElement(tag); if (classe) n.className = classe; if (texto != null) n.textContent = texto; return n; }
  function pct(x) { return Math.round(x * 100) + '%'; }

  function mostrar(alvo) {
    var r = classificar(alvo, corpus, veiculos);
    saida.replaceChildren();
    var topo = el('p', 'calc__rotulo');
    topo.appendChild(el('span', 'rotulo rotulo--' + r.rotulo, NOMES[r.rotulo]));
    if (r.confianca != null) topo.appendChild(document.createTextNode(' Confiança calculada: ' + pct(r.confianca)));
    saida.appendChild(topo);
    if (r.motivo) { saida.appendChild(el('p', null, r.motivo)); return; }
    if (!r.linhas.length) { saida.appendChild(el('p', null, 'Nenhuma notícia carregada trata de assunto parecido.')); return; }
    var tabela = el('table', 'tabela');
    var cab = el('tr');
    ['Notícia parecida', 'Veículo', 'Similaridade', 'Peso (p)', 'Conta?'].forEach(function (t) { var th = el('th', null, t); th.scope = 'col'; cab.appendChild(th); });
    var thead = el('thead'); thead.appendChild(cab); tabela.appendChild(thead);
    var corpo = el('tbody');
    r.linhas.forEach(function (l) {
      var tr = el('tr');
      tr.appendChild(el('td', null, l.titulo));
      tr.appendChild(el('td', null, l.veiculo));
      tr.appendChild(el('td', null, pct(l.s) + (l.cortou ? ' (números diferentes: metade)' : '')));
      tr.appendChild(el('td', null, l.p != null ? pct(l.p) : '—'));
      tr.appendChild(el('td', null, l.nota));
      corpo.appendChild(tr);
    });
    tabela.appendChild(corpo);
    var rolagem = el('div', 'tabela-rolagem'); rolagem.appendChild(tabela);
    saida.appendChild(rolagem);
    var conta = r.linhas.filter(function (l) { return l.p != null; }).map(function (l) { return '(1 − ' + l.p.toFixed(2).replace('.', ',') + ')'; });
    if (r.sinais.length) {
      var lista = el('ul', 'lista-marcada');
      r.sinais.forEach(function (s) { lista.appendChild(el('li', null, s[0] + ': chances × ' + String(s[1]).replace('.', ','))); });
      saida.appendChild(el('p', null, 'Sinais da própria notícia:'));
      saida.appendChild(lista);
    }
    saida.appendChild(el('p', 'calc__conta', conta.length
      ? 'Confirmações: 1 − ' + conta.join(' × ') + ' = ' + pct(r.base) +
        (r.sinais.length ? '. Com os sinais, as chances ' + pct(r.base) + ' ÷ ' + pct(1 - r.base) + ' são multiplicadas e a confiança final fica em ' + pct(r.confianca) : '') +
        ', com ' + r.grupos + ' grupo(s) de imprensa e ' + r.oficiais + ' fonte(s) oficial(is). ' +
        (r.rotulo === 'confirmada' ? 'Passa dos 70% com dois grupos ou uma fonte oficial: Confirmada.'
          : r.divergem ? 'Os números diferem dos da fonte oficial: não pode ser Confirmada.'
          : r.checagem ? 'Há uma checagem parecida: não pode ser Confirmada.'
          : 'Precisa de dois grupos ou uma fonte oficial, e 70%: Em apuração.')
      : 'Nenhuma notícia passou do limiar de similaridade (48%): Em apuração.'));
  }

  function carregar(uf) {
    return Promise.all([
      fetch('dados/noticias.json').then(function (r) { return r.json(); }),
      fetch('dados/estados/' + uf + '.json').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
    ]).then(function (res) {
      var geral = res[0], est = res[1];
      (geral.veiculos || []).forEach(function (v) { veiculos[v.id] = v; });
      var vistos = {};
      function juntar(lista, uso) {
        (lista || []).forEach(function (n) { if (!vistos[n.link]) { vistos[n.link] = 1; noticias.push(Object.assign({ uso: uso }, n)); } });
      }
      Object.keys(geral.escalas || {}).forEach(function (e) { juntar(geral.escalas[e], 'noticias'); });
      if (est) Object.keys(est.escalas || {}).forEach(function (e) { juntar(est.escalas[e], 'noticias'); });
      juntar(geral.checagens, 'checagens');
      juntar(geral.oficiais, 'oficial');
      corpus = new Corpus(noticias);
      var opcoes = noticias.filter(function (n) { return n.uso === 'noticias'; }).slice(0, 80).map(function (n, i) {
        var o = el('option', null, n.titulo.slice(0, 90) + ' — ' + n.veiculo);
        o.value = String(noticias.indexOf(n));
        return o;
      });
      seletor.replaceChildren.apply(seletor, [el('option', null, 'Escolha uma notícia')].concat(opcoes));
      seletor.disabled = false;
      if (estado) estado.textContent = noticias.length + ' notícias carregadas para comparar.';
    });
  }

  seletor.addEventListener('change', function () {
    var n = noticias[parseInt(seletor.value, 10)];
    if (n) mostrar(n);
  });
  document.getElementById('calc-form').addEventListener('submit', function (e) {
    e.preventDefault();
    if (!corpus || !campo.value.trim()) return;
    mostrar({ titulo: campo.value.trim(), resumo: '', link: '', veiculo_id: null, publicado_em: null, digitado: true });
  });

  var uf = (window.Farol && Farol.local && Farol.local.lerOuPadrao && Farol.local.lerOuPadrao().uf) || 'SE';
  carregar(uf).catch(function () {
    if (estado) estado.textContent = 'Não foi possível carregar as notícias agora. Tente recarregar a página.';
  });
})();
