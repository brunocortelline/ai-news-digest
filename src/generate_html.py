"""
Gera o dashboard HTML estático a partir da lista de notícias já resumidas/
traduzidas. Suporta múltiplos "sites" independentes (ex: o boletim geral de
IA e a aba de produtos/aplicações por setor), cada um com seu próprio
histórico de edições, mas com um link de navegação cruzada entre os dois.

Recursos do dashboard:
- busca por texto (título, resumo, fonte)
- filtro por categoria
- favoritar notícias (salvo no navegador via localStorage)
- tema claro, cards com cor própria por categoria
- histórico de edições anteriores, navegável
- navegação entre as diferentes abas/sites do projeto
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import OrderedDict

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"

# Os dois "sites" do projeto. Cada um é publicado em sua própria pasta dentro
# de docs/, com seu próprio index.html e histórico — completamente
# independentes um do outro, exceto pelo link de navegação cruzada.
SITE_BOLETIM = {"docs_dir": DOCS_ROOT, "nome": "Boletim de IA", "emoji": "📡"}
SITE_PRODUTOS = {"docs_dir": DOCS_ROOT / "produtos", "nome": "Aplicações de IA por Setor", "emoji": "🏭"}

MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# Paleta por categoria (cor de destaque, fundo do selo, texto do selo).
# Compartilhada entre os dois sites — categorias não listadas aqui caem no
# CICLO_FALLBACK, na ordem em que aparecem.
CORES_CATEGORIA = {
    "Labs & Modelos":          {"cor": "#E08D2D", "selo_bg": "#FDEEDC", "selo_texto": "#8A4B12"},
    "Mercado & Negócios":      {"cor": "#1D9E75", "selo_bg": "#DFF5F0", "selo_texto": "#0F6E56"},
    "Pesquisa & Tendências":   {"cor": "#7F77DD", "selo_bg": "#EDEAFB", "selo_texto": "#3C3489"},
    "Comunidade & Devs":       {"cor": "#D4537E", "selo_bg": "#FBE9EF", "selo_texto": "#8A2A50"},
    "Empresas de Tecnologia":  {"cor": "#5A7CB0", "selo_bg": "#E9EEF7", "selo_texto": "#33456B"},
    "Saúde":                   {"cor": "#2FA65A", "selo_bg": "#DFF5E5", "selo_texto": "#1A6B3B"},
    "Financeiro":              {"cor": "#3B6FD4", "selo_bg": "#E4ECFC", "selo_texto": "#244A99"},
    "Energia":                 {"cor": "#C99A1E", "selo_bg": "#FBF1D6", "selo_texto": "#7A5E10"},
}
CICLO_FALLBACK = [
    {"cor": "#B0805A", "selo_bg": "#F7EEE7", "selo_texto": "#6B4A2E"},
    {"cor": "#5AAFB0", "selo_bg": "#E3F4F4", "selo_texto": "#2E6B6B"},
]


def _data_extenso_pt(dt: datetime) -> str:
    return f"{dt.day} de {MESES_PT[dt.month - 1]} de {dt.year}"


def _link_relativo(de_arquivo: Path, para_arquivo: Path) -> str:
    """Caminho relativo de um arquivo HTML gerado até outro, para uso em
    href — funciona automaticamente independente de quantos níveis de pasta
    cada site está (docs/, docs/arquivo/, docs/produtos/, docs/produtos/arquivo/)."""
    return os.path.relpath(para_arquivo, start=de_arquivo.parent).replace(os.sep, "/")


def _cor_para_categoria(categoria: str, mapa_fallback: dict) -> dict:
    if categoria in CORES_CATEGORIA:
        return CORES_CATEGORIA[categoria]
    if categoria not in mapa_fallback:
        indice = len(mapa_fallback) % len(CICLO_FALLBACK)
        mapa_fallback[categoria] = CICLO_FALLBACK[indice]
    return mapa_fallback[categoria]


def _preparar_artigos_para_js(artigos: list) -> list:
    mapa_fallback = {}
    preparados = []

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


def _categorias_para_js(artigos_preparados: list) -> list:
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
<title>__NOME_SITE__ — __EDICAO__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
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
  .tabs-site {
    display: flex;
    gap: 8px;
    padding: 20px 0 0;
  }
  .tabs-site .tab {
    font-size: 13px;
    font-weight: 500;
    padding: 7px 14px;
    border-radius: 999px;
    text-decoration: none;
    color: var(--text-secondary);
    background: #EDEFF6;
  }
  .tabs-site .tab.ativo {
    background: var(--accent);
    color: #fff;
    font-weight: 600;
  }
  .tabs-site a.tab:hover { background: #E3E6F1; }
  header {
    padding: 28px 0 28px;
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
    margin: 8px 0 0;
    font-size: 14.5px;
    font-weight: 500;
    position: relative;
    z-index: 1;
  }
  .link-arquivo {
    color: var(--accent);
    text-decoration: none;
  }
  .link-arquivo:hover { text-decoration: underline; }
  .banner-arquivo {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px 14px;
    background: var(--accent-bg);
    color: var(--accent);
    border-radius: 12px;
    padding: 12px 18px;
    font-size: 13.5px;
    font-weight: 500;
    margin: 16px 0 -4px;
  }
  .banner-arquivo a {
    color: var(--accent);
    font-weight: 600;
    text-decoration: none;
  }
  .banner-arquivo a:hover { text-decoration: underline; }
  .banner-arquivo .separador { color: var(--border-strong); }
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
    font-size: 13px;
    font-weight: 500;
    padding: 7px 14px;
    border-radius: 999px;
    border: 1px solid transparent;
    background: #EDEFF6;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: background-color 0.15s ease, color 0.15s ease;
  }
  .chip:hover { background: #E3E6F1; }
  .chip .ponto {
    width: 7px; height: 7px; border-radius: 50%;
    display: inline-block;
  }
  .chip.ativo {
    background: var(--accent);
    color: #fff;
    font-weight: 600;
  }
  .chip.favoritos-chip.ativo {
    background: var(--favorito);
    color: #fff;
  }
  .contador {
    margin-top: 16px;
    font-size: 13px;
    font-weight: 500;
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
    border-radius: 14px;
    padding: 20px 22px;
    position: relative;
    box-shadow: 0 1px 2px rgba(27,35,64,0.04), 0 4px 16px rgba(27,35,64,0.03);
    transition: box-shadow 0.15s ease;
  }
  .card:hover {
    box-shadow: 0 2px 6px rgba(27,35,64,0.06), 0 8px 24px rgba(27,35,64,0.05);
  }
  .card-topo {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
  }
  .card-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--text-muted);
    flex-wrap: wrap;
  }
  .selo {
    font-size: 11.5px;
    font-weight: 600;
    padding: 4px 11px;
    border-radius: 999px;
    letter-spacing: 0.01em;
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
    font-size: 13px;
  }
  @media (max-width: 480px) {
    header h1 { font-size: 23px; }
    .card { padding: 15px 16px; }
  }
</style>
</head>
<body>
  <div class="envelope">
    <nav class="tabs-site">
      <span class="tab ativo">__EMOJI_SITE__ __NOME_SITE__</span>
      <a class="tab" href="__LINK_OUTRO_SITE__">__EMOJI_OUTRO_SITE__ __NOME_OUTRO_SITE__</a>
    </nav>
    __BANNER_ARQUIVO__
    <header>
      <div class="radar-fundo"></div>
      <div class="titulo-linha">
        <div class="radar-icone"></div>
        <h1>__NOME_SITE__</h1>
      </div>
      <p class="subtitulo">edição de __EDICAO__ · __TOTAL__ notícias captadas · <a class="link-arquivo" href="__LINK_ARQUIVO__">ver edições anteriores</a></p>

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
    const CHAVE_FAVORITOS = 'ai-digest-favoritos-__CHAVE_SITE__';

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
        <h3>${a.link && a.link.startsWith('http') ? `<a href="${escaparHtml(a.link)}" target="_blank" rel="noopener">${escaparHtml(a.titulo)}</a>` : escaparHtml(a.titulo)}</h3>
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


def gerar_html(
    artigos: list,
    modo: str = "atual",
    data_edicao: datetime = None,
    nome_site: str = "Boletim de IA",
    emoji_site: str = "📡",
    link_outro_site: str = "",
    nome_outro_site: str = "",
    emoji_outro_site: str = "",
) -> str:
    agora = data_edicao or datetime.now(timezone.utc)
    artigos_preparados = _preparar_artigos_para_js(artigos)
    categorias = _categorias_para_js(artigos_preparados)

    artigos_json = json.dumps(artigos_preparados, ensure_ascii=False).replace("</", "<\\/")
    categorias_json = json.dumps(categorias, ensure_ascii=False).replace("</", "<\\/")
    chave_site = "".join(c for c in nome_site.lower() if c.isalnum())

    if modo == "arquivo":
        link_arquivo = "index.html"
        banner = (
            f'<div class="banner-arquivo">📚 Esta é uma edição anterior ({_data_extenso_pt(agora)}).'
            f' <a href="index.html">← ver lista de edições</a>'
            f' <span class="separador">·</span>'
            f' <a href="../index.html">ver a mais recente →</a></div>'
        )
    else:
        link_arquivo = "arquivo/index.html"
        banner = ""

    html = TEMPLATE_HTML
    html = html.replace("__EDICAO__", _data_extenso_pt(agora))
    html = html.replace("__TOTAL__", str(len(artigos)))
    html = html.replace("__ARTIGOS_JSON__", artigos_json)
    html = html.replace("__CATEGORIAS_JSON__", categorias_json)
    html = html.replace("__LINK_ARQUIVO__", link_arquivo)
    html = html.replace("__BANNER_ARQUIVO__", banner)
    html = html.replace("__NOME_SITE__", nome_site)
    html = html.replace("__EMOJI_SITE__", emoji_site)
    html = html.replace("__LINK_OUTRO_SITE__", link_outro_site)
    html = html.replace("__NOME_OUTRO_SITE__", nome_outro_site)
    html = html.replace("__EMOJI_OUTRO_SITE__", emoji_outro_site)
    html = html.replace("__CHAVE_SITE__", chave_site)
    return html


def _listar_edicoes_anteriores(arquivo_dir: Path) -> list:
    if not arquivo_dir.exists():
        return []

    edicoes = []
    for arq in sorted(arquivo_dir.glob("*.html"), reverse=True):
        if arq.name == "index.html":
            continue
        try:
            data = datetime.strptime(arq.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            data_fmt = _data_extenso_pt(data)
        except ValueError:
            data_fmt = arq.stem
        edicoes.append({"arquivo": arq.name, "data": data_fmt})
    return edicoes


TEMPLATE_INDICE_ARQUIVO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Edições anteriores — __NOME_SITE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #F4F6FB;
    --card-bg: #FFFFFF;
    --text: #1B2340;
    --text-muted: #848DA6;
    --text-secondary: #4B5470;
    --border: #E1E5F0;
    --accent: #5A4FCF;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.55;
  }
  .envelope { max-width: 640px; margin: 0 auto; padding: 20px 24px 80px; }
  .tabs-site {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
  }
  .tabs-site .tab {
    font-size: 13px;
    font-weight: 500;
    padding: 7px 14px;
    border-radius: 999px;
    text-decoration: none;
    color: var(--text-secondary);
    background: #EDEFF6;
  }
  .tabs-site .tab.ativo {
    background: var(--accent);
    color: #fff;
    font-weight: 600;
  }
  .tabs-site a.tab:hover { background: #E3E6F1; }
  a.voltar {
    color: var(--accent);
    text-decoration: none;
    font-size: 13.5px;
    font-weight: 500;
  }
  a.voltar:hover { text-decoration: underline; }
  h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 26px;
    font-weight: 600;
    margin: 20px 0 4px;
  }
  p.subtitulo { color: var(--text-muted); margin: 0 0 28px; font-size: 14.5px; }
  ul.lista-edicoes { list-style: none; padding: 0; margin: 0; }
  ul.lista-edicoes li {
    border: 1px solid var(--border);
    background: var(--card-bg);
    border-radius: 12px;
    margin-bottom: 10px;
    box-shadow: 0 1px 2px rgba(27,35,64,0.04);
    transition: box-shadow 0.15s ease;
  }
  ul.lista-edicoes li:hover {
    box-shadow: 0 4px 16px rgba(27,35,64,0.06);
  }
  ul.lista-edicoes a {
    display: block;
    padding: 15px 18px;
    color: var(--text);
    text-decoration: none;
    font-size: 15px;
    font-weight: 500;
  }
  ul.lista-edicoes a:hover { color: var(--accent); }
  .vazio { color: var(--text-muted); margin-top: 20px; }
</style>
</head>
<body>
  <div class="envelope">
    <nav class="tabs-site">
      <span class="tab ativo">__EMOJI_SITE__ __NOME_SITE__</span>
      <a class="tab" href="__LINK_OUTRO_SITE__">__EMOJI_OUTRO_SITE__ __NOME_OUTRO_SITE__</a>
    </nav>
    <a class="voltar" href="../index.html">&larr; voltar para a edição mais recente</a>
    <h1>📚 Edições anteriores</h1>
    <p class="subtitulo">Todo o histórico do __NOME_SITE__, uma edição por semana.</p>
    __LISTA_EDICOES__
  </div>
</body>
</html>
"""


def _gerar_indice_arquivo(
    arquivo_dir: Path, nome_site: str, link_outro_site: str, nome_outro_site: str, emoji_outro_site: str, emoji_site: str
) -> str:
    edicoes = _listar_edicoes_anteriores(arquivo_dir)

    if not edicoes:
        lista_html = '<p class="vazio">Nenhuma edição anterior ainda.</p>'
    else:
        itens = "\n".join(
            f'      <li><a href="{e["arquivo"]}">{e["data"]}</a></li>' for e in edicoes
        )
        lista_html = f'<ul class="lista-edicoes">\n{itens}\n    </ul>'

    html = TEMPLATE_INDICE_ARQUIVO.replace("__LISTA_EDICOES__", lista_html)
    html = html.replace("__NOME_SITE__", nome_site)
    html = html.replace("__EMOJI_SITE__", emoji_site)
    html = html.replace("__LINK_OUTRO_SITE__", link_outro_site)
    html = html.replace("__NOME_OUTRO_SITE__", nome_outro_site)
    html = html.replace("__EMOJI_OUTRO_SITE__", emoji_outro_site)
    return html


def publicar(artigos: list, site: dict = None, outro_site: dict = None):
    """site e outro_site são dicts com 'docs_dir' (Path), 'nome' (str) e
    'emoji' (str) — veja SITE_BOLETIM e SITE_PRODUTOS no topo do arquivo."""
    site = site or SITE_BOLETIM
    outro_site = outro_site or SITE_PRODUTOS

    docs_dir = site["docs_dir"]
    arquivo_dir = docs_dir / "arquivo"
    docs_dir.mkdir(parents=True, exist_ok=True)
    arquivo_dir.mkdir(parents=True, exist_ok=True)

    outro_index = outro_site["docs_dir"] / "index.html"

    agora = datetime.now(timezone.utc)

    # edição atual (link fixo, sempre a mais recente)
    caminho_atual = docs_dir / "index.html"
    link_outro_atual = _link_relativo(caminho_atual, outro_index)
    html_atual = gerar_html(
        artigos, modo="atual", data_edicao=agora,
        nome_site=site["nome"], emoji_site=site["emoji"],
        link_outro_site=link_outro_atual, nome_outro_site=outro_site["nome"], emoji_outro_site=outro_site["emoji"],
    )
    caminho_atual.write_text(html_atual, encoding="utf-8")

    # cópia no histórico
    nome_arquivo = agora.strftime("%Y-%m-%d") + ".html"
    caminho_arquivo_datado = arquivo_dir / nome_arquivo
    link_outro_arquivo = _link_relativo(caminho_arquivo_datado, outro_index)
    html_arquivo = gerar_html(
        artigos, modo="arquivo", data_edicao=agora,
        nome_site=site["nome"], emoji_site=site["emoji"],
        link_outro_site=link_outro_arquivo, nome_outro_site=outro_site["nome"], emoji_outro_site=outro_site["emoji"],
    )
    caminho_arquivo_datado.write_text(html_arquivo, encoding="utf-8")

    # índice com a lista de todas as edições
    caminho_indice = arquivo_dir / "index.html"
    link_outro_indice = _link_relativo(caminho_indice, outro_index)
    indice_html = _gerar_indice_arquivo(
        arquivo_dir, site["nome"], link_outro_indice, outro_site["nome"], outro_site["emoji"], site["emoji"]
    )
    caminho_indice.write_text(indice_html, encoding="utf-8")


if __name__ == "__main__":
    from fetch import buscar_noticias
    from summarize import processar_lista

    noticias = buscar_noticias()
    processadas = processar_lista(noticias)
    publicar(processadas, site=SITE_BOLETIM, outro_site=SITE_PRODUTOS)
    print(f"Dashboard gerado em: {SITE_BOLETIM['docs_dir'] / 'index.html'}")
