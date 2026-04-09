# ==============================================================
# LLM CACHE
# ==============================================================
# Este módulo centraliza o mecanismo de cache das respostas do LLM.
#
# Objetivos principais:
#
# 1. Reduzir custos de execução da aplicação
#    - Evita chamadas repetidas ao modelo (Claude / Anthropic)
#    - Reutiliza respostas previamente geradas para prompts idênticos
#
# 2. Melhorar desempenho da aplicação
#    - Respostas podem ser recuperadas instantaneamente do cache
#    - Evita latência de chamadas externas à API
#
# 3. Evitar dependências circulares (circular import)
#    - O cache era originalmente implementado no audit_generator.py
#    - Como excel_generator.py também utiliza o cache, a lógica foi
#      isolada neste módulo para permitir reutilização segura
#
# Funcionamento:
#
# - Cada prompt enviado ao LLM é normalizado e convertido em um hash MD5
# - O hash é utilizado como nome do arquivo no diretório "cache/"
# - Se o arquivo existir, a resposta é carregada do cache
# - Caso contrário, a chamada ao LLM é realizada e a resposta é salva
#
# Estrutura de cache:
#
# cache/
#   <hash_do_prompt>.json
#
# Este mecanismo reduz significativamente o custo de uso do LLM
# durante desenvolvimento, testes e execuções repetidas da aplicação.
# ==============================================================

import os
import re
import hashlib


def gerar_hash_prompt(prompt):

    prompt = prompt.strip()

    prompt = re.sub(r"\s+", " ", prompt)

    prompt = prompt.replace("\n", " ")

    return hashlib.md5(prompt.encode("utf-8")).hexdigest()


def buscar_cache(prompt):

    cache_dir = "cache"

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    prompt_hash = gerar_hash_prompt(prompt)

    cache_file = os.path.join(cache_dir, f"{prompt_hash}.json")

    if os.path.exists(cache_file):

        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read()

    return None


def salvar_cache(prompt, resposta):

    cache_dir = "cache"

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    prompt_hash = gerar_hash_prompt(prompt)

    cache_file = os.path.join(cache_dir, f"{prompt_hash}.json")

    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(resposta)