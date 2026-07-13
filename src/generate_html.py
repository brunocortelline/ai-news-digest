"""
Gera o dashboard HTML estático (boletim semanal de IA) a partir da lista de
notícias já resumidas/traduzidas. Publica em docs/index.html (link fixo,
sempre a edição mais recente) e mantém um arquivo de arquivo histórico em
docs/arquivo/AAAA-MM-DD.html.
"""

from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

DOCS_DIR = Path(__file__).parent.parent / "docs"
ARQUIVO_DIR = DOCS_DIR / "arquivo"

MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _data_extenso_pt(dt: datetime) -> str:
    return f"{dt.day} de {MESES_PT[dt.month - 1]} de {dt.year}"


def _agrupar_por_categoria(artigos):
    grupos = defaultdict(list)
    for a in artigos:
        grupos[a.get("categoria", "Outros")].append(a)
    return grupos


def _card_html(artigo) -> str:
    data_str = ""
    if artigo.get("data_publicacao"):
        try:
            data_str = artigo["data_publicacao"].strftime("%d/%m/%Y")
        except Exception:
            data_str = ""

    por_que = artigo.get("por_que_importa", "")
    por_que_html = (
        f'<p class="por-que"><strong>Por que importa:</strong> {por_que}</p>'
        if por_que
        else ""
    )

    return f"""
    <article class="card">
      <div class="card-meta">
        <span class="fonte">{artigo.get('fonte', '')}</span>
        {f'<span class="data">{data_str}</span>' if data_str else ''}
      </div>
      <h3><a href="{artigo.get('link', '#')}" target="_blank" rel="noopener">{artigo.get('titulo_pt', artigo.get('titulo_original',''))}</a></h3>
      <p class="resumo">{artigo.get('resumo_pt', '')}</p>
      {por_que_html}
    </article>
    """


def gerar_html(artigos: list[dict]) -> str:
    agora = datetime.now(timezone.utc)
    grupos = _agrupar_por_categoria(artigos)

    secoes_html = ""
    for categoria, itens in grupos.items():
        cards = "\n".join(_card_html(a) for a in itens)
        secoes_html += f"""
        <section class="categoria">
          <h2>{categoria}</h2>
          <div class="cards">
            {cards}
          </div>
        </section>
        """

    total = len(artigos)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Boletim Semanal de IA — {_data_extenso_pt(agora)}</title>
<style>
  :root {{
    --bg: #0f1115;
    --card-bg: #171a21;
    --text: #e8e9ec;
    --text-muted: #9aa0aa;
    --accent: #7c9eff;
    --border: #262b35;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.5;
  }}
  header {{
    padding: 48px 24px 24px;
    max-width: 900px;
    margin: 0 auto;
  }}
  header h1 {{
    font-size: 28px;
    margin: 0 0 8px;
  }}
  header p {{
    color: var(--text-muted);
    margin: 0;
  }}
  main {{
    max-width: 900px;
    margin: 0 auto;
    padding: 0 24px 64px;
  }}
  .categoria {{
    margin-top: 40px;
  }}
  .categoria h2 {{
    font-size: 18px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }}
  .cards {{
    display: grid;
    gap: 16px;
    margin-top: 16px;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
  }}
  .card-meta {{
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 8px;
  }}
  .card h3 {{
    margin: 0 0 8px;
    font-size: 17px;
  }}
  .card h3 a {{
    color: var(--text);
    text-decoration: none;
  }}
  .card h3 a:hover {{
    color: var(--accent);
    text-decoration: underline;
  }}
  .resumo {{
    margin: 0 0 8px;
    color: var(--text);
  }}
  .por-que {{
    margin: 0;
    font-size: 14px;
    color: var(--text-muted);
    border-left: 2px solid var(--accent);
    padding-left: 10px;
  }}
  footer {{
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
    color: var(--text-muted);
    font-size: 13px;
    border-top: 1px solid var(--border);
  }}
</style>
</head>
<body>
  <header>
    <h1>🤖 Boletim Semanal de IA</h1>
    <p>Edição de {_data_extenso_pt(agora)} · {total} notícias selecionadas</p>
  </header>
  <main>
    {secoes_html}
  </main>
  <footer>
    Gerado automaticamente a partir de fontes públicas, resumido e traduzido com a API da Claude (Anthropic).
  </footer>
</body>
</html>
"""


def publicar(artigos: list[dict]):
    DOCS_DIR.mkdir(exist_ok=True)
    ARQUIVO_DIR.mkdir(exist_ok=True)

    html = gerar_html(artigos)

    # sempre atualiza o link fixo
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")

    # mantém histórico
    nome_arquivo = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".html"
    (ARQUIVO_DIR / nome_arquivo).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    from fetch import buscar_noticias
    from summarize import processar_lista

    noticias = buscar_noticias()
    processadas = processar_lista(noticias)
    publicar(processadas)
    print(f"Dashboard gerado em: {DOCS_DIR / 'index.html'}")
