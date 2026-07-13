# Boletim Semanal de IA

Pipeline simples que busca notícias de IA da semana, resume e traduz para
PT-BR usando a API da Claude, e publica um dashboard estático (link fixo,
sempre atualizado) via GitHub Pages.

## Como configurar (uma única vez)

1. **Criar um repositório no GitHub** e subir esta pasta para ele.

   ```bash
   git init
   git add .
   git commit -m "Boletim semanal de IA - setup inicial"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/ai-news-digest.git
   git push -u origin main
   ```

2. **Adicionar sua chave da API da Claude como secret do repositório:**
   - No GitHub: Settings → Secrets and variables → Actions → New repository secret
   - Nome: `ANTHROPIC_API_KEY`
   - Valor: sua chave da API (https://console.anthropic.com)

3. **Ativar o GitHub Pages:**
   - Settings → Pages → Build and deployment
   - Source: "Deploy from a branch"
   - Branch: `main`, pasta `/docs`
   - Salvar. O link fixo do seu boletim vai ficar em algo como:
     `https://SEU_USUARIO.github.io/ai-news-digest/`

4. Pronto. O workflow em `.github/workflows/weekly-digest.yml` já está
   configurado para rodar toda segunda-feira às 09h (horário de Brasília)
   automaticamente, buscar as notícias, resumir/traduzir e publicar.

## Rodar manualmente (sem esperar a segunda-feira)

Pela aba **Actions** do repositório no GitHub, escolha o workflow
"Boletim Semanal de IA" e clique em **Run workflow**.

## Rodar localmente (para testar)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sua-chave-aqui"
python src/main.py
```

O resultado fica em `docs/index.html` — pode abrir direto no navegador.

## Customizações fáceis

- **Adicionar/remover fontes:** edite `config/sources.yaml`. Qualquer feed
  RSS funciona.
- **Mudar frequência:** ajuste o `cron` em
  `.github/workflows/weekly-digest.yml` (ex: `0 12 * * 1,4` = segunda e quinta).
- **Mudar o modelo da Claude usado:** defina a variável de ambiente
  `ANTHROPIC_MODEL` (ex: no workflow, ou localmente).
- **Estilo do dashboard:** edite o CSS em `src/generate_html.py`.

## Estrutura

```
config/sources.yaml       # fontes de notícias e palavras-chave
src/fetch.py               # busca e filtra os feeds RSS
src/summarize.py           # resume e traduz via API da Claude
src/generate_html.py       # gera o dashboard HTML
src/main.py                 # orquestra o pipeline completo
docs/index.html             # link fixo, sempre a edição mais recente
docs/arquivo/AAAA-MM-DD.html # histórico de edições anteriores
.github/workflows/          # automação semanal via GitHub Actions
```
