"""
Orquestra o pipeline completo:
  1. Busca notícias de IA da última semana (fetch.py)
  2. Resume e traduz cada uma para PT-BR usando a API da Claude (summarize.py)
  3. Gera e publica o dashboard HTML (generate_html.py)

Uso:
    python src/main.py
Requer a variável de ambiente ANTHROPIC_API_KEY configurada.
"""

import sys
from fetch import buscar_noticias
from summarize import processar_lista
from generate_html import publicar


def main():
    print("Buscando notícias...")
    noticias = buscar_noticias()
    print(f"  {len(noticias)} notícias relevantes encontradas.")

    if not noticias:
        print("Nenhuma notícia encontrada nesta semana. Encerrando sem publicar.")
        sys.exit(0)

    print("Resumindo e traduzindo com a API da Claude...")
    processadas = processar_lista(noticias)
    print(f"  {len(processadas)} notícias processadas com sucesso.")

    print("Gerando e publicando o dashboard...")
    publicar(processadas)
    print("Concluído. Veja docs/index.html")


if __name__ == "__main__":
    main()
