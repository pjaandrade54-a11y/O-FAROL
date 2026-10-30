// O Farol: comportamentos só da página inicial.
// 1. Entradas: título, texto e imagem de cada seção sobem um pouco quando a seção aparece, uma vez.
// 2. Os rótulos: escolher um nome troca o exemplo por uma notícia real com aquele rótulo, tirada das
//    notícias carregadas (sem notícias carregadas, ficam os exemplos escritos na página).
// 3. Anuncie: o cupom monta o e-mail da proposta com o que a pessoa preencheu.

(function () {
  document.documentElement.classList.add('js');

  // 1. Entradas, em cascata dentro de cada seção
  var calmo = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var secoes = document.querySelectorAll('main .secao');
  secoes.forEach(function (secao) {
    var partes = secao.querySelectorAll('h2, h3, .bloco p, .receber__centro p, .receber__acoes, [data-ui], .rotulos__nome, .rotulos__regra, .cupom__campos');
    partes.forEach(function (el, i) {
      el.setAttribute('data-entrada', '');
      el.style.transitionDelay = (Math.min(i, 8) * 75) + 'ms';
    });
  });
  if ('IntersectionObserver' in window && !calmo) {
    var io = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.querySelectorAll('[data-entrada]').forEach(function (el) { el.classList.add('entrou'); });
        io.unobserve(e.target);
      });
    }, { threshold: 0.12 });
    secoes.forEach(function (s) { io.observe(s); });
  } else {
    document.querySelectorAll('[data-entrada]').forEach(function (el) { el.classList.add('entrou'); });
  }

  // 2. Os rótulos
  var REGRAS = {
    'confirmada': 'Dois veículos de grupos diferentes do original publicaram o mesmo fato.',
    'em-apuracao': 'Só um veículo publicou, ou ainda falta a confirmação de um segundo grupo de mídia.',
    'opiniao': 'Coluna, artigo ou editorial: não recebe rótulo de verdadeiro ou falso.',
    'desmentida': 'Só o conselho humano marca uma notícia como Desmentida, depois de conferir a checagem.',
    'aguardando': 'A notícia acabou de chegar e entra na próxima rodada de análise.'
  };
  var NOMES = { 'confirmada': 'Confirmada', 'em-apuracao': 'Em apuração', 'opiniao': 'Opinião ou análise',
    'desmentida': 'Desmentida', 'aguardando': 'Aguardando análise' };
  var ESCALAS = { cidade: 'Cidade', estado: 'Estado', pais: 'País', mundo: 'Mundo' };
  var exemplos = {};
  var palco = document.querySelector('.rotulos__palco');
  var botoes = document.querySelectorAll('.rotulos__nome');
  var cartao = document.querySelector('.exemplo');

  function mostrar(rotulo) {
    botoes.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-rotulo') === rotulo)); });
    palco.setAttribute('data-rotulo', rotulo);
    document.getElementById('rotulos-regra').textContent = REGRAS[rotulo];
    var ex = exemplos[rotulo];
    if (!ex) return;
    cartao.classList.add('trocando');
    setTimeout(function () {
      document.getElementById('exemplo-escala').textContent = ex.escala;
      document.getElementById('exemplo-titulo').textContent = ex.titulo;
      var chip = document.getElementById('exemplo-rotulo');
      chip.textContent = ex.chip;
      chip.className = 'rotulo rotulo--' + ex.classe;
      document.getElementById('exemplo-veiculo').textContent = ex.veiculo;
      document.getElementById('exemplo-porque').textContent = ex.porque;
      cartao.classList.remove('trocando');
    }, calmo ? 0 : 240);
  }

  botoes.forEach(function (b) {
    var rotulo = b.getAttribute('data-rotulo');
    b.addEventListener('click', function () { mostrar(rotulo); });
    // Com mouse, apontar já mostra; no toque, vale o toque
    b.addEventListener('mouseenter', function () { if (matchMedia('(hover: hover)').matches) mostrar(rotulo); });
    b.addEventListener('focus', function () { mostrar(rotulo); });
  });

  // Exemplos reais, a partir das notícias que o painel acabou de carregar
  document.addEventListener('farol:noticias', function (e) {
    var dados = e.detail;
    Object.keys(ESCALAS).forEach(function (escala) {
      (dados.escalas[escala] || []).forEach(function (n) {
        var r = n.analise ? n.analise.rotulo : 'aguardando';
        if (exemplos[r] || !NOMES[r]) return;
        var motivo = n.analise && n.analise.pareceres && n.analise.pareceres[0] && n.analise.pareceres[0].motivos[0];
        exemplos[r] = {
          escala: ESCALAS[escala] + (n.cidade && escala === 'cidade' ? ' · ' + n.cidade : ''),
          titulo: n.titulo, chip: NOMES[r] + (n.analise && n.analise.destino === 'conselho' ? ' · provisório' : ''),
          classe: r, veiculo: n.veiculo, porque: motivo || REGRAS[r]
        };
      });
    });
    var checagem = (dados.checagens || [])[0];
    if (checagem && !exemplos.desmentida) {
      exemplos.desmentida = {
        escala: 'Checagem', titulo: checagem.titulo, chip: 'Checagem', classe: 'desmentida', veiculo: checagem.veiculo,
        porque: 'Uma notícia sobre o mesmo assunto só vira Desmentida depois que o conselho humano confere a checagem.'
      };
    }
    var atual = document.querySelector('.rotulos__nome[aria-pressed="true"]');
    if (atual) mostrar(atual.getAttribute('data-rotulo'));
  });

  // 3. Anuncie: monta o e-mail com os campos preenchidos (o site não tem servidor de formulário)
  var cupom = document.getElementById('form-anuncie');
  if (cupom) {
    cupom.addEventListener('submit', function (e) {
      e.preventDefault();
      var f = cupom.elements;
      var corpo = 'Nome: ' + f.nome.value + '\nEmpresa: ' + f.empresa.value + '\nE-mail: ' + f.email.value +
        '\nCidade onde quer anunciar: ' + f.cidade.value + '\n\nQuero saber como anunciar no Farol.';
      var email = (window.Farol && Farol.site && Farol.site.email) || 'ofarolnws@gmail.com';
      location.href = 'mailto:' + email + '?subject=' + encodeURIComponent('Anuncie: ' + f.empresa.value) +
        '&body=' + encodeURIComponent(corpo);
      document.getElementById('anuncio-status').textContent =
        'Abrimos o seu e-mail com a proposta pronta. Se não abriu, escreva para ' + email + '.';
    });
  }
})();
