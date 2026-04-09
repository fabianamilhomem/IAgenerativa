# ==============================================================
# RAG ENGINE
# ==============================================================
# Recupera normas relevantes e gera critérios de auditoria
# ==============================================================

import os
import json
import re

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    VECTOR_DB_NAME
)

# ==============================================================
# CARREGAR DOCUMENTOS
# ==============================================================

def load_documents(folder):

    docs = []

    if not os.path.exists(folder):
        return docs

    for file in os.listdir(folder):

        if file.lower().endswith(".pdf"):

            path = os.path.join(folder, file)

            loader = PyPDFLoader(path)

            docs.extend(loader.load())

    return docs

# ==============================================================
# DIVIDIR TEXTO POR ARTIGOS (MELHORIA RAG JURÍDICO)
# ==============================================================

def split_by_articles(text):

    """
    Divide o texto jurídico por artigos (Art. 1º, Art. 2º etc.)
    Isso melhora muito a recuperação normativa.
    """

    partes = re.split(r'(?=Art\.?\s*\d+)', text)

    chunks = []

    for p in partes:

        p = p.strip()

        if len(p) > 50:

            chunks.append(p)

    return chunks

# ==============================================================
# CRIAR BASE VETORIAL
# ==============================================================

def create_vector_db(norms_path, vector_db_path):

    print("\nCriando base vetorial de normas...")

    documents = load_documents(norms_path)

    if len(documents) == 0:

        print("Nenhum PDF encontrado para indexação.")

        return None

    # ----------------------------------------------------------
    # EXTRAIR CHUNKS JURÍDICOS
    # ----------------------------------------------------------

    textos = []

    for doc in documents:

        conteudo = doc.page_content

        artigos = split_by_articles(conteudo)

        if artigos:

            textos.extend(artigos)

        else:

            textos.append(conteudo)

    # ----------------------------------------------------------
    # SPLITTER TRADICIONAL (fallback)
    # ----------------------------------------------------------

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks = []

    for texto in textos:

        if len(texto) > CHUNK_SIZE:

            partes = splitter.split_text(texto)

            chunks.extend(partes)

        else:

            chunks.append(texto)


    print(f"Chunks gerados: {len(chunks)}")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    db = Chroma.from_texts(
        chunks,
        embeddings,
        persist_directory=vector_db_path
    )

    print("Base vetorial criada.")

    return db

# ==============================================================
# CARREGAR BASE EXISTENTE
# ==============================================================

def load_vector_db(vector_db_path):

    if not os.path.exists(vector_db_path):

        return None

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    db = Chroma(
        persist_directory=vector_db_path,
        embedding_function=embeddings
    )

    return db

# ==============================================================
# GARANTIR BASE VETORIAL
# ==============================================================

def get_or_create_vector_db(norms_path, vector_db_path):

    db = load_vector_db(vector_db_path)

    if db is None:

        db = create_vector_db(norms_path, vector_db_path)

    return db

# ====================================================================
# BUSCAR CONTEXTO NAS NORMAS - RAG + MMR
# ====================================================================

def search_norms(query, project_db=None, general_db=None, k=4):

    docs = []

    # ----------------------------------------------------------
    # BASE DO PROJETO
    # ----------------------------------------------------------

    if project_db:

        try:

            docs.extend(
                project_db.max_marginal_relevance_search(
                    query,
                    k=2,
                    fetch_k=6
                )
            )

        except:

            docs.extend(
                project_db.similarity_search(
                    query,
                    k=2
                )
            )

    # ----------------------------------------------------------
    # BASE GERAL DE NORMAS
    # ----------------------------------------------------------

    if general_db:

        try:

            docs.extend(
                general_db.max_marginal_relevance_search(
                    query,
                    k=2,
                    fetch_k=6
                )
            )

        except:

            docs.extend(
                general_db.similarity_search(
                    query,
                    k=2
                )
            )

    if len(docs) == 0:

        return ""

    # ----------------------------------------------------------
    # REMOVER DUPLICAÇÃO DE TRECHOS
    # ----------------------------------------------------------

    textos = []
    vistos = set()

    for d in docs:

        t = d.page_content.strip()

        # normalizar para evitar duplicações pequenas
        chave = t[:200]

        if chave not in vistos:

            textos.append(t)

            vistos.add(chave)

    context = "\n\n".join(textos)

    return context

# ==============================================================
# GERAR CAMPOS DA MATRIZ DE PLANEJAMENTO
# ==============================================================

def gerar_campos_planejamento(
        risco,
        procedimento,
        contexto_normas,
        chamar_llm):

    from src.audit_generator import extrair_json

    prompt = f"""
Você é um auditor governamental especialista em auditoria baseada em normas jurídicas.

Sua tarefa é produzir campos para uma MATRIZ DE PLANEJAMENTO DE AUDITORIA.

Use o risco identificado, o procedimento de auditoria e os trechos de normas
recuperados pelo sistema RAG.

================================================================
REGRAS IMPORTANTES
================================================================

O campo CRITÉRIO deve obrigatoriamente citar:

• nome da norma
• número da norma
• artigo
• inciso ou alínea quando existir

Exemplo de resposta correta para CRITÉRIO:

Lei 12.527/2011 (Lei de Acesso à Informação), art. 8º, inciso I – obrigação de divulgação ativa de informações de interesse coletivo.

Resolução CNJ nº 215/2015, art. 3º – obrigação de transparência ativa pelos órgãos do Poder Judiciário.

Instrução Normativa TCU nº 84/2020, arts. 8º e 9º – requisitos para divulgação de informações e prestação de contas.

NÃO responda com conceitos genéricos.

================================================================
RISCO IDENTIFICADO
================================================================

{risco}

================================================================
PROCEDIMENTO DE AUDITORIA
================================================================

{procedimento}

================================================================
TRECHOS DE NORMAS RECUPERADOS PELO RAG
================================================================

{contexto_normas}

================================================================
RESPONDA SOMENTE EM JSON VÁLIDO
================================================================

{{
"criterio": "Norma jurídica + artigo + inciso + obrigação normativa",
"informacoes_requeridas": "documentos, registros ou evidências necessários para execução do procedimento",
"fontes_informacao": "sistemas, bases de dados, documentos ou unidades organizacionais",
"possiveis_limitacoes": "restrições que podem afetar a execução da auditoria",
"possiveis_achados": "irregularidades ou falhas que podem ser identificadas"
}}
"""

    resposta = chamar_llm(prompt)

    try:
        return extrair_json(resposta)
    except Exception as e:
        print("Erro ao interpretar resposta do RAG:", e)
        return {
            "criterio": "Erro na extração",
            "informacoes_requeridas": "",
            "fontes_informacao": "",
            "possiveis_limitacoes": "",
            "possiveis_achados": ""
        }