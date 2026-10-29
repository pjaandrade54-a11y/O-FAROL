// O Farol — comportamento comum a todas as páginas (e os extras da página inicial)

window.Farol = window.Farol || {};

// Copia um texto. Se o navegador recusar, seleciona o campo para a pessoa copiar à mão.
Farol.copiar = function (texto, campo, status) {
  function manual() {
    if (campo) { campo.focus(); campo.select(); }
    if (status) status.textContent = 'Não foi possível copiar sozinho. O texto está selecionado: use Ctrl+C (ou Copiar, no celular).';
  }
  try {
    navigator.clipboard.writeText(texto).then(function () {
      if (status) status.textContent = 'Mensagem copiada. Cole no seu e-mail e envie para ofarolnws@gmail.com.';
    }, manual);
  } catch (e) { manual(); }
};

(function () {
  // Data da edição e ano do rodapé
  var hoje = new Date();
  var data = hoje.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  var campoData = document.getElementById('data-hoje');
  var campoAno = document.getElementById('ano');
  if (campoData) campoData.textContent = data + ' · edição digital';
  if (campoAno) campoAno.textContent = hoje.getFullYear();

  // Localização lembrada entre as páginas (só neste navegador): {nome, uf}; sem cidade, só o estado
  var PADRAO = { nome: 'Aracaju', uf: 'SE' };
  Farol.local = {
    ler: function () {
      var guardado = null;
      try { guardado = localStorage.getItem('farol-local'); } catch (e) { /* sem armazenamento */ }
      if (!guardado) return null;
      try {
        var local = JSON.parse(guardado);
        if (local && (local.nome || local.uf)) return local;
      } catch (e) { /* versão antiga guardava só o nome */ }
      return { nome: guardado, uf: null };
    },
    lerOuPadrao: function () { return Farol.local.ler() || PADRAO; },
    guardar: function (local) {
      try { localStorage.setItem('farol-local', JSON.stringify(local)); } catch (e) { /* segue sem lembrar */ }
      Farol.local.aplicar(local);
    },
    texto: function (local) {
      if (!local) return 'Sua cidade';
      return local.nome ? local.nome + (local.uf ? ' (' + local.uf + ')' : '') : 'Estado: ' + local.uf;
    },
    aplicar: function (local) {
      document.querySelectorAll('[data-local]').forEach(function (el) { el.textContent = Farol.local.texto(local); });
    }
  };
  Farol.local.aplicar(Farol.local.lerOuPadrao());

  // Canais (WhatsApp, Instagram, TikTok, resumo por e-mail): link quando existir, "em breve" enquanto não
  var site = Farol.site || {};
  document.querySelectorAll('[data-canal]').forEach(function (link) {
    var endereco = site[link.getAttribute('data-canal')];
    if (endereco) {
      link.href = endereco;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
    } else {
      link.classList.add('em-breve');
      link.setAttribute('aria-disabled', 'true');
      link.removeAttribute('href');
      link.appendChild(document.createTextNode(' · em breve'));
    }
  });

  // Apoie: mostra a chave Pix configurada em js/site.js, com botão de copiar
  var chave = document.getElementById('pix-chave');
  var copiarPix = document.getElementById('copiar-pix');
  if (chave && copiarPix && site.pix) {
    chave.textContent = site.pix;
    copiarPix.hidden = false;
    copiarPix.addEventListener('click', function () {
      var status = document.getElementById('pix-status');
      function manual() {
        var faixa = document.createRange();
        faixa.selectNodeContents(chave);
        var selecao = window.getSelection();
        selecao.removeAllRanges();
        selecao.addRange(faixa);
        status.textContent = 'Chave selecionada: copie e cole no app do seu banco.';
      }
      try {
        navigator.clipboard.writeText(site.pix).then(function () {
          status.textContent = 'Chave copiada. Cole no app do seu banco, na opção Pix.';
        }, manual);
      } catch (e) { manual(); }
    });
  }

  // Menu no celular
  var alternar = document.querySelector('.nav__alternar');
  var lista = document.getElementById('nav-lista');
  if (alternar && lista) {
    alternar.addEventListener('click', function () {
      var aberto = lista.classList.toggle('aberta');
      alternar.setAttribute('aria-expanded', String(aberto));
    });
    lista.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        lista.classList.remove('aberta');
        alternar.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Abas do painel de notícias (setas do teclado navegam entre elas)
  var abas = Array.prototype.slice.call(document.querySelectorAll('.abas [role="tab"]'));
  function selecionar(aba) {
    abas.forEach(function (a) {
      var ativa = a === aba;
      a.setAttribute('aria-selected', String(ativa));
      a.tabIndex = ativa ? 0 : -1;
      document.getElementById(a.getAttribute('aria-controls')).hidden = !ativa;
    });
  }
  Farol.selecionarAba = function (indice) { if (abas[indice]) selecionar(abas[indice]); };
  abas.forEach(function (aba, i) {
    aba.addEventListener('click', function () { selecionar(aba); });
    aba.addEventListener('keydown', function (e) {
      var passo = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!passo) return;
      var proxima = abas[(i + passo + abas.length) % abas.length];
      selecionar(proxima);
      proxima.focus();
    });
  });

})();
