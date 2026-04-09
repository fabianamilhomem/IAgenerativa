# =========================================
# Configurações do Sistema
# =========================================
# Modelo LLM hugging face
# Llama-3.1-8B-Instruct

import os
from dotenv import load_dotenv

# =========================================
# CARREGAR API KEY
# =========================================

load_dotenv("OPEN_API_Key.env")

OPEN_API_KEY = os.getenv("OPEN_API_KEY")

# =========================================
# CAMINHOS DO PROJETO
# =========================================

PROJECTS_PATH = "projects"

GENERAL_NORMS_PATH = "data/normas_gerais"

TEMPLATES_PATH = "templates"


# =========================================
# MODELOS DE IA
# =========================================

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# EMBEDDING_MODEL = "BAAI/bge-m3"

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

# =========================================
# PARÂMETROS DO RAG
# =========================================

CHUNK_SIZE = 1000  # Aumentado de 800 para 1000 para gerar menos chunks
CHUNK_OVERLAP = 100


# =========================================
# VECTOR DATABASE
# =========================================

VECTOR_DB_NAME = "vector_db"