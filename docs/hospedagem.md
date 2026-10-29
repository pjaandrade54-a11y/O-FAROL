# Colocar o site no ar de graça

O site fica no **GitHub Pages** e a coleta roda no **GitHub Actions** a cada 30 minutos, seguida do conselho de IA nos modelos gratuitos do GitHub Models. Tudo é gratuito para repositórios públicos, e não é preciso deixar nenhum computador ligado. O fluxo está em `.github/workflows/coletar-e-publicar.yml`.

O site está no ar em **https://pjaandrade54-a11y.github.io/O-FAROL/**.

## Uma vez só (cerca de 15 minutos)

1. **Crie uma conta** em [github.com](https://github.com), se ainda não tiver.
2. **Instale o GitHub Desktop** ([desktop.github.com](https://desktop.github.com)) e entre com a sua conta.
3. **Transforme a pasta em repositório.** No GitHub Desktop: *File → Add local repository…*, escolha a pasta `O Farol`. Ele vai dizer que a pasta ainda não é um repositório; clique em *create a repository*, mantenha o nome e clique em *Create repository*.
4. **Publique.** Clique em *Publish repository*. **Desmarque "Keep this code private"**: o GitHub Pages gratuito exige repositório público. Clique em *Publish repository*.
5. **Ligue o Pages.** No site do GitHub, abra o repositório e vá em *Settings → Pages*. Em *Build and deployment → Source*, escolha **GitHub Actions**.
6. **Rode a primeira coleta.** Na aba *Actions*, clique em *Coletar notícias e publicar o site* e depois em *Run workflow*. Em uns 2 minutos o site estará em `https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/`. O endereço exato aparece no resultado da execução e em *Settings → Pages*.

Depois disso, a coleta e a publicação acontecem sozinhas a cada 30 minutos.

## Conselho de IA (gratuito)

O conselho de IA já vem ligado e **não custa nada**: ele usa os modelos gratuitos do **GitHub Models**, com a permissão que o próprio GitHub Actions fornece (`models: read` no fluxo). Não é preciso chave, conta paga nem cartão.

- **Modelos:** a cada execução, o fluxo consulta o catálogo do GitHub Models e escolhe um modelo para cada agente (Acusação e Defesa de empresas diferentes). O passo "Conselho de IA" mostra quais foram usados, e o site mostra o modelo de cada parecer.
- **Cota gratuita:** o GitHub limita os pedidos por dia e por minuto de cada modelo. Cada notícia usa 3 pedidos (um por agente). Por isso, o padrão é analisar no máximo **15 notícias por dia**, 3 por execução. Quando a cota acaba, a execução para e as notícias restantes ficam "Aguardando análise" até a cota renovar. Não há cobrança.
- **Escolher outros modelos:** crie as variáveis `GITHUB_MODELO_ACUSACAO`, `GITHUB_MODELO_DEFESA` ou `GITHUB_MODELO_FONTES` com o id do modelo (por exemplo `openai/gpt-4.1`), como aparece no passo "Conselho de IA" ou em [github.com/marketplace/models](https://github.com/marketplace/models).

Variáveis opcionais, em *Settings → Secrets and variables → Actions → aba Variables → New repository variable*:

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `IA_PROVEDOR` | github | `github` (gratuito), `anthropic` (pago, com as chaves abaixo) ou `desligado` |
| `IA_POR_DIA` | 15 | Máximo de notícias analisadas por dia (UTC) |
| `IA_POR_EXECUCAO` | 3 | Máximo por execução de 30 minutos |
| `GITHUB_MODELO_ACUSACAO`, `GITHUB_MODELO_DEFESA`, `GITHUB_MODELO_FONTES` | escolhidos pelo catálogo | Modelo de cada agente no GitHub Models |

Mudar modelo é mudar a metodologia: registre a mudança em `metodologia.html`.

### Opção paga: Claude e GPT

Para usar o Claude Opus 5.5 (Acusação e Auditor de fontes) e o GPT (Defesa), crie a variável `IA_PROVEDOR` com o valor `anthropic` e guarde as chaves em *Settings → Secrets and variables → Actions → New repository secret*: `ANTHROPIC_API_KEY` e, se quiser, `OPENAI_API_KEY` (sem ela, a Defesa roda no Claude). As contas precisam de créditos; defina um limite mensal de gasto em cada uma. Estimativa: US$ 0,05 a 0,15 por notícia. Nesse modo também valem as variáveis `CLAUDE_MODELO`, `OPENAI_MODELO` e `IA_ESFORCO` (`low`, `medium` ou `high`).

### Conselho humano

Quando os agentes divergem, um parecer é descartado, o tema é sensível ou há suspeita de manipulação, o rótulo fica "provisório" e o fluxo abre um caso na aba **Issues** do repositório, com a etiqueta `conselho`, a notícia e os pareceres. O GitHub avisa por e-mail quem acompanha o repositório (*Watch → All Activity*). Para decidir: comente o motivo, aplique ao caso a etiqueta do rótulo final (`confirmada`, `contestada`, `desmentida`, `em-apuracao`, `dados-insuficientes` ou `opiniao`) e feche o caso. Na coleta seguinte, o site mostra a decisão do conselho no lugar do rótulo provisório.

## No dia a dia

- **Mudou algum arquivo?** No GitHub Desktop, escreva um resumo da mudança, clique em *Commit to main* e depois em *Push origin*. O site é republicado sozinho.
- **Cadastrou um veículo?** O mesmo: o `dados/veiculos.json` alterado vai no próximo envio.
- **Algo deu errado?** A aba *Actions* mostra cada execução. Uma execução vermelha tem o motivo no passo que falhou; o site continua no ar com a última versão boa.

## O que é bom saber

- **O código fica público.** Não há nada secreto nele. Se um dia usar chaves de API (opção paga), elas ficam em *Settings → Secrets and variables → Actions*, **nunca** dentro dos arquivos.
- **Atrasos.** O GitHub não garante o horário exato das execuções agendadas: em repositórios novos ou em horário de pico, uma execução pode atrasar bastante ou ser pulada. O fluxo roda nos minutos 7 e 37 de cada hora, fora da virada da hora, quando o GitHub fica mais lento. Com a página aberta, o site busca notícias novas sozinho a cada 5 minutos, então o leitor vê a coleta assim que ela é publicada.
- **60 dias sem mudanças.** Em repositório público, o GitHub pausa as execuções agendadas depois de 60 dias sem nenhuma atividade no repositório e avisa por e-mail. Basta enviar qualquer mudança ou reativar em *Actions*.
- **O banco** (`dados/farol.db`) não vai para o repositório. Ele passa de uma execução para a outra pelo cache do GitHub, com as notícias e as análises do conselho de IA, e as notícias com mais de 30 dias são apagadas. Se o cache sumir, a coleta seguinte recomeça do zero: as notícias da página inicial são analisadas de novo (dentro do limite diário), e as decisões do conselho humano são recuperadas dos casos fechados.
- **Ficam fora do repositório:** a pasta `referencia/` (o PDF do mockup) e as configurações locais em `.claude/`.
- **Testes locais continuam iguais:** `python -m coletor coletar` e o servidor de `ferramentas/servidor.ps1`.
