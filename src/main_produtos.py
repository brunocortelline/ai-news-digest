"""
Orquestra o pipeline completo da aba "Aplicações de IA por Setor":
  1. Busca notícias da última semana (config/sources_produtos.yaml)
  2. Resume e traduz cada uma para PT-BR usando a API da Claude
  3. Gera e publica o dashboard HTML em docs/produtos/

Uso:
    python src/main_produtos.py
Requer a variável de ambiente ANTHROPIC_API_KEY configurada.
"""

import sys
from pathlib import Path

from fetch import buscar_noticias
from summarize import processar_lista
from generate_html import publicar, SITE_BOLETIM, SITE_PRODUTOS

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources_produtos.yaml"


def main():
    print("[Aplicações de IA por Setor] Buscando notícias...")
    noticias = buscar_noticias(config_path=CONFIG_PATH)
    print(f"  {len(noticias)} notícias relevantes encontradas.")

    if not noticias:
        print("Nenhuma notícia encontrada nesta semana. Encerrando sem publicar.")
        sys.exit(0)

    print("Resumindo e traduzindo com a API da Claude...")
    processadas = processar_lista(noticias)
    print(f"  {len(processadas)} notícias processadas com sucesso.")

    print("Gerando e publicando o dashboard...")
    publicar(processadas, site=SITE_PRODUTOS, outro_site=SITE_BOLETIM)
    print(f"Concluído. Veja {SITE_PRODUTOS['docs_dir']}/index.html")


if __name__ == "__main__":
    main()
