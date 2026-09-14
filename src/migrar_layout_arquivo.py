"""
Script de manutenção (rode uma única vez, localmente, sempre que o template
do dashboard mudar de forma visual) para atualizar edições já arquivadas
para o layout mais recente — sem precisar chamar a API da Claude de novo.

Funciona extraindo os dados de notícias já embutidos em cada página antiga
(no bloco <script id="dados-artigos">) e regerando o HTML com o gerar_html()
atual.

Uso:
    cd src
    python migrar_layout_arquivo.py              # migra o boletim geral
    python migrar_layout_arquivo.py produtos      # migra a aba de produtos
    python migrar_layout_arquivo.py todos         # migra os dois

Observação: edições geradas ANTES da versão com busca/filtro (totalmente
estáticas, sem JavaScript) não têm esse bloco de dados embutido e não podem
ser migradas automaticamente — o script avisa e pula esses arquivos.
"""

import re
import sys
import json
from datetime import datetime, timezone

from generate_html import (
    SITE_BOLETIM,
    SITE_PRODUTOS,
    gerar_html,
    _gerar_indice_arquivo,
    _link_relativo,
)

PADRAO_JSON = re.compile(
    r'<script id="dados-artigos" type="application/json">(.*?)</script>', re.DOTALL
)


def _converter_para_artigo(item: dict) -> dict:
    data_publicacao = None
    if item.get("data"):
        try:
            data_publicacao = datetime.strptime(item["data"], "%d/%m/%Y").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            data_publicacao = None

    return {
        "titulo_pt": item.get("titulo", ""),
        "resumo_pt": item.get("resumo", ""),
        "por_que_importa": item.get("por_que_importa", ""),
        "link": item.get("link", ""),
        "fonte": item.get("fonte", ""),
        "categoria": item.get("categoria", "Outros"),
        "data_publicacao": data_publicacao,
    }


def migrar_site(site: dict, outro_site: dict):
    docs_dir = site["docs_dir"]
    arquivo_dir = docs_dir / "arquivo"

    print(f"\n=== {site['nome']} ({docs_dir}) ===")

    if not arquivo_dir.exists():
        print("Pasta de arquivo não encontrada. Nada para migrar.")
        return

    outro_index = outro_site["docs_dir"] / "index.html"
    arquivos = sorted(arquivo_dir.glob("*.html"))
    migrados, pulados = 0, 0

    for arquivo in arquivos:
        if arquivo.name == "index.html":
            continue

        texto = arquivo.read_text(encoding="utf-8")
        match = PADRAO_JSON.search(texto)

        if not match:
            print(f"[pulado] {arquivo.name}: não tem dados embutidos (versão muito antiga)")
            pulados += 1
            continue

        try:
            itens = json.loads(match.group(1))
        except json.JSONDecodeError:
            print(f"[pulado] {arquivo.name}: dados embutidos não puderam ser lidos")
            pulados += 1
            continue

        artigos = [_converter_para_artigo(item) for item in itens]

        try:
            data_edicao = datetime.strptime(arquivo.stem, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            data_edicao = datetime.now(timezone.utc)

        link_outro = _link_relativo(arquivo, outro_index)
        html_novo = gerar_html(
            artigos, modo="arquivo", data_edicao=data_edicao,
            nome_site=site["nome"], emoji_site=site["emoji"],
            link_outro_site=link_outro, nome_outro_site=outro_site["nome"], emoji_outro_site=outro_site["emoji"],
        )
        arquivo.write_text(html_novo, encoding="utf-8")
        print(f"[migrado] {arquivo.name}: {len(artigos)} notícias")
        migrados += 1

    caminho_indice = arquivo_dir / "index.html"
    link_outro_indice = _link_relativo(caminho_indice, outro_index)
    indice_html = _gerar_indice_arquivo(
        arquivo_dir, site["nome"], link_outro_indice, outro_site["nome"], outro_site["emoji"], site["emoji"]
    )
    caminho_indice.write_text(indice_html, encoding="utf-8")

    print(f"Concluído: {migrados} edição(ões) migrada(s), {pulados} pulada(s).")


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "boletim"

    if alvo == "todos":
        migrar_site(SITE_BOLETIM, SITE_PRODUTOS)
        migrar_site(SITE_PRODUTOS, SITE_BOLETIM)
    elif alvo == "produtos":
        migrar_site(SITE_PRODUTOS, SITE_BOLETIM)
    else:
        migrar_site(SITE_BOLETIM, SITE_PRODUTOS)
