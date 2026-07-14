"""
Gera o dashboard HTML estático (boletim semanal de IA) a partir da lista de
notícias já resumidas/traduzidas. Publica em docs/index.html (link fixo,
sempre a edição mais recente) e mantém um arquivo de arquivo histórico em
docs/arquivo/AAAA-MM-DD.html.

Recursos do dashboard:
- busca por texto (título, resumo, fonte)
- filtro por categoria
- favoritar notícias (salvo no navegador via localStorage - funciona porque
  este é um site real hospedado no GitHub Pages, não um sandbox)
- tema claro, um "painel de sinais" com cor própria por categoria
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from collections import OrderedDict

DOCS_DIR = Path(__file__).parent.parent / "docs"
ARQUIVO_DIR = DOCS_DIR / "arquivo"

MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# Paleta por categoria (cor de destaque, fundo do selo, texto do selo).
# Categorias não listadas aqui caem no CICLO_FALLBACK, na ordem em que aparecem.
CORES_CATEGORIA = {
    "Labs & Modelos":          {"cor": "#E08D2D", "selo_bg": "#FDEEDC", "selo_texto": "#8A4B12"},
    "Mercado & Negócios":      {"cor": "#1D9E75", "selo_bg": "#DFF5F0", "selo_texto": "#0F6E56"},
    "Pesquisa & Tendências":   {"cor": "#7F77DD", "selo_bg": "#EDEAFB", "selo_texto": "#3C3489"},
    "Comunidade & Devs":       {"cor": "#D4537E", "selo_bg": "#FBE9EF", "selo_texto": "#8A2A50"},
}
CICLO_FALLBACK = [
    {"cor": "#5A7CB0", "selo_bg": "#E9EEF7", "selo_texto": "#33456B"},
    {"cor": "#B0805A", "selo_bg": "#F7EEE7", "selo_texto": "#6B4A2E"},
]


def _data_extenso_pt(dt: datetime) -> str:
    return f"{dt.day} de {MESES_PT[dt.month - 1]} de {dt.year}"


def _cor_para_categoria(categoria: str, mapa_fallback: dict) -> dict:
    if categoria in CORES_CATEGORIA:
        return CORES_CATEGORIA[categoria]
    if categoria not in mapa_fallback:
        indice = len(mapa_fallback) % len(CICLO_FALLBACK)
        mapa_fallback[categoria] = CICLO_FALLBACK[indice]
    return mapa_fallback[categoria]


def _preparar_artigos_para_js(artigos: list[dict]) -> list[dict]:
    """Converte os artigos para um formato serializável em JSON, já com
    a cor da categoria resolvida e a data formatada em PT-BR."""
    mapa_fallback = {}
    preparados = []

    # preserva ordem de categorias como aparecem, para os filtros
    categorias_ordem = list(OrderedDict.fromkeys(a.get("categoria", "Outros") for a in artigos))
    for cat in categorias_ordem:
        _cor_para_categoria(cat, mapa_fallback)

    for a in artigos:
        categoria = a.get("categoria", "Outros")
        cores = _cor_para_categoria(categoria, mapa_fallback)

        data_str = ""
        if a.get("data_publicacao"):
            try:
                data_str = a["data_publicacao"].strftime("%d/%m/%Y")
            except Exception:
                data_str = ""

        preparados.append({
            "titulo": a.get("titulo_pt") or a.get("titulo_original", ""),
            "resumo": a.get("resumo_pt", ""),
            "por_que_importa": a.get("por_que_importa", ""),
            "link": a.get("link", "#"),
            "fonte": a.get("fonte", ""),
            "categoria": categoria,
            "data": data_str,
            "cor": cores["cor"],
            "selo_bg": cores["selo_bg"],
            "selo_texto": cores["selo_texto"],
        })

    return preparados


def _categorias_para_js(artigos_preparados: list[dict]) -> list[dict]:
    vistas = OrderedDict()
    for a in artigos_preparados:
        if a["categoria"] not in vistas:
            vistas[a["categoria"]] = {"nome": a["categoria"], "cor": a["cor"]}
    return list(vistas.values())


TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Boletim Semanal de IA — __EDICAO__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600&family=Inter:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #F4F6FB;
    --card-bg: #FFFFFF;
    --text: #1B2340;
    --text-secondary: #4B5470;
    --text-muted: #848DA6;
    --border: #E1E5F0;
    --border-strong: #C9CFE0;
    --accent: #5A4FCF;
    --accent-bg: #EDEAFB;
    --favorito: #E08D2D;
    --favorito-bg: #FDEEDC;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.55;
  }
  .envelope {
    max-width: 880px;
    margin: 0 auto;
    padding: 0 24px 80px;
  }
  header {
    padding: 48px 0 28px;
    position: relative;
  }
  .radar-fundo {
    position: absolute;
    top: -40px;
    right: -60px;
    width: 260px;
    height: 260px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(90,79,207,0.10) 0%, rgba(90,79,207,0) 70%);
    pointer-events: none;
    z-index: 0;
  }
  .titulo-linha {
    display: flex;
    align-items: center;
    gap: 12px;
    position: relative;
    z-index: 1;
  }
  .radar-icone {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--accent);
    position: relative;
    flex-shrink: 0;
  }
  .radar-icone::before, .radar-icone::after {
    content: "";
    position: absolute;
    border: 1.5px solid rgba(255,255,255,0.55);
    border-radius: 50%;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
  }
  .radar-icone::before { width: 22px; height: 22px; }
  .radar-icone::after { width: 12px; height: 12px; background: #fff; border: none; }
  header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 28px;
    font-weight: 600;
    margin: 0;
    letter-spacing: -0.01em;
  }
  header p.subtitulo {
    color: var(--text-muted);
    margin: 6px 0 0;
    font-size: 14px;
    font-family: 'IBM Plex Mono', monospace;
    position: relative;
    z-index: 1;
  }
  .controles {
    margin-top: 28px;
    position: relative;
    z-index: 1;
  }
  .busca {
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
  }
  .busca svg { flex-shrink: 0; color: var(--text-muted); }
  .busca input {
    border: none;
    outline: none;
    font-size: 15px;
    font-family: 'Inter', sans-serif;
    color: var(--text);
    width: 100%;
    background: transparent;
  }
  .busca input::placeholder { color: var(--text-muted); }
  .filtros {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
  }
  .chip {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12.5px;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--card-bg);
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: border-color 0.15s ease;
  }
  .chip:hover { border-color: var(--border-strong); }
  .chip .ponto {
    width: 7px; height: 7px; border-radius: 50%;
    display: inline-block;
  }
  .chip.ativo {
    background: var(--accent-bg);
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 500;
  }
  .chip.favoritos-chip.ativo {
    background: var(--favorito-bg);
    border-color: var(--favorito);
    color: #8A4B12;
  }
  .contador {
    margin-top: 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12.5px;
    color: var(--text-muted);
  }
  main { margin-top: 8px; }
  .lista {
    display: grid;
    gap: 14px;
    margin-top: 8px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--card-cor, var(--accent));
    border-radius: 10px;
    padding: 18px 20px;
    position: relative;
  }
  .card-topo {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
  }
  .card-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--text-muted);
    flex-wrap: wrap;
  }
  .selo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    padding: 3px 9px;
    border-radius: 999px;
    font-weight: 500;
  }
  .favorito-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    padding: 2px;
    line-height: 0;
    flex-shrink: 0;
  }
  .favorito-btn:hover { color: var(--favorito); }
  .favorito-btn.ativo { color: var(--favorito); }
  .card h3 {
    margin: 0 0 8px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 17px;
    font-weight: 600;
    line-height: 1.35;
  }
  .card h3 a {
    color: var(--text);
    text-decoration: none;
  }
  .card h3 a:hover { color: var(--accent); }
  .resumo {
    margin: 0 0 10px;
    color: var(--text-secondary);
    font-size: 14.5px;
  }
  .por-que {
    margin: 0;
    font-size: 13.5px;
    color: var(--text-secondary);
    background: var(--bg);
    border-left: 2px solid var(--card-cor, var(--accent));
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
  }
  .por-que strong { color: var(--text); }
  .vazio {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
  }
  .vazio p { margin: 4px 0; }
  footer {
    margin-top: 48px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 12.5px;
    font-family: 'IBM Plex Mono', monospace;
  }
  @media (max-width: 480px) {
    header h1 { font-size: 23px; }
    .card { padding: 15px 16px; }
  }
</style>
</head>
<body>
  <div class="envelope">
    <header>
      <div class="radar-fundo"></div>
      <div class="titulo-linha">
        <div class="radar-icone"></div>
        <h1>Boletim Semanal de IA</h1>
      </div>
      <p class="subtitulo">edição de __EDICAO__ · __TOTAL__ notícias captadas</p>

      <div class="controles">
        <div class="busca">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" id="campo-busca" placeholder="Buscar por título, fonte ou assunto...">
        </div>
        <div class="filtros" id="filtros"></div>
      </div>

      <p class="contador" id="contador"></p>
    </header>

    <main>
      <div class="lista" id="lista-artigos"></div>
    </main>

    <footer>
      gerado automaticamente a partir de fontes públicas · resumido e traduzido com a API da Claude (Anthropic) · favoritos salvos neste navegador
    </footer>
  </div>

  <script id="dados-artigos" type="application/json">__ARTIGOS_JSON__</script>
  <script>
    const artigos = JSON.parse(document.getElementById('dados-artigos').textContent);
    const categorias = __CATEGORIAS_JSON__;
    const CHAVE_FAVORITOS = 'ai-digest-favoritos';

    let favoritos = new Set(JSON.parse(localStorage.getItem(CHAVE_FAVORITOS) || '[]'));
    let categoriaAtiva = 'todas';
    let somenteFavoritos = false;
    let termoBusca = '';

    function salvarFavoritos() {
      localStorage.setItem(CHAVE_FAVORITOS, JSON.stringify([...favoritos]));
    }

    function escaparHtml(texto) {
      const div = document.createElement('div');
      div.textContent = texto || '';
      return div.innerHTML;
    }

    function normalizar(texto) {
      return (texto || '').toLowerCase();
    }

    function artigosFiltrados() {
      return artigos.filter(a => {
        if (somenteFavoritos && !favoritos.has(a.link)) return false;
        if (categoriaAtiva !== 'todas' && a.categoria !== categoriaAtiva) return false;
        if (termoBusca) {
          const texto = normalizar(a.titulo + ' ' + a.resumo + ' ' + a.fonte);
          if (!texto.includes(normalizar(termoBusca))) return false;
        }
        return true;
      });
    }

    function renderizarFiltros() {
      const container = document.getElementById('filtros');
      let html = '<span class="chip todas-chip" data-cat="todas">todas</span>';
      categorias.forEach(cat => {
        html += `<span class="chip" data-cat="${escaparHtml(cat.nome)}"><span class="ponto" style="background:${cat.cor}"></span>${escaparHtml(cat.nome)}</span>`;
      });
      html += '<span class="chip favoritos-chip" data-cat="__favoritos__">&#9733; favoritos</span>';
      container.innerHTML = html;

      container.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
          const cat = chip.dataset.cat;
          if (cat === '__favoritos__') {
            somenteFavoritos = !somenteFavoritos;
          } else {
            categoriaAtiva = cat;
          }
          atualizarEstadoChips();
          renderizarLista();
        });
      });
      atualizarEstadoChips();
    }

    function atualizarEstadoChips() {
      document.querySelectorAll('.chip').forEach(chip => {
        const cat = chip.dataset.cat;
        if (cat === '__favoritos__') {
          chip.classList.toggle('ativo', somenteFavoritos);
        } else {
          chip.classList.toggle('ativo', cat === categoriaAtiva);
        }
      });
    }

    function cardHtml(a) {
      const ehFavorito = favoritos.has(a.link);
      const porQue = a.por_que_importa
        ? `<p class="por-que"><strong>Por que importa:</strong> ${escaparHtml(a.por_que_importa)}</p>`
        : '';
      return `
      <article class="card" style="--card-cor:${a.cor}">
        <div class="card-topo">
          <div class="card-meta">
            <span class="selo" style="background:${a.selo_bg};color:${a.selo_texto}">${escaparHtml(a.categoria)}</span>
            <span>${escaparHtml(a.fonte)}</span>
            ${a.data ? `<span>${a.data}</span>` : ''}
          </div>
          <button class="favorito-btn ${ehFavorito ? 'ativo' : ''}" data-link="${escaparHtml(a.link)}" aria-label="Favoritar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="${ehFavorito ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="1.8"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          </button>
        </div>
        <h3><a href="${escaparHtml(a.link)}" target="_blank" rel="noopener">${escaparHtml(a.titulo)}</a></h3>
        <p class="resumo">${escaparHtml(a.resumo)}</p>
        ${porQue}
      </article>
      `;
    }

    function renderizarLista() {
      const lista = artigosFiltrados();
      const container = document.getElementById('lista-artigos');
      const contador = document.getElementById('contador');

      contador.textContent = lista.length + (lista.length === 1 ? ' notícia exibida' : ' notícias exibidas');

      if (lista.length === 0) {
        container.innerHTML = `
          <div class="vazio">
            <p><strong>Nenhum sinal encontrado com esses filtros.</strong></p>
            <p>Tente limpar a busca ou escolher outra categoria.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = lista.map(cardHtml).join('');

      container.querySelectorAll('.favorito-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const link = btn.dataset.link;
          if (favoritos.has(link)) {
            favoritos.delete(link);
          } else {
            favoritos.add(link);
          }
          salvarFavoritos();
          renderizarLista();
        });
      });
    }

    document.getElementById('campo-busca').addEventListener('input', (e) => {
      termoBusca = e.target.value;
      renderizarLista();
    });

    renderizarFiltros();
    renderizarLista();
  </script>
</body>
</html>
"""


def gerar_html(artigos: list[dict]) -> str:
    agora = datetime.now(timezone.utc)
    artigos_preparados = _preparar_artigos_para_js(artigos)
    categorias = _categorias_para_js(artigos_preparados)

    artigos_json = json.dumps(artigos_preparados, ensure_ascii=False).replace("</", "<\\/")
    categorias_json = json.dumps(categorias, ensure_ascii=False).replace("</", "<\\/")

    html = TEMPLATE_HTML
    html = html.replace("__EDICAO__", _data_extenso_pt(agora))
    html = html.replace("__TOTAL__", str(len(artigos)))
    html = html.replace("__ARTIGOS_JSON__", artigos_json)
    html = html.replace("__CATEGORIAS_JSON__", categorias_json)
    return html


def publicar(artigos: list[dict]):
    DOCS_DIR.mkdir(exist_ok=True)
    ARQUIVO_DIR.mkdir(exist_ok=True)

    html = gerar_html(artigos)

    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")

    nome_arquivo = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".html"
    (ARQUIVO_DIR / nome_arquivo).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    from fetch import buscar_noticias
    from summarize import processar_lista

    noticias = buscar_noticias()
    processadas = processar_lista(noticias)
    publicar(processadas)
    print(f"Dashboard gerado em: {DOCS_DIR / 'index.html'}")
