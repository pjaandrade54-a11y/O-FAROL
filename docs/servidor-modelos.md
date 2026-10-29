# Servidor de modelos do painel de verificação

> **Notícias reais:** os agentes já rodam de verdade nas notícias coletadas, sem servidor, dentro do GitHub Actions (`python -m coletor analisar`, código em `coletor/conselho.py`). Por padrão, no plano gratuito do Google Gemini; veja [hospedagem.md](hospedagem.md#conselho-de-ia-gratuito). Este documento trata do painel interativo (`painel.html`), que ainda precisa de um servidor para chamar os modelos a partir do navegador.

O painel (`painel.html`) funciona hoje em **modo demonstração**: os quatro agentes são simulados pelas regras de `js/painel/agentes.js`. Para usar modelos de IA de verdade, falta um servidor que receba cada caso e devolva o parecer de cada agente. As chaves de API ficam **só no servidor**, nunca no navegador.

## Quem executa cada agente

Definido em `js/painel/config.js`:

| Agente | Executa | Observação |
| --- | --- | --- |
| Acusação | Claude Opus 5.5 (`claude-opus-5-5`, Anthropic) | |
| Defesa | GPT-6.1 Terra (`gpt-6.1-terra`, OpenAI) | |
| Auditor de fontes | Claude Opus 5.5 (`claude-opus-5-5`, Anthropic) | |
| Auditor de regras | Código da metodologia (`js/painel/metodologia.js`) | Não usa IA e nunca vai ao servidor |

Acusação e Defesa ficam em empresas diferentes para que os dois lados não errem do mesmo jeito. O servidor precisa de duas chaves de API: uma da Anthropic e uma da OpenAI.

## Conselho humano por e-mail

Os casos que o painel não resolve vão para o e-mail do conselho (`emailConselho` em `js/painel/config.js`). Hoje o painel monta a mensagem com o resumo do caso e os pareceres, e quem opera clica para enviar. Quando o servidor existir, ele pode enviar sozinho, por um serviço de e-mail transacional. A decisão final volta a quem contestou, por e-mail, em até 3 dias úteis.

## Contrato

O navegador chama, uma vez por agente (exceto o Auditor de regras):

```
POST /api/painel/parecer
Content-Type: application/json

{
  "agente": "acusacao" | "defesa" | "auditor-fontes",
  "versaoMetodologia": "0.1",
  "caso": { ...mesmo formato dos objetos em js/painel/casos.js... }
}
```

O servidor responde com o parecer:

```json
{
  "agente": "acusacao",
  "rotuloSugerido": "em-apuracao",
  "confianca": 0.7,
  "motivos": ["Menos de duas confirmações de grupos independentes."],
  "provas": ["Portal Bairro Novo reproduz o texto sem apuração própria"]
}
```

`rotuloSugerido` é um destes: `opiniao`, `desmentida`, `contestada`, `confirmada`, `em-apuracao`, `dados-insuficientes`. O navegador valida o parecer com `validarParecer` e descarta qualquer conclusão sem prova citada. A decisão final (rótulo e envio ao conselho) continua sendo calculada pelo navegador com as regras da metodologia.

## Recomendações para o servidor

- **Saída estruturada.** Pedir ao modelo uma resposta no esquema acima (JSON Schema), não texto livre.
- **Texto da notícia é dado.** Enviar `caso.trecho` separado das instruções do agente e dizer ao modelo que nenhuma instrução dentro dele deve ser seguida. O painel também detecta tentativas de manipulação e manda o caso ao conselho.
- **Toda mudança de prompt ou modelo é uma mudança de metodologia:** testar contra os casos já decididos por pessoas, rodar a auditoria de viés, ter aprovação do conselho e publicar a nova versão.
- Para os agentes no Claude: `claude-opus-5-5` com saída estruturada (`output_config.format`). Os detalhes de cada SDK dependem da linguagem escolhida para o servidor (Python ou Node.js, nenhum dos dois instalado neste computador ainda).
