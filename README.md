# Boletim Semanal de IA

Duas abas independentes, cada uma com seu próprio pipeline (busca → resumo/
tradução via API da Claude → dashboard estático), publicadas via GitHub
Pages:

- **📡 Boletim de IA** (`docs/index.html`) — modelos, mercado, comunidade dev.
- **🏭 Aplicações de IA por Setor** (`docs/produtos/index.html`) — o que
  empresas estão desenvolvendo e aplicando na prática, com foco em saúde,
  financeiro, energia e empresas de tecnologia.

As duas abas têm um link de navegação cruzada entre si, mas históricos,
favoritos e busca são completamente independentes.

## Como configurar (uma única vez)

1. **Criar um repositório no GitHub** e subir esta pasta para ele.

2. **Adicionar sua chave da API da Claude como secret do repositório:**
   - Settings → Secrets and variables → Actions → New repository secret
   - Nome: `ANTHROPIC_API_KEY`
   - Valor: sua chave da API (https://console.anthropic.com)

3. **Ativar o GitHub Pages:**
   - Settings → Pages → Build and deployment
   - Source: "Deploy from a branch"
   - Branch: `main`, pasta `/docs`
   - Salvar. O boletim geral fica em `https://SEU_USUARIO.github.io/ai-news-digest/`
     e a aba de produtos em `https://SEU_USUARIO.github.io/ai-news-digest/produtos/`

4. Pronto. O workflow em `.github/workflows/weekly-digest.yml` roda toda
   segunda-feira às 09h (horário de Brasília), gera as duas abas e publica.

## Rodar manualmente

Aba **Actions** do repositório → "Boletim Semanal de IA" → **Run workflow**.

## Rodar localmente (para testar)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sua-chave-aqui"
cd src
python main.py             # boletim geral
python main_produtos.py    # aba de produtos
```

## Diagnosticar fontes (quando alguma parecer estar trazendo pouco)

```bash
cd src
python diagnosticar_fontes.py            # testa as fontes do boletim geral
python diagnosticar_fontes.py produtos   # testa as fontes da aba de produtos
```

Mostra, fonte por fonte, quantos itens vieram, quantos passaram no filtro de
data, de palavra-chave e de conteúdo — e avisa se alguma URL parece quebrada.

## Migrar edições antigas para um layout novo

Sempre que o visual do dashboard mudar, rode isto uma vez para atualizar o
histórico já publicado (não chama a API, é só reformatação local):

```bash
cd src
python migrar_layout_arquivo.py todos
```

## Recursos do dashboard

- **Busca**: filtra por título, resumo ou fonte, em tempo real.
- **Filtro por categoria**: clique nos chips para ver só uma categoria.
- **Favoritos**: clique na estrela de uma notícia para marcá-la. Fica salvo
  no navegador (localStorage) daquele computador/navegador específico —
  cada aba (boletim/produtos) guarda seus favoritos separadamente.
- **Histórico navegável**: link "ver edições anteriores" em cada dashboard.

## Customizações fáceis

- **Adicionar/remover fontes:** edite `config/sources.yaml` (boletim geral)
  ou `config/sources_produtos.yaml` (aba de produtos). Qualquer feed RSS
  funciona.
- **Quantidade de notícias / diversidade de fontes:** `max_noticias` e
  `max_por_fonte` em cada config.
- **Critério de prioridade** quando uma fonte tem itens sobrando:
  `palavras_chave_prioridade` em cada config.
- **Mudar frequência:** ajuste o `cron` em `.github/workflows/weekly-digest.yml`.
- **Mudar o modelo da Claude usado:** variável de ambiente `ANTHROPIC_MODEL`.
- **Estilo do dashboard:** `src/generate_html.py` (compartilhado pelas duas abas).

## Domínio próprio

Veja a conversa/documentação do projeto para o passo a passo de configurar
um domínio personalizado (em vez de `usuario.github.io`) com HTTPS gratuito
via GitHub Pages.

## Estrutura

```
config/sources.yaml             # fontes do boletim geral
config/sources_produtos.yaml    # fontes da aba de produtos
src/fetch.py                    # busca, filtra e seleciona os feeds (as duas abas)
src/summarize.py                # resume e traduz via API da Claude (as duas abas)
src/generate_html.py            # gera os dashboards HTML (as duas abas)
src/main.py                     # orquestra o boletim geral
src/main_produtos.py            # orquestra a aba de produtos
src/diagnosticar_fontes.py      # ferramenta de diagnóstico de feeds
src/migrar_layout_arquivo.py    # ferramenta de migração de layout do histórico
docs/index.html                 # boletim geral — link fixo
docs/arquivo/                   # histórico do boletim geral
docs/produtos/index.html        # aba de produtos — link fixo
docs/produtos/arquivo/          # histórico da aba de produtos
.github/workflows/              # automação semanal via GitHub Actions
```
