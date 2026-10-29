# Coletor de notícias

O coletor lê os feeds RSS dos veículos cadastrados, guarda as notícias novas e gera `dados/noticias.json`, um arquivo que o site pode ler direto. Usa só o Python (3.11 ou mais novo), sem instalar nada.

## Comandos

Rode na pasta do projeto:

| Comando | O que faz |
| --- | --- |
| `python -m coletor coletar` | Coleta todos os veículos ativos e atualiza `dados/noticias.json` |
| `python -m coletor coletar --veiculo g1` | Coleta um veículo só |
| `python -m coletor exportar` | Só regenera `dados/noticias.json` |
| `python -m coletor analisar` | Rotula as notícias da página inicial (por regras, sem IA; ou com o Gemini gratuito, se houver `GEMINI_API_KEY`) e regenera `dados/noticias.json` (veja [hospedagem.md](hospedagem.md#análise-das-notícias-gratuita)) |
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

`dados/cidades.json` tem as 27 capitais, as maiores cidades de cada estado e os principais municípios de Sergipe, com coordenadas aproximadas (usadas no botão "Usar minha localização", que acha a cidade mais próxima no próprio navegador).

- Uma notícia **estadual** que cita no título ou no resumo uma cidade do mesmo estado vai para a aba Cidade daquela cidade.
- Uma notícia **nacional** que cita uma cidade fica na aba País e também aparece na aba Cidade de quem escolheu aquela cidade.
- Cidades marcadas com `"ambigua": true` têm nome que também é palavra comum ou outro lugar (Natal, Vitória, Serra, Palmas, Lagarto…): elas só contam em veículos do mesmo estado.
- Uma notícia que cita várias cidades aparece na aba Cidade de todas elas (e no arquivo de cada estado envolvido).
- Quando dois nomes se sobrepõem, vale o mais longo ("Juazeiro do Norte" não conta também como "Juazeiro").

Para incluir outra cidade, acrescente uma linha, por exemplo `{"nome": "Petrópolis", "uf": "RJ", "lat": -22.51, "lon": -43.18}`.

No site, o leitor escolhe a cidade (ou só o estado) no campo "Onde você está?". A escolha fica guardada no navegador dele. Sem escolha, o site mostra Aracaju (SE).

## Veículos e como testar feeds novos

O cadastro tem 127 veículos: todos os g1 estaduais, portais de cada estado, nacionais, internacionais em português e checadores. Os 113 incluídos em 29/10/2026 foram testados antes por `ferramentas/testar_candidatos.py`, que tenta o feed informado e os endereços comuns (`/feed/`, `/rss`, `/rss.xml`, `/feed`) e só aceita feed com notícias dos últimos 14 dias.

Para testar outros, ponha os candidatos em `ferramentas/candidatos.json` (mesmo formato) e rode na aba *Actions* o fluxo **Testar veículos candidatos**, ou no computador: `python ferramentas/testar_candidatos.py ferramentas/candidatos.json`. Para conferir os feeds já cadastrados: `python -m coletor veiculos testar`.

Ficaram de fora porque o feed não respondeu, não existe nos endereços testados ou está parado (vale testar de novo no futuro): 180graus, A Crítica, ACidade ON, AFP Checamos, Agência Amapá, Agência Aracaju de Notícias, Agência Brasília, Agência Estadual de Notícias (PR), Agência Pará, Agência Sergipe de Notícias, Agência de Notícias SC, Alô Sergipe, Band Jornalismo, Cada Minuto, Correio (BA), Correio Braziliense, Correio do Estado, Correio do Povo, D24AM, Diario de Pernambuco, Diário do Nordeste, EmSergipe, Extra, F5 News, Folha de Pernambuco, FolhaMax, GP1, GZH, Gazeta Digital, Hoje em Dia, Itatiaia, JL Política, Jornal Opção, Jornal de Brasília, Jornal do Brasil, Jornal do Commercio, Jornal do Comércio (RS), Jornal do Tocantins, Mais Goiás, Matinal, Meio Norte, MidiaNews, Midiamax, Novo Notícias, O Dia, O Estado do Maranhão, O Globo, O Liberal, O Popular, O Povo, O Tempo, Olhar Direto, Plural, Portal Itnet, Portal O Dia, Projeto Comprova, R7, RDNews, RioOnWatch, Roma News, Rondoniaovivo, Rondônia Dinâmica, Roraima em Tempo, SE Notícias, Saiba Mais, Spresso SP, T1 Notícias, Tribuna Hoje, Tribuna do Ceará, Tudo Rondônia, UOL, Universo Político e WSCOM. Também ficaram de fora o Estadão (feed geral parado desde 16/10) e o ge (só esporte, lotaria a aba País).

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
