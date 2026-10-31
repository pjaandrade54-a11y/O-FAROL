// O Farol — painel de verificação: os quatro agentes e a decisão do painel
// No modo demonstração, cada agente é simulado por regras locais. No modo remoto, cada parecer
// vem do servidor de modelos (contrato em docs/servidor-modelos.md), validado pelo mesmo formato.

window.Farol = window.Farol || {};

Farol.agentes = (function (m) {
  function parecer(agente, rotulo, confianca, motivos, provas) {
    return { agente: agente, rotuloSugerido: rotulo, confianca: confianca, motivos: motivos, provas: provas || [] };
  }

  function nomes(lista) {
    return lista.map(function (c) { return c.veiculo; }).join(', ');
  }

  // Procura as provas contra a afirmação
  function acusacao(caso) {
    var id = 'acusacao';
    if (caso.tipo === 'opiniao') return parecer(id, 'opiniao', 0.9, ['Texto de opinião: não há afirmação de fato a contestar.']);
    var falsas = m.checagens(caso, 'falso');
    if (falsas.length) {
      return parecer(id, 'desmentida', 0.95, ['Há checagem independente que classifica a afirmação como falsa.'],
        falsas.map(function (c) { return c.organizacao + ', ' + c.data; }));
    }
    var contrarias = m.independentes(caso, false);
    if (contrarias.length) {
      return parecer(id, 'contestada', 0.85, ['Fontes independentes publicaram versões diferentes do fato central.'],
        contrarias.map(function (c) { return c.veiculo + ': ' + c.versao; }));
    }
    var motivos = [];
    (caso.alertas || []).forEach(function (a) { motivos.push('Sinal de alerta: ' + m.ALERTAS[a].toLowerCase() + '.'); });
    if (m.independentes(caso, true).length < 2) motivos.push('Menos de duas confirmações de grupos independentes.');
    if (!caso.fontePrimaria) motivos.push('Nenhuma fonte primária citada.');
    if (!caso.atribuicao.autor) motivos.push('Texto sem autor identificado.');
    if (motivos.length) return parecer(id, 'em-apuracao', 0.7, motivos);
    return parecer(id, 'confirmada', 0.6, ['Não encontrei provas contra a afirmação central.'], [
      'Nenhuma checagem independente contrária',
      'Nenhum grupo independente com versão diferente',
      'Nenhum sinal de alerta no texto'
    ]);
  }

  // Procura as provas a favor
  function defesa(caso) {
    var id = 'defesa';
    if (caso.tipo === 'opiniao') return parecer(id, 'opiniao', 0.9, ['Texto de opinião, identificado pelo próprio veículo.']);
    var falsas = m.checagens(caso, 'falso');
    if (falsas.length) {
      return parecer(id, 'desmentida', 0.9, ['Existe checagem independente contrária; não há como sustentar a afirmação.'],
        falsas.map(function (c) { return c.organizacao + ', ' + c.data; }));
    }
    var contrarias = m.independentes(caso, false);
    if (contrarias.length) {
      return parecer(id, 'contestada', 0.7, ['A versão do original tem apoio, mas há fontes independentes que divergem.'],
        contrarias.map(function (c) { return c.veiculo + ': ' + c.versao; }));
    }
    var confirmam = m.independentes(caso, true);
    var provas = confirmam.map(function (c) { return c.veiculo + ' confirma com apuração própria'; });
    if (caso.fontePrimaria) provas.push('Fonte primária: ' + caso.fontePrimaria.descricao);
    m.checagens(caso, 'verdadeiro').forEach(function (c) { provas.push(c.organizacao + ' confirmou em ' + c.data); });
    if (confirmam.length >= 2 && caso.fontePrimaria) {
      return parecer(id, 'confirmada', 0.85, ['A afirmação tem fonte primária e confirmação de ' + confirmam.length + ' grupos independentes.'], provas);
    }
    if (provas.length) return parecer(id, 'em-apuracao', 0.65, ['Há provas a favor, mas ainda insuficientes para confirmar.'], provas);
    return parecer(id, 'em-apuracao', 0.4, ['Não encontrei provas a favor além do próprio texto.']);
  }

  // Confere a independência das fontes e a existência de fonte primária
  function auditorFontes(caso) {
    var id = 'auditor-fontes';
    if (caso.tipo === 'opiniao') return parecer(id, 'opiniao', 0.9, ['Opinião: a análise de fontes não se aplica.']);
    var confirmam = m.independentes(caso, true);
    var contrarias = m.independentes(caso, false);
    var provas = [];
    if (confirmam.length) provas.push('Confirmam: ' + nomes(confirmam));
    if (contrarias.length) provas.push('Divergem: ' + nomes(contrarias));
    m.descartadas(caso).forEach(function (d) { provas.push('Não conta: ' + d.veiculo + ' (' + d.motivo + ')'); });
    provas.push(caso.fontePrimaria ? 'Fonte primária: ' + caso.fontePrimaria.descricao : 'Sem fonte primária');

    if (m.checagens(caso, 'falso').length) return parecer(id, 'desmentida', 0.9, ['Uma fonte independente de checagem desmente a afirmação.'], provas);
    if (contrarias.length) return parecer(id, 'contestada', 0.85, [contrarias.length + ' grupo(s) independente(s) com versão diferente.'], provas);
    if (confirmam.length >= 2 && caso.tema === 'politica' && !m.temPluralidade(caso)) {
      return parecer(id, 'em-apuracao', 0.75, ['As confirmações vêm só de veículos com a mesma linha editorial declarada do original.'], provas);
    }
    if (confirmam.length >= 2) return parecer(id, 'confirmada', 0.8, [confirmam.length + ' grupos independentes confirmam com apuração própria.'], provas);
    return parecer(id, 'em-apuracao', 0.7, ['Confirmações independentes insuficientes (' + confirmam.length + ').'], provas);
  }

  // Confere se o rótulo segue a metodologia ao pé da letra
  function auditorRegras(caso) {
    var id = 'auditor-regras';
    var pontuacao = m.pontuar(caso);
    var regra = m.rotular(caso, pontuacao);
    var motivos = regra.motivos.slice();
    var provas = ['Metodologia versão ' + m.VERSAO, 'Pontuação calculada: ' + pontuacao.total + ' de 100'];
    var p = parecer(id, regra.rotulo, 0.95, motivos, provas);
    if (m.suspeitaManipulacao(caso.trecho)) {
      p.motivos.push('O texto contém instruções dirigidas ao sistema. Foram tratadas como conteúdo, não como ordem.');
      p.manipulacao = true;
    }
    return p;
  }

  var LISTA = [
    { id: 'acusacao', nome: 'Acusação', papel: 'Procura as provas contra a afirmação', analisar: acusacao },
    { id: 'defesa', nome: 'Defesa', papel: 'Procura as provas a favor', analisar: defesa },
    { id: 'auditor-fontes', nome: 'Auditor de fontes', papel: 'Confere independência e fonte primária', analisar: auditorFontes },
    { id: 'auditor-regras', nome: 'Auditor de regras', papel: 'Aplica a metodologia ao pé da letra', analisar: auditorRegras }
  ];

  // Mesmo formato exigido dos pareceres vindos de modelos reais
  function validarParecer(p, agenteEsperado) {
    var erros = [];
    if (!p || typeof p !== 'object') return ['Parecer vazio ou em formato inválido.'];
    if (p.agente !== agenteEsperado) erros.push('Campo "agente" diferente do esperado.');
    if (!m.ROTULOS[p.rotuloSugerido]) erros.push('Rótulo sugerido desconhecido.');
    if (typeof p.confianca !== 'number' || p.confianca < 0 || p.confianca > 1) erros.push('Confiança fora do intervalo 0 a 1.');
    if (!Array.isArray(p.motivos) || !p.motivos.length || !p.motivos.every(function (x) { return typeof x === 'string'; })) erros.push('Motivos ausentes.');
    if (!Array.isArray(p.provas)) erros.push('Lista de provas ausente.');
    if (p.rotuloSugerido === 'confirmada' && p.agente !== 'auditor-regras' && (!p.provas || !p.provas.length)) erros.push('Conclusão sem prova citada é descartada.');
    return erros;
  }

  var ENDPOINT_REMOTO = '/api/painel/parecer';

  function parecerRemoto(agente, caso) {
    return fetch(ENDPOINT_REMOTO, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agente: agente.id, versaoMetodologia: m.VERSAO, caso: caso })
    }).then(function (r) {
      if (!r.ok) throw new Error('O servidor de modelos respondeu ' + r.status + ' em ' + ENDPOINT_REMOTO + '.');
      return r.json();
    }).then(function (p) {
      var erros = validarParecer(p, agente.id);
      if (erros.length) throw new Error(agente.nome + ': ' + erros.join(' '));
      return p;
    });
  }

  // O Auditor de regras sempre roda aqui: é o código da metodologia, não um modelo
  function obterParecer(agente, caso, modo) {
    if (modo === 'remoto' && agente.id !== 'auditor-regras') return parecerRemoto(agente, caso);
    return Promise.resolve(agente.analisar(caso));
  }

  // Decide o rótulo final, sem revisão humana: se os agentes divergem, o Relator de IA decide pela
  // metodologia; com suspeita de manipulação, a notícia fica Em apuração
  function decidir(caso, pareceres) {
    var pontuacao = m.pontuar(caso);
    var regra = m.rotular(caso, pontuacao);
    var sugeridos = pareceres.map(function (p) { return p.rotuloSugerido; });
    var consenso = sugeridos.every(function (r) { return r === sugeridos[0]; });
    var avisos = [];
    var rotulo = regra.rotulo;

    if (!consenso) avisos.push('Os agentes divergiram sobre o rótulo; o Relator de IA pesou os pareceres e decidiu.');
    if (pareceres.some(function (p) { return p.manipulacao; })) {
      avisos.push('O texto parece tentar dar ordens ao sistema; o rótulo fica Em apuração.');
      rotulo = 'em-apuracao';
    }

    return {
      pontuacao: pontuacao,
      rotulo: rotulo,
      motivos: regra.motivos,
      consenso: consenso,
      destino: consenso ? 'automatico' : 'relator',
      motivosDestino: avisos
    };
  }

  return {
    LISTA: LISTA,
    ENDPOINT_REMOTO: ENDPOINT_REMOTO,
    obterParecer: obterParecer,
    validarParecer: validarParecer,
    decidir: decidir
  };
})(Farol.metodologia);
