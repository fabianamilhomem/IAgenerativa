# ==============================================================
# MRC PARSER - Lê a MRC e transforma em estrutura de auditoria.
# ==============================================================
# Responsável por ler a planilha da MRC enviada via Streamlit
# e extrair os riscos priorizados (Risco Residual = ALTO ou EXTREMO)
# ==============================================================

import pandas as pd

def parse_mrc(file_path):
    """
    Realiza o parsing da planilha de Matriz de Riscos e Controles.
    O file_path agora é fornecido dinamicamente pelo app_streamlit.py.
    """
    try:
        # Lê a aba "MRC" começando na linha 7 (header=6) conforme o padrão de template TJDFT
        df = pd.read_excel(
            file_path,
            sheet_name="MRC",
            header=6
        )
    except Exception as e:
        raise Exception(f"Erro ao abrir a planilha MRC: {e}")

    # -----------------------------------
    # POSIÇÕES DAS COLUNAS (Maturidade do Projeto)
    # -----------------------------------
    COL_OBJETIVO = 0 
    COL_RISCO = 1
    COL_CONTROLE = 9
    COL_CLASSIFICACAO_RR = 12

    # -----------------------------------
    # LIMPEZA E TRATAMENTO DE DADOS
    # -----------------------------------
    
    # Remove linhas onde a descrição do Risco está ausente
    df = df[df.iloc[:, COL_RISCO].notna()]

    # Propaga o Objetivo (ffill) para tratar células mescladas do Excel
    df.iloc[:, COL_OBJETIVO] = df.iloc[:, COL_OBJETIVO].ffill()

    # Preenche controles vazios para evitar que o LLM receba dados nulos
    df.iloc[:, COL_CONTROLE] = df.iloc[:, COL_CONTROLE].fillna("Controle não identificado")

    # -----------------------------------
    # FILTRAGEM DE RISCOS PRIORITÁRIOS
    # -----------------------------------
    # Mantém apenas riscos classificados como ALTO ou EXTREMO
    df_prioritarios = df[
        df.iloc[:, COL_CLASSIFICACAO_RR]
        .astype(str)
        .str.upper()
        .str.strip()
        .isin(["ALTO", "EXTREMO"])
    ].copy()

    # -----------------------------------
    # ESTRUTURAÇÃO PARA O GERADOR (LLM)
    # -----------------------------------
    mrc_data = []

    for _, row in df_prioritarios.iterrows():
        # Normalização de strings para garantir qualidade no prompt do Llama 3.1
        objetivo = str(row.iloc[COL_OBJETIVO]).strip()
        
        registro = {
            "objetivo": objetivo if objetivo.lower() != "nan" else "Objetivo não especificado",
            "risco": str(row.iloc[COL_RISCO]).strip(),
            "controle": str(row.iloc[COL_CONTROLE]).strip(),
            "risco_residual": str(row.iloc[COL_CLASSIFICACAO_RR]).strip()
        }

        mrc_data.append(registro)

    return mrc_data