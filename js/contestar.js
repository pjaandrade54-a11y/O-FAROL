// O Farol — formulário de contestação (contestar.html)
// Monta o e-mail da contestação com os dados dela e a avaliação atual do painel.

(function (m, agentes, casos, config) {
  var form = document.getElementById('form-contestacao');
  var noticia = document.getElementById('c-noticia');
  var campoOutra = document.getElementById('campo-outra');
  var outra = document.getElementById('c-outra');
  var atual = document.getElementById('rotulo-atual');
  var erro = document.getElementById('erro-contestacao');
  var confirmacao = document.getElementById('confirmacao');

  casos.forEach(function (c) {
    var op = document.createElement('option');
    op.value = c.id;
    op.textContent = c.titulo;
    noticia.appendChild(op);
  });
  var opOutra = document.createElement('option');
  opOutra.value = 'outra';
  opOutra.textContent = 'Outra notícia';
  noticia.appendChild(opOutra);

  function casoEscolhido() {
    return casos.filter(function (c) { return c.id === noticia.value; })[0];
  }

  function avaliar(caso) {
    var pareceres = agentes.LISTA.map(function (a) { return a.analisar(caso); });
    return { pareceres: pareceres, decisao: agentes.decidir(caso, pareceres) };
  }

  function mostrarAtual() {
    campoOutra.hidden = noticia.value !== 'outra';
    var caso = casoEscolhido();
    if (!caso) { atual.textContent = ''; return; }
    var d = avaliar(caso).decisao;
    atual.textContent = 'Avaliação atual: ' + m.ROTULOS[d.rotulo] + ' (pontuação ' + d.pontuacao.total + ' de 100' +
      (d.destino === 'relator' ? ', decidida pelo Relator de IA' : '') + ').';
  }
  noticia.addEventListener('change', mostrarAtual);

  // Permite chegar já com a notícia escolhida: contestar.html#caso-escolas
  var pedido = casos.filter(function (c) { return location.hash === '#caso-' + c.id; })[0];
  if (pedido) { noticia.value = pedido.id; mostrarAtual(); }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var email = document.getElementById('c-email');
    var explicacao = document.getElementById('c-explicacao');
    var faltando = [];
    if (!noticia.value) faltando.push('a notícia');
    if (noticia.value === 'outra' && !outra.value.trim()) faltando.push('o título ou link da notícia');
    if (!explicacao.value.trim()) faltando.push('a explicação');
    if (!email.value.trim() || !email.checkValidity()) faltando.push('um e-mail válido');
    if (faltando.length) {
      erro.textContent = 'Falta preencher: ' + faltando.join(', ') + '.';
      return;
    }
    erro.textContent = '';

    var caso = casoEscolhido();
    var tituloNoticia = caso ? caso.titulo : outra.value.trim();
    var linhas = [
      'Contestação recebida pelo site do Farol.',
      '',
      'Notícia: ' + tituloNoticia,
      'O que é contestado: ' + document.getElementById('c-alvo').value,
      'Quem contesta: ' + document.getElementById('c-quem').value,
      'E-mail para resposta: ' + email.value.trim(),
      '',
      'Por que a avaliação está errada:',
      explicacao.value.trim(),
      '',
      'Provas:',
      document.getElementById('c-provas').value.trim() || '(nenhuma informada)'
    ];
    if (caso) {
      var av = avaliar(caso);
      linhas.push('', 'Avaliação atual do painel: ' + m.ROTULOS[av.decisao.rotulo] + ' (pontuação ' + av.decisao.pontuacao.total + ' de 100)');
      av.pareceres.forEach(function (p) {
        var nome = agentes.LISTA.filter(function (a) { return a.id === p.agente; })[0].nome;
        linhas.push('- ' + nome + ': ' + m.ROTULOS[p.rotuloSugerido] + '. ' + p.motivos.join(' '));
      });
    }
    linhas.push('', 'Prazo: nova análise por e-mail em até ' + config.prazoConselho + '.');

    var assunto = '[Conselho] Contestação: ' + tituloNoticia;
    var corpo = linhas.join('\r\n');
    document.getElementById('link-email').href = 'mailto:' + config.emailConselho +
      '?subject=' + encodeURIComponent(assunto) + '&body=' + encodeURIComponent(corpo);
    mensagem.value = 'Para: ' + config.emailConselho + '\r\nAssunto: ' + assunto + '\r\n\r\n' + corpo;
    copiaStatus.textContent = '';

    form.hidden = true;
    confirmacao.hidden = false;
    confirmacao.focus();
  });

  var mensagem = document.getElementById('mensagem-pronta');
  var copiaStatus = document.getElementById('copia-status');
  document.getElementById('copiar-mensagem').addEventListener('click', function () {
    Farol.copiar(mensagem.value, mensagem, copiaStatus);
  });
  document.getElementById('nova-contestacao').addEventListener('click', function () {
    confirmacao.hidden = true;
    form.hidden = false;
    form.reset();
    mostrarAtual();
  });
})(Farol.metodologia, Farol.agentes, Farol.casos, Farol.config);
