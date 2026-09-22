"""
Orquestra o pipeline completo do boletim geral de IA:
  1. Busca notícias da última semana (config/sources.yaml)
  2. Resume e traduz cada uma para PT-BR usando a API da Claude
  3. Gera e publica o dashboard HTML em docs/

Uso:
    python src/main.py
Requer a variável de ambiente ANTHROPIC_API_KEY configurada.
"""

import sys
from fetch import buscar_noticias, salvar_links_usados
from summarize import processar_lista
from generate_html import publicar, SITE_BOLETIM, SITE_PRODUTOS


def main():
    print("[Boletim de IA] Buscando notícias...")
    noticias = buscar_noticias()
    print(f"  {len(noticias)} notícias relevantes encontradas.")

    if not noticias:
        print("Nenhuma notícia encontrada nesta semana. Encerrando sem publicar.")
        sys.exit(0)

    print("Resumindo e traduzindo com a API da Claude...")
    processadas = processar_lista(noticias)
    print(f"  {len(processadas)} notícias processadas com sucesso.")

    # Salva os links usados aqui para a aba de produtos (que roda depois)
    # não repetir as mesmas notícias.
    salvar_links_usados(processadas)

    print("Gerando e publicando o dashboard...")
    publicar(processadas, site=SITE_BOLETIM, outro_site=SITE_PRODUTOS)
    print(f"Concluído. Veja {SITE_BOLETIM['docs_dir']}/index.html")


if __name__ == "__main__":
    main()
