// O Farol: comportamentos só da página inicial.
// 1. Entradas: título, texto e imagem de cada seção sobem um pouco quando a seção aparece, uma vez.
// 2. Os rótulos: escolher um nome troca o exemplo por uma notícia real com aquele rótulo, tirada das
//    notícias carregadas (sem notícias carregadas, ficam os exemplos escritos na página).
// 3. Anuncie: o cupom monta o e-mail da proposta com o que a pessoa preencheu.
// 4. Fluidez: barra de leitura, cabeçalho que some ao descer e volta ao subir, o feixe que segue o
//    ponteiro, o número de veículos contando, as etapas que crescem e o arrastar entre as abas no celular.

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
      var foto = document.getElementById('exemplo-foto');
      if (ex.imagem) foto.src = ex.imagem; else foto.removeAttribute('src');
      foto.hidden = !ex.imagem;
      cartao.classList.remove('trocando');
    }, calmo ? 0 : 240);
  }

  botoes.forEach(function (b) {
    var rotulo = b.getAttribute('data-rotulo');
    b.addEventListener('click', function () { parar(); mostrar(rotulo); });
    // Com mouse, apontar já mostra; no toque, vale o toque
    b.addEventListener('mouseenter', function () { if (matchMedia('(hover: hover)').matches) { parar(); mostrar(rotulo); } });
    b.addEventListener('focus', function () { parar(); mostrar(rotulo); });
  });

  // Enquanto ninguém mexe, os rótulos passam sozinhos, um a cada 4,5 s, só com a seção na tela
  var giro = null;
  function parar() { clearInterval(giro); giro = null; autoplay = false; }
  var autoplay = !calmo;
  if ('IntersectionObserver' in window && palco) {
    new IntersectionObserver(function (entradas) {
      if (!autoplay) return;
      if (entradas[0].isIntersecting && !giro) {
        giro = setInterval(function () {
          var lista = Array.prototype.slice.call(botoes);
          var atual = lista.findIndex(function (b) { return b.getAttribute('aria-pressed') === 'true'; });
          mostrar(lista[(atual + 1) % lista.length].getAttribute('data-rotulo'));
        }, 4500);
      } else if (!entradas[0].isIntersecting) {
        clearInterval(giro); giro = null;
      }
    }, { threshold: 0.4 }).observe(palco);
  }

  // Exemplos reais, a partir das notícias que o painel acabou de carregar
  document.addEventListener('farol:noticias', function (e) {
    var dados = e.detail;
    Object.keys(ESCALAS).forEach(function (escala) {
      (dados.escalas[escala] || []).forEach(function (n) {
        var r = n.analise ? n.analise.rotulo : 'aguardando';
        if (!NOMES[r] || (exemplos[r] && (exemplos[r].imagem || !n.imagem))) return;
        var motivo = n.analise && n.analise.pareceres && n.analise.pareceres[0] && n.analise.pareceres[0].motivos[0];
        exemplos[r] = {
          escala: ESCALAS[escala] + (n.cidade && escala === 'cidade' ? ' · ' + n.cidade : ''),
          titulo: n.titulo, chip: NOMES[r] + (n.analise && n.analise.destino === 'conselho' ? ' · provisório' : ''),
          classe: r, veiculo: n.veiculo, porque: motivo || REGRAS[r], imagem: n.imagem
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

  // 4. Fluidez
  var raiz = document.documentElement;
  var barra = document.createElement('div');
  barra.className = 'progresso';
  barra.setAttribute('aria-hidden', 'true');
  document.body.appendChild(barra);
  var cabecalho = document.querySelector('.cabecalho');
  var ultimoY = window.scrollY, pedido = null;
  function aoRolar() {
    pedido = null;
    var y = window.scrollY;
    var total = raiz.scrollHeight - innerHeight;
    barra.style.transform = 'scaleX(' + (total > 0 ? Math.min(1, y / total) : 0) + ')';
    // Desce: o cabeçalho sai do caminho; sobe: volta. Perto do topo ou com o menu aberto, fica sempre
    var menuAberto = document.querySelector('.nav__lista.aberta');
    if (cabecalho && !menuAberto) cabecalho.classList.toggle('cabecalho--escondido', y > 320 && y > ultimoY + 4);
    if (cabecalho && (y < ultimoY - 4 || y < 320)) cabecalho.classList.remove('cabecalho--escondido');
    if (Math.abs(y - ultimoY) > 4) ultimoY = y;
  }
  addEventListener('scroll', function () { if (!pedido) pedido = requestAnimationFrame(aoRolar); }, { passive: true });
  aoRolar();

  // O feixe da abertura gira na direção do ponteiro (só com mouse e sem pedido de menos movimento)
  var abertura = document.querySelector('.abertura');
  var feixe = document.querySelector('.abertura__feixe');
  if (abertura && feixe && !calmo && matchMedia('(hover: hover) and (pointer: fine)').matches) {
    abertura.addEventListener('pointermove', function (e) {
      var r = abertura.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      feixe.classList.add('feixe--guiado');
      feixe.style.setProperty('--giro', (y * 10 - x * 4).toFixed(2) + 'deg');
    });
    abertura.addEventListener('pointerleave', function () { feixe.classList.remove('feixe--guiado'); });
  }

  // O número de veículos conta de 0 até o número real quando aparece
  document.querySelectorAll('[data-contar]').forEach(function (n) {
    var alvo = parseInt(n.textContent, 10);
    if (calmo || !alvo) return;
    var inicio = null;
    n.style.fontVariantNumeric = 'tabular-nums';
    function passo(t) {
      if (!inicio) inicio = t;
      var p = Math.min(1, (t - inicio) / 1400);
      n.textContent = Math.round(alvo * (1 - Math.pow(1 - p, 4)));
      if (p < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  });

  // Arrastar o dedo para o lado troca de aba (Cidade, Estado, País, Mundo)
  var listas = document.querySelector('.pasta__listas');
  if (listas && window.Farol && Farol.selecionarAba) {
    var toque = null;
    document.querySelectorAll('.abas [role="tab"]').forEach(function (a) {
      a.addEventListener('click', function () { listas.removeAttribute('data-direcao'); });
    });
    listas.addEventListener('touchstart', function (e) {
      toque = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }, { passive: true });
    listas.addEventListener('touchend', function (e) {
      if (!toque) return;
      var dx = e.changedTouches[0].clientX - toque.x, dy = e.changedTouches[0].clientY - toque.y;
      toque = null;
      if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
      var abas = Array.prototype.slice.call(document.querySelectorAll('.abas [role="tab"]:not([hidden])'));
      var atual = abas.findIndex(function (a) { return a.getAttribute('aria-selected') === 'true'; });
      var proxima = atual + (dx < 0 ? 1 : -1);
      if (proxima >= 0 && proxima < abas.length) {
        listas.setAttribute('data-direcao', dx < 0 ? 'avanca' : 'volta');
        Farol.selecionarAba(proxima);
      }
    }, { passive: true });
  }
})();
