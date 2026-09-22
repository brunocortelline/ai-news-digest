"""
Busca notícias a partir dos feeds RSS configurados em um arquivo YAML (por
padrão, config/sources.yaml — o boletim geral de IA; mas aceita qualquer
outro config, como config/sources_produtos.yaml, para a aba de produtos).
Filtra por janela de tempo, palavras-chave e conteúdo substancial, e seleciona
um conjunto final balanceado entre fontes, priorizando temas configurados
quando uma fonte tem mais itens do que o teto permite.
"""

import time
import re
import json
import yaml
import feedparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONFIG_PATH_PADRAO = Path(__file__).parent.parent / "config" / "sources.yaml"

# Arquivo temporário (não versionado) usado para evitar que a mesma notícia
# apareça duplicada nas duas abas do projeto. A aba que roda primeiro (o
# boletim geral, no workflow) salva aqui os links que usou; a aba seguinte
# (produtos) lê esse arquivo e exclui esses links da própria seleção.
CACHE_DIR = Path(__file__).parent.parent / ".cache"
LINKS_USADOS_CACHE = CACHE_DIR / "links_usados_semana.json"


def salvar_links_usados(artigos: list, caminho: Path = LINKS_USADOS_CACHE) -> None:
    """Salva os links dos artigos selecionados por uma aba, para que a
    próxima aba a rodar possa excluí-los da própria seleção."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    links = [a["link"] for a in artigos if a.get("link")]
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(links, f)


def carregar_links_usados(caminho: Path = LINKS_USADOS_CACHE) -> set:
    """Carrega os links já usados por uma aba anterior nesta mesma execução.
    Se o arquivo não existir (ex: rodando só esta aba isoladamente, sem ter
    rodado a outra antes), simplesmente não exclui nada."""
    if not caminho.exists():
        return set()
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()

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


def _pontuacao_prioridade(item: dict, palavras_prioridade: list) -> int:
    """Quanto maior, mais prioridade a notícia tem quando uma fonte precisa
    ser cortada (mais itens do que o teto permite). Conta quantas palavras-
    chave de prioridade aparecem no título ou resumo — não é só sim/não,
    para desempatar entre vários itens igualmente "relevantes"."""
    texto = f"{item['titulo_original']} {item['resumo_original']}".lower()
    return sum(1 for palavra in palavras_prioridade if palavra.lower() in texto)


def carregar_config(config_path: Path = None) -> dict:
    caminho = config_path or CONFIG_PATH_PADRAO
    with open(caminho, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _entry_para_dict(entry, fonte, categoria):
    data_publicacao = None
    if getattr(entry, "published_parsed", None):
        data_publicacao = datetime.fromtimestamp(
            time.mktime(entry.published_parsed), tz=timezone.utc
        )

    resumo_original = getattr(entry, "summary", "") or getattr(entry, "description", "")

    link = getattr(entry, "link", "") or ""
    if not link.startswith("http"):
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
    for palavra in palavras_chave:
        p = palavra.lower()
        if " " in p:
            # frase com mais de uma palavra: substring simples já é seguro
            # (ex: "inteligência artificial", "machine learning")
            if p in texto:
                return True
        else:
            # palavra única/sigla: precisa de borda de palavra, senão "AI"
            # daria match em "air fryer", "praia" etc, e "IA" em "companhia"
            if re.search(rf"\b{re.escape(p)}\b", texto):
                return True
    return False


def buscar_noticias(config_path: Path = None, links_excluir: set = None) -> list:
    config = carregar_config(config_path)
    janela = timedelta(days=config.get("janela_dias", 7))
    limite_data = datetime.now(timezone.utc) - janela
    palavras_chave = config.get("palavras_chave", [])
    links_excluir = links_excluir or set()

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

    # Remove links já usados por outra aba nesta mesma execução (evita a
    # mesma notícia aparecer duplicada no boletim geral e na aba de produtos).
    # Se sobrar menos notícias do que o teto de max_noticias, tudo bem —
    # é melhor publicar com menos do que repetir conteúdo.
    if links_excluir:
        unicos = [a for a in unicos if a["link"] not in links_excluir]

    unicos.sort(
        key=lambda a: a["data_publicacao"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    max_noticias = config.get("max_noticias", 25)
    max_por_fonte = config.get("max_por_fonte", 3)
    palavras_prioridade = config.get("palavras_chave_prioridade", [])

    return _selecionar_balanceado(unicos, max_noticias, max_por_fonte, palavras_prioridade)


def _selecionar_balanceado(
    artigos: list, max_noticias: int, max_por_fonte: int, palavras_prioridade: list = None
) -> list:
    """Seleciona notícias garantindo diversidade de fontes: em vez de pegar
    só as N mais recentes no total (o que deixa fontes de alto volume
    dominarem a lista), distribui em rodadas — uma notícia de cada fonte por
    vez — respeitando um teto por fonte.

    Quando uma fonte tem mais itens do que o teto permite, os itens dessa
    fonte são ordenados por prioridade (temas configurados em
    'palavras_chave_prioridade') antes de aplicar o corte — ou seja, entre
    vários itens da mesma fonte, os mais alinhados a esses temas têm
    preferência, não só os mais recentes."""
    palavras_prioridade = palavras_prioridade or []

    por_fonte: dict = {}
    for artigo in artigos:
        por_fonte.setdefault(artigo["fonte"], []).append(artigo)

    for fonte, itens in por_fonte.items():
        itens.sort(
            key=lambda a: (
                -_pontuacao_prioridade(a, palavras_prioridade),
                -(a["data_publicacao"] or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
            )
        )

    selecionados = []
    indice_por_fonte = {fonte: 0 for fonte in por_fonte}

    while len(selecionados) < max_noticias:
        adicionou_algo = False
        for fonte, itens in por_fonte.items():
            if len(selecionados) >= max_noticias:
                break
            i = indice_por_fonte[fonte]
            if i >= min(len(itens), max_por_fonte):
                continue
            selecionados.append(itens[i])
            indice_por_fonte[fonte] += 1
            adicionou_algo = True
        if not adicionou_algo:
            break

    selecionados.sort(
        key=lambda a: a["data_publicacao"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return selecionados


if __name__ == "__main__":
    noticias = buscar_noticias()
    print(f"Encontradas {len(noticias)} notícias relevantes.")
    for n in noticias[:5]:
        print(f"- [{n['categoria']}] {n['titulo_original']} ({n['fonte']})")
