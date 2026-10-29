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

O conselho de IA usa o **plano gratuito da API do Google Gemini**: sem cartão e sem cobrança.

**Para ligar (uma vez só, cerca de 3 minutos):**

1. Entre em [aistudio.google.com](https://aistudio.google.com) com uma conta Google e clique em **Get API key → Create API key**. Copie a chave (começa com `AIza`).
2. No GitHub, abra o repositório e vá em **Settings → Secrets and variables → Actions → New repository secret**. Em *Name*, escreva `GEMINI_API_KEY`; em *Secret*, cole a chave; clique em **Add secret**.
3. Rode **Actions → Coletar notícias e publicar o site → Run workflow**. O passo "Conselho de IA" mostra os modelos escolhidos e cada notícia analisada.

**Como funciona:**

- **Modelos:** a cada execução, o fluxo lista os modelos que a chave pode usar e escolhe o Gemini Flash estável mais novo para a Acusação e o Auditor de fontes, e o Flash-Lite para a Defesa. Os três são do Google: a diversidade entre empresas só existe na opção paga. Cada parecer mostra o modelo que o produziu.
- **Cota gratuita:** o Google limita os pedidos por minuto e por dia. Cada notícia usa 3 pedidos (um por agente), com uma pausa entre eles. O padrão é analisar no máximo **15 notícias por dia**, 3 por execução. Quando a cota acaba, a execução para e as notícias restantes ficam "Aguardando análise" até a cota renovar.
- **Privacidade:** no plano gratuito, o Google pode usar os textos enviados para melhorar os produtos dele. Aqui vão só títulos e resumos de notícias já públicas.

Variáveis opcionais, em *Settings → Secrets and variables → Actions → aba Variables → New repository variable*:

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `IA_PROVEDOR` | gemini | `gemini` (gratuito), `github` (GitHub Models, gratuito, mas sem funcionar em 29/10/2026), `anthropic` (pago) ou `desligado` |
| `IA_POR_DIA` | 15 | Máximo de notícias analisadas por dia (UTC) |
| `IA_POR_EXECUCAO` | 3 | Máximo por execução de 30 minutos |
| `GEMINI_MODELO_ACUSACAO`, `GEMINI_MODELO_DEFESA`, `GEMINI_MODELO_FONTES` | escolhidos pela lista | Modelo de cada agente, por exemplo `gemini-2.5-flash` |

Mudar modelo é mudar a metodologia: registre a mudança em `metodologia.html`.

### GitHub Models

Com `IA_PROVEDOR` = `github`, os agentes usam os modelos gratuitos do GitHub Models, pelo `GITHUB_TOKEN` do próprio Actions. Em 29/10/2026 o serviço respondia só "OK" em texto, sem analisar nada; o código está pronto para quando voltar a funcionar. Modelos por variável: `GITHUB_MODELO_ACUSACAO`, `GITHUB_MODELO_DEFESA`, `GITHUB_MODELO_FONTES`.

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
