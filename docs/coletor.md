# Coletor de notícias

O coletor lê os feeds RSS dos veículos cadastrados, guarda as notícias novas e gera `dados/noticias.json`, um arquivo que o site pode ler direto. Usa só o Python (3.11 ou mais novo), sem instalar nada.

## Comandos

Rode na pasta do projeto:

| Comando | O que faz |
| --- | --- |
| `python -m coletor coletar` | Coleta todos os veículos ativos e atualiza `dados/noticias.json` |
| `python -m coletor coletar --veiculo g1` | Coleta um veículo só |
| `python -m coletor exportar` | Só regenera `dados/noticias.json` |
| `python -m coletor veiculos listar` | Mostra o cadastro, quantas notícias cada um tem e se o último feed deu erro |
| `python -m coletor veiculos testar [id]` | Baixa e lê os feeds sem gravar nada |
| `python -m coletor veiculos validar` | Confere `dados/veiculos.json` depois de editar à mão |
| `python -m coletor veiculos desativar id` | Para de coletar um veículo (`ativar` volta) |
| `python -m unittest discover -s tests` | Roda os testes |

## Cadastrar um veículo

```
python -m coletor veiculos adicionar --id jornal-exemplo --nome "Jornal Exemplo" --site https://exemplo.com.br --tipo jornal --abrangencia local --uf PE --cidade Recife --feed https://exemplo.com.br/feed/
```

O feed é testado antes de cadastrar. Tipos: agencia, jornal, portal, revista, radio, tv, blog, checador. Abrangência: local (aba Cidade), estadual (Estado), nacional (País), internacional (Mundo). Para um feed de checagens, acrescente `--checagens`.

Muitos sites em WordPress têm o feed em `endereço-do-site/feed/`.

Depois, complete à mão em `dados/veiculos.json` os campos de transparência (dono, CNPJ, expediente, política de correções) e de certificações. `null` quer dizer "ainda não verificado". A linha editorial só deve ser preenchida com o que o próprio veículo declarar.

Um feed pode ir para outra aba com `"escala"`: por exemplo, o feed internacional da Agência Brasil tem `"escala": "mundo"`.

## Cidades monitoradas

Os veículos de Sergipe cobrem o estado inteiro. Para preencher a aba Cidade, uma notícia estadual ou nacional que cita no título ou no resumo uma cidade de `dados/cidades.json` (hoje, Aracaju) vai para a aba Cidade. Para incluir outra cidade, acrescente uma linha nesse arquivo, por exemplo `{"nome": "Nossa Senhora do Socorro", "uf": "SE"}`.

A detecção é por nome. Ela ainda não sabe separar uma notícia nacional publicada por um portal sergipano: essas notícias aparecem na aba Estado até a etapa de classificação com IA.

Veículos de Sergipe que ainda não entraram: F5 News (site respondeu 503) e JL Política (500), que vale testar de novo; Jornal da Cidade (bloqueia o coletor, 403); Correio de Sergipe e g1 Sergipe (sem feed RSS válido).

## Como os dados são tratados

- Guardamos título, link, um resumo de até 280 caracteres e a data. O texto completo não é copiado; o leitor vai ao site do veículo.
- Notícias repetidas (mesmo link) são ignoradas. Links de redirecionamento e parâmetros `utm_` são limpos.
- Datas no futuro (há feeds que publicam assim) são trocadas pela hora da coleta.
- A coleta pede ao site só o que mudou desde a última vez (ETag e Last-Modified), o que poupa banda dos dois lados.
- `dados/farol.db` é o banco local (SQLite). Ele fica fora do controle de versão; `dados/noticias.json` é o que vai para o site.

## Antivírus e HTTPS

O AVG deste computador inspeciona conexões HTTPS com um certificado próprio, que o modo estrito do Python 3.13+ recusa. O coletor desliga só esse modo estrito; a cadeia de certificados continua sendo verificada. Num servidor sem antivírus, nada muda.

## Coletar sozinho neste computador

No Agendador de Tarefas do Windows, crie uma tarefa que rode a cada 30 minutos:

- Programa: `python`
- Argumentos: `-m coletor coletar`
- Iniciar em: a pasta do projeto
