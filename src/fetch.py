"""
Busca notícias de IA a partir dos feeds RSS configurados em config/sources.yaml.
Filtra por janela de tempo e palavras-chave, e devolve uma lista de artigos crus
(ainda em inglês/original) prontos para serem resumidos e traduzidos.
"""

import time
import re
import yaml
import feedparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"

# Padrão de metadado do Hacker News (sem conteúdo real), ex:
# "Article URL: ... Comments URL: ... Points: 137  # Comments: 89"
_PADRAO_METADADO_HN = re.compile(r"(?i)points\s*:\s*\d+")
_PADRAO_URL_HN = re.compile(r"(?i)(article url|comments url)\s*:")


def _tem_conteudo_substancial(resumo_original: str) -> bool:
    """Verifica se o resumo original tem texto para resumir. Só descarta em
    dois casos bem específicos: resumo vazio, ou o padrão de metadado típico
    do Hacker News (sem o conteúdo real do artigo). Resumos curtos porém
    legítimos de outras fontes (comuns em vários blogs) NÃO são descartados."""
    texto = resumo_original.strip()
    if not texto:
        return False

    texto_sem_url = re.sub(r"https?://\S+", "", texto).strip()

    eh_metadado_hn = bool(_PADRAO_METADADO_HN.search(texto_sem_url)) and bool(
        _PADRAO_URL_HN.search(texto_sem_url)
    )
    if eh_metadado_hn:
        return False

    palavras = [p for p in re.split(r"\s+", texto_sem_url) if p]
    return len(palavras) >= 3


def carregar_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _entry_para_dict(entry, fonte, categoria):
    # feedparser normaliza datas em 'published_parsed' (struct_time) quando disponível
    data_publicacao = None
    if getattr(entry, "published_parsed", None):
        data_publicacao = datetime.fromtimestamp(
            time.mktime(entry.published_parsed), tz=timezone.utc
        )

    resumo_original = getattr(entry, "summary", "") or getattr(entry, "description", "")

    link = getattr(entry, "link", "") or ""
    if not link.startswith("http"):
        # fallback: alguns feeds trazem o link em 'id' quando 'link' vem vazio/malformado
        candidato = getattr(entry, "id", "") or ""
        if candidato.startswith("http"):
            link = candidato

    return {
        "titulo_original": getattr(entry, "title", "(sem título)"),
        "link": link,
        "resumo_original": resumo_original,
        "data_publicacao": data_publicacao,
        "fonte": fonte,
        "categoria": categoria,
    }


def _e_relevante(item, palavras_chave):
    texto = f"{item['titulo_original']} {item['resumo_original']}".lower()
    return any(palavra.lower() in texto for palavra in palavras_chave)


def buscar_noticias():
    config = carregar_config()
    janela = timedelta(days=config.get("janela_dias", 7))
    limite_data = datetime.now(timezone.utc) - janela
    palavras_chave = config.get("palavras_chave", [])

    artigos = []

    for feed_cfg in config["feeds"]:
        nome = feed_cfg["nome"]
        url = feed_cfg["url"]
        categoria = feed_cfg["categoria"]

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[aviso] falha ao buscar feed '{nome}': {e}")
            continue

        for entry in feed.entries:
            item = _entry_para_dict(entry, nome, categoria)

            # Se não há data, mantemos o item (alguns feeds não populam a data)
            if item["data_publicacao"] and item["data_publicacao"] < limite_data:
                continue

            if not _e_relevante(item, palavras_chave):
                continue

            if not _tem_conteudo_substancial(item["resumo_original"]):
                continue

            artigos.append(item)

    # Remove duplicados por link
    vistos = set()
    unicos = []
    for a in artigos:
        if a["link"] not in vistos:
            vistos.add(a["link"])
            unicos.append(a)

    # Mais recentes primeiro
    unicos.sort(
        key=lambda a: a["data_publicacao"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    max_noticias = config.get("max_noticias", 15)
    return unicos[:max_noticias]


if __name__ == "__main__":
    noticias = buscar_noticias()
    print(f"Encontradas {len(noticias)} notícias relevantes.")
    for n in noticias[:5]:
        print(f"- [{n['categoria']}] {n['titulo_original']} ({n['fonte']})")
