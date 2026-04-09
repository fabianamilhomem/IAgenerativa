# =========================================
# Código para testar e validar o RAG
# =========================================
# Sempre que executar este script apagar a pasta test_vector_db

import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# =========================================
# CAMINHOS
# =========================================

GENERAL_PATH = "data/normas_gerais"
PROJECT_PATH = "projects/pro_saude/normas"

VECTOR_DB_PATH = "test_vector_db"


# =========================================
# FUNÇÃO PARA CARREGAR PDFs
# =========================================

def load_pdfs(folder):

    documents = []

    if not os.path.exists(folder):

        print(f"Pasta não encontrada: {folder}")
        return documents

    for file in os.listdir(folder):

        if file.lower().endswith(".pdf"):

            path = os.path.join(folder, file)

            try:

                loader = PyPDFLoader(path)

                docs = loader.load()

                print(f"Carregado: {file} ({len(docs)} páginas)")

                for d in docs:

                    # metadata simples e confiável
                    d.metadata["arquivo"] = file

                    documents.append(d)

            except Exception as e:

                print(f"Erro ao carregar {file}: {e}")

    return documents


# =========================================
# CARREGAMENTO DOS DOCUMENTOS
# =========================================

print("\n--- Carregando normas gerais ---")

general_docs = load_pdfs(GENERAL_PATH)

print("\n--- Carregando normas do projeto ---")

project_docs = load_pdfs(PROJECT_PATH)

all_docs = general_docs + project_docs

print(f"\nTotal de páginas carregadas: {len(all_docs)}")


# =========================================
# CRIAÇÃO DOS CHUNKS
# =========================================

print("\n--- Criando chunks ---")

splitter = RecursiveCharacterTextSplitter(

    chunk_size=800,
    chunk_overlap=100

)

chunks = splitter.split_documents(all_docs)

print(f"Total de chunks criados: {len(chunks)}")


# =========================================
# EMBEDDINGS
# =========================================

print("\n--- Criando embeddings ---")

embeddings = HuggingFaceEmbeddings(

    model_name="sentence-transformers/all-MiniLM-L6-v2"

)


# =========================================
# CRIAÇÃO DO VECTOR DATABASE
# =========================================

print("\n--- Criando vector database ---")

db = Chroma.from_documents(

    chunks,
    embeddings,
    persist_directory=VECTOR_DB_PATH

)

print("Vector DB criado com sucesso")


# =========================================
# TESTE DE BUSCA SEMÂNTICA
# =========================================

print("\n--- Testando busca semântica ---")

query = "controles internos e continuidade de sistemas"

results = db.similarity_search(query, k=3)


# =========================================
# EXIBIÇÃO DOS RESULTADOS
# =========================================

for i, r in enumerate(results):

    print("\n=======================================")
    print("RESULTADO", i + 1)

    print("ARQUIVO:", r.metadata.get("arquivo"))
    print("PÁGINA:", r.metadata.get("page"))

    print("\nTRECHO:")
    print(r.page_content[:500])