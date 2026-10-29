# Colocar o site no ar de graça

O site fica no **GitHub Pages** e a coleta roda no **GitHub Actions** a cada 30 minutos, seguida do conselho de IA. Os dois são gratuitos para repositórios públicos, e não é preciso deixar nenhum computador ligado. O fluxo está em `.github/workflows/coletar-e-publicar.yml`. Só os modelos de IA são pagos (veja "Ligar o conselho de IA").

## Situação em 29/10/2026

O repositório `pjaandrade54-a11y/O-FAROL` já existe e é público, e as duas execuções da aba *Actions* coletaram as notícias, mas falharam no passo `configure-pages` com *"Get Pages site failed"*: **o GitHub Pages ainda não foi ligado.** Falta só o passo 5 abaixo (*Settings → Pages → Source: GitHub Actions*) e depois o passo 6.

## Uma vez só (cerca de 15 minutos)

1. **Crie uma conta** em [github.com](https://github.com), se ainda não tiver.
2. **Instale o GitHub Desktop** ([desktop.github.com](https://desktop.github.com)) e entre com a sua conta.
3. **Transforme a pasta em repositório.** No GitHub Desktop: *File → Add local repository…*, escolha a pasta `O Farol`. Ele vai dizer que a pasta ainda não é um repositório; clique em *create a repository*, mantenha o nome e clique em *Create repository*.
4. **Publique.** Clique em *Publish repository*. **Desmarque "Keep this code private"**: o GitHub Pages gratuito exige repositório público. Clique em *Publish repository*.
5. **Ligue o Pages.** No site do GitHub, abra o repositório e vá em *Settings → Pages*. Em *Build and deployment → Source*, escolha **GitHub Actions**.
6. **Rode a primeira coleta.** Na aba *Actions*, clique em *Coletar notícias e publicar o site* e depois em *Run workflow*. Em uns 2 minutos o site estará em `https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/`. O endereço exato aparece no resultado da execução e em *Settings → Pages*.

Depois disso, a coleta e a publicação acontecem sozinhas a cada 30 minutos.

## Ligar o conselho de IA

Sem chaves, o site funciona normalmente e as notícias aparecem como "Aguardando análise". Para ligar:

1. **Crie as chaves.** Anthropic: [console.anthropic.com](https://console.anthropic.com) → *API Keys*. OpenAI: [platform.openai.com](https://platform.openai.com) → *API keys*. Nas duas, cadastre um cartão e **defina um limite mensal de gasto** (*Limits* / *Billing*), para nunca ter surpresa.
2. **Guarde as chaves no GitHub, nunca nos arquivos.** No repositório: *Settings → Secrets and variables → Actions → New repository secret*. Crie `ANTHROPIC_API_KEY` e `OPENAI_API_KEY`, cada um com a sua chave.
3. **Rode uma vez para testar.** *Actions → Coletar notícias e publicar o site → Run workflow*. No passo "Conselho de IA" aparece cada notícia analisada e o rótulo dado.

Sem a chave da OpenAI, a Defesa roda no Claude, e o site mostra isso em cada parecer.

### Quanto custa

Cada notícia passa por três agentes (dois no Claude Opus 5.5 e um no GPT): estimativa de **US$ 0,05 a US$ 0,15 por notícia**. Só são analisadas as 5 notícias mais recentes de cada aba (as que aparecem na página inicial), e uma vez cada. Com o limite padrão de 40 notícias por dia, o gasto fica perto de **US$ 2 a 6 por dia**. O passo "Conselho de IA" mostra quantos tokens cada execução usou; compare com o painel de uso de cada empresa nos primeiros dias.

Ajustes, em *Settings → Secrets and variables → Actions → aba Variables → New repository variable* (todos opcionais):

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `IA_POR_DIA` | 40 | Máximo de notícias analisadas por dia (UTC). A principal trava de custo |
| `IA_POR_EXECUCAO` | 4 | Máximo por execução de 30 minutos |
| `IA_ESFORCO` | medium | Quanto o Claude raciocina: `low` custa menos, `high` analisa mais a fundo |
| `CLAUDE_MODELO` | claude-opus-5-5 | Modelo da Acusação e do Auditor de fontes |
| `OPENAI_MODELO` | gpt-6.1-terra | Modelo da Defesa. Troque quando a OpenAI lançar outro |

Mudar modelo ou esforço é mudar a metodologia: registre a mudança em `metodologia.html`.

### Conselho humano

Quando os agentes divergem, um parecer é descartado, o tema é sensível ou há suspeita de manipulação, o rótulo fica "provisório" e o fluxo abre um caso na aba **Issues** do repositório, com a etiqueta `conselho`, a notícia e os pareceres. O GitHub avisa por e-mail quem acompanha o repositório (*Watch → All Activity*). Para decidir: comente o motivo, aplique ao caso a etiqueta do rótulo final (`confirmada`, `contestada`, `desmentida`, `em-apuracao`, `dados-insuficientes` ou `opiniao`) e feche o caso. Na coleta seguinte, o site mostra a decisão do conselho no lugar do rótulo provisório.

## No dia a dia

- **Mudou algum arquivo?** No GitHub Desktop, escreva um resumo da mudança, clique em *Commit to main* e depois em *Push origin*. O site é republicado sozinho.
- **Cadastrou um veículo?** O mesmo: o `dados/veiculos.json` alterado vai no próximo envio.
- **Algo deu errado?** A aba *Actions* mostra cada execução. Uma execução vermelha tem o motivo no passo que falhou; o site continua no ar com a última versão boa.

## O que é bom saber

- **O código fica público.** Não há nada secreto nele. As chaves de API ficam em *Settings → Secrets and variables → Actions*, **nunca** dentro dos arquivos.
- **Atrasos.** O GitHub não garante o horário exato das execuções agendadas: em repositórios novos ou em horário de pico, uma execução pode atrasar bastante ou ser pulada. O fluxo roda nos minutos 7 e 37 de cada hora, fora da virada da hora, quando o GitHub fica mais lento. Com a página aberta, o site busca notícias novas sozinho a cada 5 minutos, então o leitor vê a coleta assim que ela é publicada.
- **60 dias sem mudanças.** Em repositório público, o GitHub pausa as execuções agendadas depois de 60 dias sem nenhuma atividade no repositório e avisa por e-mail. Basta enviar qualquer mudança ou reativar em *Actions*.
- **O banco** (`dados/farol.db`) não vai para o repositório. Ele passa de uma execução para a outra pelo cache do GitHub, com as notícias e as análises do conselho de IA, e as notícias com mais de 30 dias são apagadas. Se o cache sumir, a coleta seguinte recomeça do zero: as notícias da página inicial são analisadas de novo (dentro do limite diário), e as decisões do conselho humano são recuperadas dos casos fechados.
- **Ficam fora do repositório:** a pasta `referencia/` (o PDF do mockup) e as configurações locais em `.claude/`.
- **Testes locais continuam iguais:** `python -m coletor coletar` e o servidor de `ferramentas/servidor.ps1`.
