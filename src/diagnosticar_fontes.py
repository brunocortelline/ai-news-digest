"""
Ferramenta de diagnóstico: testa cada feed RSS individualmente e mostra
quantas notícias cada um está trazendo, em cada etapa do filtro.

Uso:
    cd src
    python diagnosticar_fontes.py                  # testa o boletim geral
    python diagnosticar_fontes.py produtos          # testa a aba de produtos
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import feedparser

from fetch import carregar_config, _entry_para_dict, _e_relevante, _tem_conteudo_substancial

CONFIG_BOLETIM = Path(__file__).parent.parent / "config" / "sources.yaml"
CONFIG_PRODUTOS = Path(__file__).parent.parent / "config" / "sources_produtos.yaml"


def diagnosticar(config_path: Path):
    config = carregar_config(config_path)
    janela = timedelta(days=config.get("janela_dias", 7))
    limite_data = datetime.now(timezone.utc) - janela
    palavras_chave = config.get("palavras_chave", [])

    print(f"Config: {config_path.name}")
    print(f"Janela de busca: últimos {config.get('janela_dias', 7)} dias")
    print(f"Testando {len(config['feeds'])} fontes...\n")
    print(f"{'FONTE':<35} {'BRUTO':>7} {'DATA':>7} {'PALAVRA':>9} {'CONTEÚDO':>10}  STATUS")
    print("-" * 90)

    total_final = 0

    for feed_cfg in config["feeds"]:
        nome = feed_cfg["nome"]
        url = feed_cfg["url"]

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"{nome:<35} {'ERRO':>7}  -- falha ao buscar: {e}")
            continue

        bruto = len(feed.entries)

        status = ""
        if getattr(feed, "bozo", False) and bruto == 0:
            status = "⚠ possível URL quebrada ou feed inválido"
        elif bruto == 0:
            status = "⚠ feed respondeu, mas sem itens"

        passou_data = 0
        passou_palavra = 0
        passou_conteudo = 0

        for entry in feed.entries:
            item = _entry_para_dict(entry, nome, feed_cfg["categoria"])

            if item["data_publicacao"] and item["data_publicacao"] < limite_data:
                continue
            passou_data += 1

            if not _e_relevante(item, palavras_chave):
                continue
            passou_palavra += 1

            if not _tem_conteudo_substancial(item["resumo_original"]):
                continue
            passou_conteudo += 1

        total_final += passou_conteudo

        if not status and passou_conteudo == 0 and bruto > 0:
            if passou_data == 0:
                status = "⚠ tinha itens, mas nenhum dentro da janela de dias"
            elif passou_palavra == 0:
                status = "⚠ tinha itens recentes, mas nenhum bateu com as palavras-chave"
            elif passou_conteudo == 0:
                status = "⚠ tinha itens relevantes, mas sem conteúdo suficiente"
        elif not status:
            status = "OK"

        print(f"{nome:<35} {bruto:>7} {passou_data:>7} {passou_palavra:>9} {passou_conteudo:>10}  {status}")

    print("-" * 90)
    print(f"\nTotal de notícias que passariam por todos os filtros: {total_final}")
    print(f"(o boletim final ainda aplica o teto de {config.get('max_noticias', 25)} notícias")
    print(f" e {config.get('max_por_fonte', 3)} no máximo por fonte, priorizando os temas")
    print(f" configurados em 'palavras_chave_prioridade' quando uma fonte tem itens sobrando)")


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "boletim"
    config_path = CONFIG_PRODUTOS if alvo == "produtos" else CONFIG_BOLETIM
    diagnosticar(config_path)
