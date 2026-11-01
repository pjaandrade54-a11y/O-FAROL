// O Farol — formulário de contestação (contestar.html)
// Lista as notícias reais do site, mostra o rótulo e a conta atuais e monta o e-mail da contestação.
// contestar.html?n=<link da notícia> já chega com a notícia escolhida.

(function () {
  var EMAIL = (window.Farol && Farol.site && Farol.site.email) || 'ofarolnws@gmail.com';
  var PRAZO = '3 dias úteis';
  var NOMES = { 'confirmada': 'Confirmada', 'em-apuracao': 'Em apuração', 'opiniao': 'Opinião ou análise',
    'dados-insuficientes': 'Dados insuficientes', 'desmentida': 'Desmentida', 'contestada': 'Contestada' };

  var form = document.getElementById('form-contestacao');
  var noticia = document.getElementById('c-noticia');
  var campoOutra = document.getElementById('campo-outra');
  var outra = document.getElementById('c-outra');
  var atual = document.getElementById('rotulo-atual');
  var erro = document.getElementById('erro-contestacao');
  var confirmacao = document.getElementById('confirmacao');
  var mensagem = document.getElementById('mensagem-pronta');
  var copiaStatus = document.getElementById('copia-status');
  var noticias = [];

  function opcao(valor, texto) {
    var op = document.createElement('option');
    op.value = valor;
    op.textContent = texto;
    return op;
  }

  function escolhida() { return noticias[parseInt(noticia.value, 10)]; }

  function descrever(n) {
    var a = n.analise;
    if (!a) return 'Ainda sem rótulo: ele aparece na próxima coleta.';
    var p = (a.pareceres || [])[0] || {};
    var c = typeof p.confianca === 'number' ? ', confiança calculada de ' + Math.round(p.confianca * 100) + '%' : '';
    return 'Rótulo atual: ' + (NOMES[a.rotulo] || a.rotulo) + c + '. ' + (p.motivos || a.motivos || []).join(' ');
  }

  function mostrarAtual() {
    campoOutra.hidden = noticia.value !== 'outra';
    var n = escolhida();
    atual.textContent = n ? descrever(n) : '';
  }
  noticia.addEventListener('change', mostrarAtual);

  // Notícias do site: o arquivo geral e o do estado do leitor
  var uf = (window.Farol && Farol.local && Farol.local.lerOuPadrao && Farol.local.lerOuPadrao().uf) || 'SE';
  Promise.all([
    fetch('dados/noticias.json').then(function (r) { return r.json(); }),
    fetch('dados/estados/' + uf + '.json').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
  ]).then(function (res) {
    var vistos = {};
    [res[0], res[1]].forEach(function (arquivo) {
      if (!arquivo) return;
      Object.keys(arquivo.escalas || {}).forEach(function (e) {
        (arquivo.escalas[e] || []).forEach(function (n) {
          if (!vistos[n.link]) { vistos[n.link] = true; noticias.push(n); }
        });
      });
    });
    noticias.sort(function (a, b) { return (b.publicado_em || '').localeCompare(a.publicado_em || ''); });
    noticias.forEach(function (n, i) { noticia.appendChild(opcao(String(i), n.titulo.slice(0, 100) + ' — ' + n.veiculo)); });
    noticia.appendChild(opcao('outra', 'Outra notícia'));
    var pedido = new URLSearchParams(location.search).get('n');
    var indice = pedido ? noticias.findIndex(function (n) { return n.link === pedido; }) : -1;
    if (indice >= 0) { noticia.value = String(indice); mostrarAtual(); }
  }).catch(function () {
    noticia.appendChild(opcao('outra', 'Outra notícia'));
  });

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

    var n = escolhida();
    var titulo = n ? n.titulo : outra.value.trim();
    var linhas = [
      'Contestação recebida pelo site do Farol.',
      '',
      'Notícia: ' + titulo
    ];
    if (n) linhas.push('Veículo: ' + n.veiculo, 'Link: ' + n.link, descrever(n));
    linhas.push(
      'O que é contestado: ' + document.getElementById('c-alvo').value,
      'Quem contesta: ' + document.getElementById('c-quem').value,
      'E-mail para resposta: ' + email.value.trim(),
      '',
      'Por que a avaliação está errada:',
      explicacao.value.trim(),
      '',
      'Provas:',
      document.getElementById('c-provas').value.trim() || '(nenhuma informada)',
      '',
      'Prazo: resposta, com a conta refeita, em até ' + PRAZO + '.');

    var assunto = 'Contestação: ' + titulo;
    var corpo = linhas.join('\r\n');
    document.getElementById('link-email').href = 'mailto:' + EMAIL +
      '?subject=' + encodeURIComponent(assunto) + '&body=' + encodeURIComponent(corpo);
    mensagem.value = 'Para: ' + EMAIL + '\r\nAssunto: ' + assunto + '\r\n\r\n' + corpo;
    copiaStatus.textContent = '';

    form.hidden = true;
    confirmacao.hidden = false;
    confirmacao.focus();
  });

  document.getElementById('copiar-mensagem').addEventListener('click', function () {
    Farol.copiar(mensagem.value, mensagem, copiaStatus);
  });
  document.getElementById('nova-contestacao').addEventListener('click', function () {
    confirmacao.hidden = true;
    form.hidden = false;
    form.reset();
    mostrarAtual();
  });
})();
