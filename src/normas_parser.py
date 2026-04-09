# ==============================================================
# NORMAS PARSER
# ==============================================================
# Extrai textos das normas (PDF) para envio ao LLM
# ==============================================================

import os
import fitz
import re

# ==============================================================
# EXTRAIR TEXTO DAS PRIMEIRAS PÁGINAS
# ==============================================================

def extrair_texto_norma(pdf_path, max_paginas=2):

    try:

        doc = fitz.open(pdf_path)

        texto = ""

        for i in range(min(max_paginas, doc.page_count)):

            page = doc.load_page(i)

            texto += page.get_text()

        doc.close()

        texto = re.sub(r"\s+", " ", texto)

        return texto[:4000]

    except Exception as e:

        print(f"Erro ao ler PDF: {pdf_path}")
        print(e)

        return ""


# ==============================================================
# COLETAR TEXTOS DAS NORMAS
# ==============================================================

def coletar_normas_pdf(pasta_normas):

    normas = []

    if not os.path.exists(pasta_normas):

        print("Pasta de normas não encontrada.")

        return normas

    for arquivo in os.listdir(pasta_normas):

        if not arquivo.lower().endswith(".pdf"):
            continue

        caminho = os.path.join(pasta_normas, arquivo)

        texto = extrair_texto_norma(caminho)

        nome = arquivo.replace(".pdf", "").replace("_", " ").strip()

        normas.append({

            "nome": nome,
            "texto": texto

        })

    return normas


# ==============================================================
# GERAR TEXTO PARA O LLM
# ==============================================================

def extrair_legislacao_normas(pasta_normas):

    normas = coletar_normas_pdf(pasta_normas)

    textos = []

    for n in normas:

        textos.append(f"""
NORMA:
{n["nome"]}

TEXTO:
{n["texto"]}

--------------------------------
""")

    return "\n".join(textos)