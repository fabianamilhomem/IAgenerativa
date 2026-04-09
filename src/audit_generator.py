# ==============================================================
# AUDIT GENERATOR
# ==============================================================
# Gera automaticamente partes do Programa de Auditoria
# utilizando LLM + dados da MRC.
# ==============================================================

import os
import json
import re
import time
# Retornando para a biblioteca do huggingface API
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from src.config import OPEN_API_KEY, MODEL_ID # Usando a chave configurada no seu config.py
from src.mrc_parser import parse_mrc
from src.docx_generator import gerar_docx_programa_auditoria
from src.excel_generator import gerar_matriz_planejamento
from src.normas_parser import extrair_legislacao_normas
from src.llm_cache import buscar_cache, salvar_cache


# ==============================================================
# CLIENTE LLM (Usando InferenceClient)
# ==============================================================
client = InferenceClient(token=OPEN_API_KEY)

# ==============================================================
# EXTRAÇÃO ROBUSTA DE JSON
# ==============================================================

def extrair_json(texto):

    if texto is None:
        raise Exception("Resposta vazia do modelo.")

    texto = str(texto)

    texto = texto.replace("\u200b", "")
    texto = texto.replace("\ufeff", "")
    texto = texto.replace("\u200e", "")

    texto = texto.replace("```json", "")
    texto = texto.replace("```", "")

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio != -1 and fim != -1:

        json_text = texto[inicio:fim+1]

        # PATCH — limpeza para evitar quebra de JSON
        json_text = json_text.replace("\n", " ")
        json_text = json_text.replace("\r", " ")

        json_text = json_text.replace("•", "-")
        json_text = json_text.replace("\t", " ")

        json_text = json_text.replace("“", '"').replace("”", '"')
        json_text = json_text.replace("’", "'")

        json_text = re.sub(r",\s*}", "}", json_text)
        json_text = re.sub(r",\s*]", "]", json_text)
        json_text = re.sub(r"}\s*{", "},{", json_text)

        try:
            return json.loads(json_text, strict=False)
        except:
            pass

    # Fallback via Regex (mecanismo de maturidade atual)
    resultado = {}

    intro = re.search(r'"introducao"\s*:\s*"(.*?)"', texto, re.DOTALL)
    if intro:
        resultado["introducao"] = intro.group(1)

    just = re.search(r'"justificativa"\s*:\s*"(.*?)"', texto, re.DOTALL)
    if just:
        resultado["justificativa"] = just.group(1)

    esc = re.search(r'"escopo"\s*:\s*"(.*?)"', texto, re.DOTALL)
    if esc:
        resultado["escopo"] = esc.group(1)

    questoes = re.findall(r'"questoes_auditoria"\s*:\s*\[(.*?)\]', texto, re.DOTALL)

    if questoes:
        lista_q = re.findall(r'"(.*?)"', questoes[0])
        resultado["questoes_auditoria"] = lista_q

    procedimentos = []

    blocos = re.findall(
        r'"questao"\s*:\s*(\d+).*?"procedimentos"\s*:\s*\[(.*?)\]',
        texto,
        re.DOTALL
    )

    for numero, bloco in blocos:

        itens = re.findall(r'"(.*?)"', bloco)

        procedimentos.append({
            "questao": int(numero),
            "procedimentos": itens
        })

    if procedimentos:
        resultado["procedimentos_auditoria"] = procedimentos

    legis = re.search(r'"legislacao"\s*:\s*"(.*?)"', texto, re.DOTALL)

    if legis:

        texto_leg = legis.group(1)

        texto_leg = texto_leg.replace("\\n", "\n")

        resultado["legislacao"] = texto_leg.strip()

    if not resultado:

        print("\nRESPOSTA DO MODELO (DEBUG):\n")
        print(texto)

        raise Exception("Não foi possível extrair dados da resposta do modelo.")

    return resultado

# ==============================================================
# CHAMADA SEGURA AO MODELO (Ajustado para InferenceClient)
# ==============================================================
def chamar_llm(prompt):
    prompt = prompt[:12000]
    resposta_cache = buscar_cache(prompt)
    if resposta_cache:
        print("\nResposta recuperada do cache.\n")
        return resposta_cache

    for tentativa in range(5):
        try:
            # Usando chat_completion do InferenceClient conforme seu backup
            response = client.chat_completion(
                model=MODEL_ID,
                messages=[
                    {
                        "role": "system",
                        "content": """
        Você é um auditor interno especialista em auditoria governamental.

        RESPONDA SOMENTE COM JSON VÁLIDO.

        Regras obrigatórias:
        - Não escreva texto antes do JSON
        - Não escreva texto depois do JSON
        - Não use markdown
        - Não explique nada
        - Apenas retorne JSON válido
        """
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.1 # Manter baixa para evitar variações criativas que quebrem o JSON
            )
            
            texto = response.choices[0].message.content
            
            # Garantir que texto seja string (caso venha como lista de tokens em algumas versões)
            if isinstance(texto, list):
                texto = texto[0]["text"]
            
            texto = str(texto).strip()
            
            inicio = texto.find("{")
            fim = texto.rfind("}")
            if inicio != -1 and fim != -1:
                texto = texto[inicio:fim+1]

            salvar_cache(prompt, texto)
            return texto

        except HfHubHTTPError as e:
            if "429" in str(e):
                espera = (tentativa + 1) * 5
                print(f"\nRate limit atingido. Aguardando {espera}s...")
                time.sleep(espera)
            else:
                print(f"[DEBUG] Erro HfHub: {e}")
                time.sleep(2)
        except Exception as e:
            print(f"[DEBUG] Erro inesperado: {e}")
            time.sleep(2)

    raise Exception("Falha ao chamar o modelo Llama via InferenceClient.")

# ==============================================================
# BLOCO 1 — INTRODUÇÃO / JUSTIFICATIVA / ESCOPO
# ==============================================================

def gerar_bloco_contextual(dados_auditoria, objetivo_mrc, riscos_texto, prompt_base):

    prompt = prompt_base + f"""
Você é um auditor interno experiente do setor público brasileiro.

Produza as seguintes seções de um Programa de Auditoria do TJDFT:

1) introducao
2) justificativa
3) escopo

Responda exclusivamente em JSON:

{{
"introducao": "...",
"justificativa": "...",
"escopo": "..."
}}

DADOS DA AUDITORIA

Título: {dados_auditoria["titulo_auditoria"]}
Modalidade: {dados_auditoria["modalidade"]}
Objeto: {dados_auditoria["objeto"]}
Objetivo: {dados_auditoria["objetivo"]}
Unidades auditadas: {dados_auditoria["unidades_auditadas"]}

OBJETIVO DA MRC
{objetivo_mrc}

RISCOS IDENTIFICADOS
{riscos_texto}
"""

    for tentativa in range(3):

        resposta = chamar_llm(prompt)

        try:
            return extrair_json(resposta)

        except Exception:

            print(f"\nFalha ao interpretar JSON (tentativa {tentativa+1})")

            if tentativa == 2:
                raise
pass

# ==============================================================
# BLOCO 2 — QUESTÕES E PROCEDIMENTOS
# ==============================================================

def gerar_bloco_exames(dados_auditoria, objetivo_mrc, riscos_texto, prompt_base):

    prompt = prompt_base + f"""
Você é um auditor interno experiente do setor público brasileiro.

Elabore:

1) questoes_auditoria
2) procedimentos_auditoria

Responda SOMENTE com JSON válido.
Não escreva explicações antes ou depois.
Use exatamente o seguinte formato:

{{
"questoes_auditoria": [
"Questão 1",
"Questão 2",
"Questão 3"
],

"procedimentos_auditoria": [
{{
"questao": 1,
"procedimentos": [
"Procedimento de auditoria",
"Procedimento de auditoria"
]
}},
{{
"questao": 2,
"procedimentos": [
"Procedimento de auditoria",
"Procedimento de auditoria"
]
}}
]
}}

DADOS DA AUDITORIA

Título: {dados_auditoria["titulo_auditoria"]}
Objeto: {dados_auditoria["objeto"]}
Objetivo: {dados_auditoria["objetivo"]}

OBJETIVO DA MRC
{objetivo_mrc}

RISCOS IDENTIFICADOS
{riscos_texto}
"""

    for tentativa in range(3):

        resposta = chamar_llm(prompt)

        try:
            return extrair_json(resposta)

        except Exception:

            print(f"\nFalha ao interpretar JSON (tentativa {tentativa+1})")

            if tentativa == 2:
                raise
pass

# ==============================================================
# AJUSTE AUTOMÁTICO DE QUESTÕES
# ==============================================================

def ajustar_quantidade_questoes(resultado, riscos):

    total_riscos = len(riscos)

    questoes = resultado.get("questoes_auditoria", [])
    procedimentos = resultado.get("procedimentos_auditoria", [])

    if len(questoes) < total_riscos:

        faltantes = total_riscos - len(questoes)

        for i in range(faltantes):

            questoes.append(
                "Avaliar a adequação dos controles internos associados ao risco identificado."
            )

            procedimentos.append({
                "questao": len(questoes),
                "procedimentos": [
                    "Realizar análise documental relacionada ao risco identificado.",
                    "Entrevistar os responsáveis pelo processo.",
                    "Verificar evidências de funcionamento dos controles internos."
                ]
            })

    resultado["questoes_auditoria"] = questoes
    resultado["procedimentos_auditoria"] = procedimentos

    return resultado
pass

# ==============================================================
# BLOCO 3 — LEGISLAÇÃO
# ==============================================================

def gerar_bloco_legislacao(texto_normas):

    prompt = f"""
Você é especialista em direito administrativo e auditoria pública.

A seguir estão trechos iniciais de normas jurídicas.

Para cada norma:

1. Identifique o nome da norma.
2. Extraia o assunto principal da norma (ementa resumida).

Responda SOMENTE em JSON no formato:

{{
"legislacao": "Norma: assunto\\nNorma: assunto"
}}

TEXTOS DAS NORMAS:

{texto_normas}
"""

    resposta = chamar_llm(prompt)

    return extrair_json(resposta)
pass

# ==============================================================
# FUNÇÃO PRINCIPAL (Ajustada para Dinamismo de Projetos)
# ==============================================================

def gerar_programa_auditoria(dados_auditoria, mrc_path):
    # AJUSTE: Identifica o diretório do projeto dinamicamente a partir do mrc_path
    project_dir = os.path.dirname(os.path.dirname(mrc_path))
    
    riscos = parse_mrc(mrc_path)
    if len(riscos) == 0:
        raise Exception("Nenhum risco priorizado encontrado na MRC.")

    objetivo_mrc = riscos[0]["objetivo"]
    riscos_texto = ""
    for r in riscos:
        riscos_texto += f"\nRISCO:\n{r['risco']}\nCONTROLE:\n{r['controle']}\nRISCO RESIDUAL:\n{r['risco_residual']}\n-------------------------\n"

    # AJUSTE: Pasta de normas agora é relativa ao projeto atual, não fixa em 'transparencia'
    pasta_normas = os.path.join(project_dir, "normas")
    texto_normas = extrair_legislacao_normas(pasta_normas)

    prompt_base = f"""
Você é um auditor interno experiente do setor público brasileiro,
especializado em auditoria governamental baseada em riscos.

Sua tarefa é redigir trechos de um PROGRAMA DE AUDITORIA institucional
do Tribunal de Justiça do Distrito Federal e Territórios (TJDFT).

O texto deve possuir o mesmo nível técnico encontrado em documentos de
auditoria do Tribunal de Contas da União (TCU), do Conselho Nacional de Justiça (CNJ)
e de unidades de auditoria interna governamental.

====================================================================
REGRAS IMPORTANTES
====================================================================

• Utilize linguagem formal e técnica de auditoria governamental.
• Produza textos completos, com parágrafos desenvolvidos.
• O texto deve parecer escrito por um auditor profissional.
• Não escreva respostas curtas ou resumidas.
• Não invente informações que não estejam nos dados fornecidos.
• Não invente unidades organizacionais, normas ou dados institucionais.

====================================================================
DADOS DA AUDITORIA
====================================================================

Título da auditoria:
{dados_auditoria["titulo_auditoria"]}

Modalidade da auditoria:
{dados_auditoria["modalidade"]}

Objeto da auditoria:
{dados_auditoria["objeto"]}

Objetivo da auditoria:
{dados_auditoria["objetivo"]}

Unidades auditadas:
{dados_auditoria["unidades_auditadas"]}

====================================================================
OBJETIVO IDENTIFICADO NA MATRIZ DE RISCOS E CONTROLES (MRC)
====================================================================

{objetivo_mrc}

====================================================================
RISCOS PRIORITÁRIOS IDENTIFICADOS NA MRC
====================================================================

{riscos_texto}

====================================================================
REQUISITOS DE QUALIDADE DO TEXTO
====================================================================

INTRODUÇÃO
A introdução deve contextualizar a auditoria no âmbito do TJDFT,
abordando a importância da transparência, da governança pública,
da gestão de riscos e dos controles internos na administração pública.

JUSTIFICATIVA
A justificativa deve explicar por que a auditoria é necessária,
considerando os riscos identificados na MRC, a relevância do tema
para a administração pública e a necessidade de fortalecimento
dos controles internos.

ESCOPO
O escopo deve delimitar claramente o objeto examinado, indicando
quais processos, controles ou atividades serão avaliados pela auditoria.

QUESTÕES DE AUDITORIA
As questões de auditoria devem:

• derivar diretamente dos riscos identificados na MRC
• permitir verificação objetiva durante os exames de auditoria
• avaliar controles internos, governança ou conformidade normativa
• ser formuladas de forma clara e técnica

Evite perguntas genéricas.

Cada risco identificado deve gerar pelo menos uma questão de auditoria.

PROCEDIMENTOS DE AUDITORIA

Os procedimentos de auditoria devem indicar as atividades que
serão executadas pelos auditores para responder às questões
de auditoria.

Os procedimentos devem:

• estar diretamente relacionados às questões de auditoria
• indicar ações concretas de verificação
• incluir análise documental, entrevistas, testes ou amostragem
• ser redigidos em formato de lista

Cada questão de auditoria deve possuir um conjunto de
procedimentos de auditoria associados.
"""

    bloco1 = gerar_bloco_contextual(dados_auditoria, objetivo_mrc, riscos_texto, prompt_base)
    bloco2 = gerar_bloco_exames(dados_auditoria, objetivo_mrc, riscos_texto, prompt_base)

    try:
        bloco3 = gerar_bloco_legislacao(texto_normas)
    except:
        bloco3 = {"legislacao": "Não foi possível extrair a legislação."}

    resultado = {**bloco1, **bloco2, **bloco3}
    resultado = ajustar_quantidade_questoes(resultado, riscos)

    return resultado