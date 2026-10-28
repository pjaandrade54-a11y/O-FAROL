// O Farol — motor da metodologia de confiabilidade (versão 0.1)
// Implementa a pontuação de uma notícia e as regras de rótulo descritas em metodologia.html.

window.Farol = window.Farol || {};

Farol.metodologia = (function () {
  var VERSAO = '0.1';

  var ROTULOS = {
    'opiniao': 'Opinião ou análise',
    'desmentida': 'Desmentida',
    'contestada': 'Contestada',
    'confirmada': 'Confirmada',
    'em-apuracao': 'Em apuração',
    'dados-insuficientes': 'Dados insuficientes'
  };

  var PONTOS_PRIMARIA = {
    'documento': 20,
    'dado-oficial': 20,
    'decisao-judicial': 20,
    'entrevistado-identificado': 12,
    'link-verificavel': 8
  };

  var ALERTAS = {
    'titulo-contradiz': 'Título contradiz o texto',
    'noticia-antiga': 'Notícia antiga apresentada como nova',
    'imagem-fora-contexto': 'Imagem fora de contexto'
  };

  // Temas em que um rótulo Contestada exige revisão humana antes de publicar
  var TEMAS_ALTO_IMPACTO = ['eleicoes', 'saude', 'seguranca'];

  // Nota neutra usada quando o veículo ainda está "Em avaliação" (ausência de dados não é penalidade)
  var NOTA_NEUTRA = 50;

  // Coberturas de grupos diferentes do original, com apuração própria, contadas uma vez por grupo
  function independentes(caso, confirma) {
    var vistos = {};
    vistos[caso.original.grupo] = true;
    return caso.coberturas.filter(function (c) {
      if (c.confirma !== confirma || !c.apuracaoPropria || vistos[c.grupo]) return false;
      vistos[c.grupo] = true;
      return true;
    });
  }

  // Coberturas que não contam como fonte independente, com o motivo
  function descartadas(caso) {
    var contados = {};
    contados[caso.original.grupo] = caso.original.nome;
    independentes(caso, true).concat(independentes(caso, false)).forEach(function (c) { contados[c.grupo] = c.veiculo; });
    return caso.coberturas.filter(function (c) {
      return !c.apuracaoPropria || contados[c.grupo] !== c.veiculo;
    }).map(function (c) {
      var motivo = !c.apuracaoPropria
        ? 'reproduz texto de outro veículo, sem apuração própria'
        : 'pertence ao mesmo grupo de ' + contados[c.grupo];
      return { veiculo: c.veiculo, motivo: motivo };
    });
  }

  function checagens(caso, veredito) {
    return (caso.checagens || []).filter(function (c) { return c.signatariaIFCN && c.veredito === veredito; });
  }

  // Em temas políticos, ao menos uma confirmação de linha editorial declarada diferente da do original
  function temPluralidade(caso) {
    return independentes(caso, true).some(function (c) {
      return c.linha !== caso.original.linha && c.linha !== 'não declarada';
    });
  }

  function notaVeiculo(caso) {
    return caso.original.notaVeiculo == null ? NOTA_NEUTRA : caso.original.notaVeiculo;
  }

  function pontuar(caso) {
    var itens = [];
    var grupos = independentes(caso, true).length;
    itens.push({
      sinal: 'Corroboração independente',
      pontos: grupos >= 3 ? 35 : grupos === 2 ? 25 : grupos === 1 ? 15 : 0,
      max: 35,
      detalhe: grupos === 0 ? 'Nenhum grupo independente confirma' : grupos + (grupos === 1 ? ' grupo independente confirma' : ' grupos independentes confirmam')
    });

    var primaria = caso.fontePrimaria;
    itens.push({
      sinal: 'Fonte primária',
      pontos: primaria ? PONTOS_PRIMARIA[primaria.tipo] || 0 : 0,
      max: 20,
      detalhe: primaria ? primaria.descricao : 'Nenhuma fonte primária citada'
    });

    var nota = notaVeiculo(caso);
    itens.push({
      sinal: 'Confiabilidade do veículo',
      pontos: Math.round(nota / 100 * 20),
      max: 20,
      detalhe: caso.original.notaVeiculo == null
        ? caso.original.nome + ' está em avaliação (valor neutro)'
        : caso.original.nome + ': nota ' + nota + ' de 100'
    });

    var confirmadaPorChecagem = checagens(caso, 'verdadeiro').length > 0;
    itens.push({
      sinal: 'Checagem independente',
      pontos: confirmadaPorChecagem ? 15 : 0,
      max: 15,
      detalhe: confirmadaPorChecagem ? 'Checagem de signatário da IFCN confirma' : 'Nenhuma checagem confirma'
    });

    var a = caso.atribuicao;
    var faltando = [];
    if (!a.autor) faltando.push('autor');
    if (!a.dataPublicacao) faltando.push('data de publicação');
    if (!a.dataAtualizacao) faltando.push('data de atualização');
    itens.push({
      sinal: 'Atribuição',
      pontos: (a.autor ? 5 : 0) + (a.dataPublicacao ? 3 : 0) + (a.dataAtualizacao ? 2 : 0),
      max: 10,
      detalhe: faltando.length ? 'Falta: ' + faltando.join(', ') : 'Autor e datas identificados'
    });

    (caso.alertas || []).forEach(function (alerta) {
      itens.push({ sinal: 'Sinal de alerta', pontos: -10, max: 0, detalhe: ALERTAS[alerta] });
    });

    var soma = itens.reduce(function (t, i) { return t + i.pontos; }, 0);
    return { total: Math.max(0, Math.min(100, soma)), itens: itens, gruposConfirmam: grupos };
  }

  function resultado(rotulo, motivos) {
    return { rotulo: rotulo, motivos: motivos };
  }

  // Regras de prioridade: a ordem importa (metodologia.html#rotulos)
  function rotular(caso, pontuacao) {
    if (caso.tipo === 'opiniao') {
      return resultado('opiniao', ['O veículo marcou o texto como opinião; não recebe rótulo de veracidade.']);
    }
    var falsas = checagens(caso, 'falso');
    if (falsas.length) {
      return resultado('desmentida', falsas.map(function (c) {
        return c.organizacao + ' (signatária da IFCN) classificou a afirmação como falsa em ' + c.data + '.';
      }));
    }
    var contrarias = independentes(caso, false);
    if (contrarias.length) {
      return resultado('contestada', contrarias.map(function (c) {
        return c.veiculo + ' publicou outra versão: ' + c.versao + '.';
      }));
    }
    if (!caso.textoAcessivel) {
      return resultado('dados-insuficientes', ['O texto original não pôde ser lido (acesso fechado).']);
    }
    if (pontuacao.total >= 70 && pontuacao.gruposConfirmam >= 2) {
      if (caso.tema === 'politica' && !temPluralidade(caso)) {
        return resultado('em-apuracao', [
          'Pontuação ' + pontuacao.total + ', mas todas as confirmações vêm de veículos com a mesma linha editorial declarada (' + caso.original.linha + ').',
          'Em temas políticos, exigimos ao menos uma confirmação de linha diferente.'
        ]);
      }
      return resultado('confirmada', [
        pontuacao.gruposConfirmam + ' grupos independentes confirmam, com pontuação ' + pontuacao.total + '.'
      ]);
    }
    if (pontuacao.total >= 40) {
      var motivos = [];
      if (pontuacao.total < 70) motivos.push('Pontuação ' + pontuacao.total + ', abaixo dos 70 necessários para confirmar.');
      if (pontuacao.gruposConfirmam < 2) motivos.push('Faltam confirmações de outros grupos de mídia (' + pontuacao.gruposConfirmam + ' de 2).');
      return resultado('em-apuracao', motivos);
    }
    return resultado('dados-insuficientes', ['Pontuação ' + pontuacao.total + ', abaixo de 40, sem checagem contrária.']);
  }

  // Texto que tenta dar ordens ao sistema é tratado como dado e sinalizado
  var PADROES_MANIPULACAO = [
    /ignor[ea]\s+(as\s+|todas\s+as\s+)?(instru[cç][oõ]es|regras)/i,
    /classifi(que|car)\s+(esta|essa|como)/i,
    /(prompt|instru[cç][aã]o)\s+do\s+sistema/i,
    /voc[eê]\s+[eé]\s+(um|uma)\s+(modelo|assistente|ia)/i
  ];

  function suspeitaManipulacao(texto) {
    return PADROES_MANIPULACAO.some(function (p) { return p.test(texto || ''); });
  }

  return {
    VERSAO: VERSAO,
    ROTULOS: ROTULOS,
    ALERTAS: ALERTAS,
    TEMAS_ALTO_IMPACTO: TEMAS_ALTO_IMPACTO,
    independentes: independentes,
    descartadas: descartadas,
    checagens: checagens,
    temPluralidade: temPluralidade,
    pontuar: pontuar,
    rotular: rotular,
    suspeitaManipulacao: suspeitaManipulacao
  };
})();
