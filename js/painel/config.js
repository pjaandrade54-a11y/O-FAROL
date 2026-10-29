// O Farol — configuração do painel de verificação
window.Farol = window.Farol || {};

Farol.config = {
  emailConselho: 'ofarolnws@gmail.com',
  prazoConselho: '3 dias úteis',

  // Quem executa cada agente. Modelos de empresas diferentes para não errarem do mesmo jeito.
  // O Auditor de regras é o próprio código da metodologia: regras exatas, sem IA.
  modelos: {
    'acusacao': { empresa: 'Anthropic', modelo: 'Claude Opus 5.5', id: 'claude-opus-5-5' },
    'defesa': { empresa: 'OpenAI', modelo: 'GPT-6.1 Terra', id: 'gpt-6.1-terra' },
    'auditor-fontes': { empresa: 'Anthropic', modelo: 'Claude Opus 5.5', id: 'claude-opus-5-5' },
    'auditor-regras': { empresa: 'O Farol', modelo: 'Código da metodologia, sem IA', id: null }
  }
};
