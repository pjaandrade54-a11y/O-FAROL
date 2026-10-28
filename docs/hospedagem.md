# Colocar o site no ar de graça

O site fica no **GitHub Pages** e a coleta roda no **GitHub Actions** a cada 30 minutos. Os dois são gratuitos para repositórios públicos, e não é preciso deixar nenhum computador ligado. O fluxo está em `.github/workflows/coletar-e-publicar.yml`.

## Uma vez só (cerca de 15 minutos)

1. **Crie uma conta** em [github.com](https://github.com), se ainda não tiver.
2. **Instale o GitHub Desktop** ([desktop.github.com](https://desktop.github.com)) e entre com a sua conta.
3. **Transforme a pasta em repositório.** No GitHub Desktop: *File → Add local repository…*, escolha a pasta `O Farol`. Ele vai dizer que a pasta ainda não é um repositório; clique em *create a repository*, mantenha o nome e clique em *Create repository*.
4. **Publique.** Clique em *Publish repository*. **Desmarque "Keep this code private"**: o GitHub Pages gratuito exige repositório público. Clique em *Publish repository*.
5. **Ligue o Pages.** No site do GitHub, abra o repositório e vá em *Settings → Pages*. Em *Build and deployment → Source*, escolha **GitHub Actions**.
6. **Rode a primeira coleta.** Na aba *Actions*, clique em *Coletar notícias e publicar o site* e depois em *Run workflow*. Em uns 2 minutos o site estará em `https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/`. O endereço exato aparece no resultado da execução e em *Settings → Pages*.

Depois disso, a coleta e a publicação acontecem sozinhas a cada 30 minutos.

## No dia a dia

- **Mudou algum arquivo?** No GitHub Desktop, escreva um resumo da mudança, clique em *Commit to main* e depois em *Push origin*. O site é republicado sozinho.
- **Cadastrou um veículo?** O mesmo: o `dados/veiculos.json` alterado vai no próximo envio.
- **Algo deu errado?** A aba *Actions* mostra cada execução. Uma execução vermelha tem o motivo no passo que falhou; o site continua no ar com a última versão boa.

## O que é bom saber

- **O código fica público.** Hoje não há nada secreto nele. Quando houver chaves de API (para a IA), elas vão em *Settings → Secrets and variables → Actions*, **nunca** dentro dos arquivos.
- **Atrasos.** O GitHub não garante o horário exato das execuções agendadas; atrasos de alguns minutos são normais.
- **60 dias sem mudanças.** Em repositório público, o GitHub pausa as execuções agendadas depois de 60 dias sem nenhuma atividade no repositório e avisa por e-mail. Basta enviar qualquer mudança ou reativar em *Actions*.
- **O banco** (`dados/farol.db`) não vai para o repositório. Ele passa de uma execução para a outra pelo cache do GitHub, e as notícias com mais de 30 dias são apagadas. Se o cache sumir, a coleta seguinte recomeça do zero sem problema.
- **Ficam fora do repositório:** a pasta `referencia/` (o PDF do mockup) e as configurações locais em `.claude/`.
- **Testes locais continuam iguais:** `python -m coletor coletar` e o servidor de `ferramentas/servidor.ps1`.
