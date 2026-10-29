# O Farol

Agregador de notícias com rótulos de confiabilidade e cobertura local, em fase de testes. Piloto em Aracaju (SE).

- **Site:** páginas estáticas (`index.html`, `painel.html`, `metodologia.html`, `quem-somos.html`, `contestar.html`, `privacidade.html`).
- **Coletor:** `python -m coletor coletar` lê os feeds RSS de `dados/veiculos.json` e gera `dados/noticias.json`. Veja [docs/coletor.md](docs/coletor.md).
- **Conselho de IA:** `python -m coletor analisar` roda os agentes (plano gratuito do Google Gemini; Claude e GPT como opção paga) nas notícias da página inicial e manda os casos difíceis ao conselho humano (issues com a etiqueta `conselho`). Código em `coletor/conselho.py`.
- **Painel de verificação:** protótipo em `js/painel/`, com casos fictícios. Contrato do futuro servidor de IA em [docs/servidor-modelos.md](docs/servidor-modelos.md).
- **Hospedagem:** GitHub Pages com coleta e conselho de IA automáticos a cada 30 minutos. Veja [docs/hospedagem.md](docs/hospedagem.md).
- **Testes:** `python -m unittest discover -s tests`

Contato: ofarolnws@gmail.com
