
# =========================================================
# Aplicação AUDITGEN – Gerador de Auditoria com IA
# =========================================================
# [1] Criar Projeto
# [2] Upload da MRC
# [3] Upload das Normas
# [4] Executar Auditoria
# [5] Download dos documentos

import streamlit as st
import os
import json
import sys
from pathlib import Path

# Garante que o src seja visto (mesmo na raiz)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# 1. Primeiro importe o config para carregar as chaves de ambiente
from src import config

# 2. Depois as demais importações
from src.mrc_parser import parse_mrc
from src.rag_engine import get_or_create_vector_db
from src.audit_generator import gerar_programa_auditoria, chamar_llm
from src.docx_generator import gerar_docx_programa_auditoria
from src.excel_generator import gerar_matriz_planejamento

BASE_PROJECTS = "projects"

st.set_page_config(
    page_title="AuditGen - TJDFT",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ícone alterado para Lupa (🔍) coerente com Auditoria e IA
st.title("🔍 AuditGen — Auditoria com IA Generativa")
st.markdown("---")

# Sidebar para seleção/criação de projeto
with st.sidebar:
    st.header("Configurações do Projeto")
    
    if not os.path.exists(BASE_PROJECTS):
        os.makedirs(BASE_PROJECTS)
    
    projetos_existentes = [d for d in os.listdir(BASE_PROJECTS) if os.path.isdir(os.path.join(BASE_PROJECTS, d))]
    
    modo = st.radio("Ação:", ["Selecionar Projeto", "Criar Novo Projeto"])
    
    if modo == "Criar Novo Projeto":
        novo_projeto = st.text_input("Nome da nova auditoria")
        if st.button("Criar Estrutura"):
            path = Path(BASE_PROJECTS) / novo_projeto
            (path / "normas").mkdir(parents=True, exist_ok=True)
            (path / "mrc").mkdir(parents=True, exist_ok=True)
            (path / "output").mkdir(parents=True, exist_ok=True)
            st.success(f"Projeto '{novo_projeto}' criado!")
            st.rerun()
    else:
        project_name = st.selectbox("Selecione a Auditoria:", [""] + projetos_existentes)

if 'project_name' in locals() and project_name:
    project_path = Path(BASE_PROJECTS) / project_name
    
    col_up1, col_up2 = st.columns(2)

    with col_up1:
        st.header("1. Matriz de Riscos (MRC)")
        uploaded_mrc = st.file_uploader("Upload da MRC (Excel)", type=["xlsx"])
        if uploaded_mrc:
            mrc_dir = project_path / "mrc"
            mrc_dir.mkdir(exist_ok=True)
            mrc_file_path = mrc_dir / "Matriz_de_Riscos_e_Controles.xlsx"
            with open(mrc_file_path, "wb") as f:
                f.write(uploaded_mrc.getbuffer())
            st.success("✅ MRC salva.")

    with col_up2:
        st.header("2. Normas e Legislação")
        uploaded_norms = st.file_uploader("Upload de PDFs", type=["pdf"], accept_multiple_files=True)
        if uploaded_norms:
            norms_dir = project_path / "normas"
            for pdf in uploaded_norms:
                with open(norms_dir / pdf.name, "wb") as f:
                    f.write(pdf.getbuffer())
            st.success(f"✅ {len(uploaded_norms)} normas carregadas.")

    st.markdown("---")

    # =========================================================
    # [3] Execução da Inteligência - Campos Atualizados
    # =========================================================
    st.header("3. Execução da Inteligência")
    
    col_input1, col_input2 = st.columns(2)

    with col_input1:
        modalidade = st.selectbox(
            "Modalidade", 
            ["Operacional", "Conformidade", "Financeira", "Conformidade e Operacional"]
        )
        objeto = st.text_input("Objeto da Auditoria (ex: Portal da Transparência)")
        unidades_auditadas = st.text_area("Unidade(s) Auditada(s)", help="Pressione Enter para separar as unidades.", height=100)
        equipe = st.text_area("Equipe de Auditoria", help="Pressione Enter para separar os membros da equipe.", height=100)
        nucleo_auditoria = st.text_input("Núcleo de Auditoria")

    with col_input2:
        periodo = st.text_input("Período de realização da Auditoria")
        pa_sei_autorizacao = st.text_input("PA SEI Autorização (Presidente)")
        pa_sei_auditoria = st.text_input("PA SEI da Auditoria")
        objetivo_geral = st.text_area("Objetivo Geral")

    # Montagem do dicionário de dados atualizado
    dados_auditoria = {
        "titulo_auditoria": project_name,
        "modalidade": modalidade,
        "objeto": objeto,
        "objetivo": objetivo_geral,
        "unidades_auditadas": unidades_auditadas,
        "equipe": equipe,
        "nucleo_auditoria": nucleo_auditoria,
        "periodo": periodo,
        "sei_autorizacao": pa_sei_autorizacao,
        "sei_auditoria": pa_sei_auditoria
    }

    if st.button("🚀 Iniciar Processamento Inteligente"):
        with st.status("Processando auditoria... isso pode levar alguns minutos.", expanded=True) as status:
            
            # 1. RAG - Criar base vetorial
            st.write("Indexando normas no Vector DB...")
            vector_db_path = project_path / "vector_db"
            get_or_create_vector_db(str(project_path / "normas"), str(vector_db_path))
            
            # 2. Gerar conteúdo via LLM (Llama 3.1)
            st.write("Chamando Llama 3.1 para gerar conteúdo técnico...")
            mrc_path = project_path / "mrc" / "Matriz_de_Riscos_e_Controles.xlsx"
            resultado_llm = gerar_programa_auditoria(dados_auditoria, str(mrc_path))
            st.session_state["resultado_llm"] = resultado_llm
            
            # 3. Gerar Documentos Físicos
            st.write("Gerando arquivos Word e Excel...")
            docx_path = gerar_docx_programa_auditoria(resultado_llm, dados_auditoria, str(project_path))
            riscos = parse_mrc(str(mrc_path))
            excel_path = gerar_matriz_planejamento(resultado_llm, dados_auditoria, riscos, str(project_path), chamar_llm)
            
            st.session_state["docx_final"] = docx_path
            st.session_state["excel_final"] = excel_path
            
            status.update(label="✅ Processamento Concluído!", state="complete")

    # =========================================================
    # [5] Download
    # =========================================================
    if "docx_final" in st.session_state:
        st.markdown("---")
        st.header("4. Download dos Resultados")
        c1, c2 = st.columns(2)
        
        with c1:
            with open(st.session_state["docx_final"], "rb") as f:
                st.download_button("📂 Baixar Programa de Auditoria (Word)", f, file_name=f"Programa_{project_name}.docx")
        
        with c2:
            with open(st.session_state["excel_final"], "rb") as f:
                st.download_button("📊 Baixar Matriz de Planejamento (Excel)", f, file_name=f"Matriz_{project_name}.xlsx")

else:
    st.info("👈 Crie ou selecione uma auditoria na barra lateral para começar.")