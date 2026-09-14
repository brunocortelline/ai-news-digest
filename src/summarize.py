"""
Usa a API da Claude para resumir e traduzir cada notícia para PT-BR.
Cada artigo vira um resumo curto, objetivo, com foco em "o que isso significa
na prática" — pensado para leitura rápida em um boletim semanal.
"""

import os
import re
import json
import anthropic

MODELO = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente

PROMPT_SISTEMA = """Você é um analista de tecnologia especializado em Inteligência Artificial,
escrevendo para um executivo de produtos e inovação de uma empresa brasileira de TI.

Para cada notícia recebida (título e resumo original, possivelmente em inglês), gere:
1. Um título traduzido e adaptado para PT-BR (natural, não literal), de até 12 palavras.
2. Um resumo em PT-BR de 2 a 3 frases, direto ao ponto, explicando o que aconteceu.
3. Uma frase curta de "por que importa" (relevância prática/estratégica), focada em
   possíveis implicações para produtos, inovação ou negócios — não genérica.

IMPORTANTE: às vezes o "resumo original" recebido é só metadado (ex: link do artigo,
número de pontos/comentários no Hacker News), sem o conteúdo real do texto. Nesses casos,
NUNCA se recuse e NUNCA explique a limitação — gere o melhor resumo possível baseado
apenas no título, de forma honesta e direta. Sempre produza os três campos, mesmo que
de forma mais genérica.

Responda SEMPRE e SOMENTE em JSON válido, sem markdown, sem crases, sem texto antes ou
depois, exatamente neste formato:
{"titulo_pt": "...", "resumo_pt": "...", "por_que_importa": "..."}
"""

LEMBRETE_FORMATO = (
    "Lembrete: responda SOMENTE com o objeto JSON, nada de texto antes ou depois, "
    "nada de explicações sobre limitações. Só o JSON."
)


def _extrair_json(texto: str):
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _chamar_modelo(conteudo_usuario: str, reforcar_formato: bool = False) -> str:
    mensagens = [{"role": "user", "content": conteudo_usuario}]
    if reforcar_formato:
        mensagens.append({"role": "assistant", "content": "{"})

    resposta = client.messages.create(
        model=MODELO,
        max_tokens=500,
        system=PROMPT_SISTEMA,
        messages=mensagens,
    )

    texto = "".join(
        bloco.text for bloco in resposta.content if getattr(bloco, "type", None) == "text"
    )

    if reforcar_formato:
        texto = "{" + texto

    return texto


def resumir_e_traduzir(artigo: dict):
    conteudo_usuario = (
        f"Título original: {artigo['titulo_original']}\n"
        f"Fonte: {artigo['fonte']}\n"
        f"Resumo original: {artigo['resumo_original'][:1500]}\n\n"
        f"{LEMBRETE_FORMATO}"
    )

    texto = _chamar_modelo(conteudo_usuario)
    dados = _extrair_json(texto)

    if dados is None:
        texto_retry = _chamar_modelo(conteudo_usuario, reforcar_formato=True)
        dados = _extrair_json(texto_retry)

    if dados is None:
        print(f"[aviso] descartando item sem resumo confiável: '{artigo['titulo_original']}'")
        return None

    artigo_traduzido = {**artigo, **dados}
    return artigo_traduzido


def processar_lista(artigos: list) -> list:
    processados = []
    for artigo in artigos:
        try:
            resultado = resumir_e_traduzir(artigo)
            if resultado is not None:
                processados.append(resultado)
        except Exception as e:
            print(f"[aviso] falha ao processar '{artigo['titulo_original']}': {e}")
    return processados


if __name__ == "__main__":
    from fetch import buscar_noticias

    noticias = buscar_noticias()
    processadas = processar_lista(noticias)
    for n in processadas[:3]:
        print(json.dumps(n, ensure_ascii=False, indent=2, default=str))
