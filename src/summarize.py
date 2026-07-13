"""
Usa a API da Claude para resumir e traduzir cada notícia para PT-BR.
Cada artigo vira um resumo curto, objetivo, com foco em "o que isso significa
na prática" — pensado para leitura rápida em um boletim semanal.
"""

import os
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

Responda SOMENTE em JSON válido, sem markdown, sem texto antes ou depois, no formato:
{"titulo_pt": "...", "resumo_pt": "...", "por_que_importa": "..."}
"""


def resumir_e_traduzir(artigo: dict) -> dict:
    conteudo_usuario = (
        f"Título original: {artigo['titulo_original']}\n"
        f"Fonte: {artigo['fonte']}\n"
        f"Resumo original: {artigo['resumo_original'][:1500]}"
    )

    resposta = client.messages.create(
        model=MODELO,
        max_tokens=500,
        system=PROMPT_SISTEMA,
        messages=[{"role": "user", "content": conteudo_usuario}],
    )

    texto = "".join(
        bloco.text for bloco in resposta.content if getattr(bloco, "type", None) == "text"
    )

    try:
        dados = json.loads(texto.strip())
    except json.JSONDecodeError:
        # fallback defensivo caso o modelo devolva algo fora do formato esperado
        dados = {
            "titulo_pt": artigo["titulo_original"],
            "resumo_pt": "Não foi possível gerar o resumo automaticamente para este item.",
            "por_que_importa": "",
        }

    artigo_traduzido = {**artigo, **dados}
    return artigo_traduzido


def processar_lista(artigos: list[dict]) -> list[dict]:
    processados = []
    for artigo in artigos:
        try:
            processados.append(resumir_e_traduzir(artigo))
        except Exception as e:
            print(f"[aviso] falha ao processar '{artigo['titulo_original']}': {e}")
    return processados


if __name__ == "__main__":
    from fetch import buscar_noticias

    noticias = buscar_noticias()
    processadas = processar_lista(noticias)
    for n in processadas[:3]:
        print(json.dumps(n, ensure_ascii=False, indent=2, default=str))
