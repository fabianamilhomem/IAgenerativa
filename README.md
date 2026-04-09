# AuditGen — Sistema de Inteligência Artificial para Auditoria Governamental

Este sistema aplica técnicas de Inteligência Artificial, com uso de Modelos de Linguagem de Grande Escala (LLM) e abordagem RAG (Retrieval-Augmented Generation), para automatizar a elaboração de **Programas de Auditoria** e **Matrizes de Planejamento** para o TJDFT.

## Tecnologias Utilizadas

* [cite_start]**LLM:** Llama-3.1-8B-Instruct (via Hugging Face API)[cite: 101, 103].
* [cite_start]**Embeddings:** `all-MiniLM-L6-v2` (Sentence Transformers)[cite: 73, 74].
* [cite_start]**Vector DB:** ChromaDB (Persistência local)[cite: 78, 101].
* [cite_start]**Orquestração:** LangChain[cite: 79, 132].
* [cite_start]**Interface:** Streamlit[cite: 93].
--- 

## Estrutura do Projeto e Funções dos Arquivos

O sistema é dividido em módulos para garantir organização e facilidade de manutenção:

### 1. Interface e Orquestração
* **`app_streamlit.py`**: Ponto de entrada da aplicação. Gerencia a interface web, coleta inputs do usuário (títulos, unidades, prazos), processa uploads de arquivos e exibe os botões de download.
* **`src/audit_generator.py`**: Orquestrador da IA. Define o comportamento do LLM, gerencia o *System Prompt* de auditoria e coordena a geração dos blocos de texto (Introdução, Justificativa, etc.).

### 2. Motor de Inteligência e Dados (RAG)
* **`src/rag_engine.py`**: Responsável pela "leitura" inteligente das normas. Divide os PDFs em artigos, cria a base vetorial e busca os trechos jurídicos mais relevantes para cada procedimento.
* **`src/llm_cache.py`**: Armazena respostas anteriores do LLM. Se você rodar o mesmo projeto novamente, ele recupera do disco em vez de gastar tokens da API.
* **`src/mrc_parser.py`**: Especializado em ler a Matriz de Riscos e Controles (MRC) em Excel e extrair os dados para o auditor de IA.
* **`src/normas_parser.py`**: Utilitário para extração de texto bruto de arquivos PDF.

### 3. Geradores de Documentos (Templates)
* **`src/docx_generator.py`**: Preenche o template institucional `.docx`. Gerencia formatações complexas, como manter títulos fixos, aplicar fonte Arial 12 e forçar alinhamento à esquerda em listas.
* **`src/excel_generator.py`**: Preenche a Matriz de Planejamento `.xlsx`. Utiliza processamento em lotes (Batch) para fundamentar cada teste de auditoria com as normas encontradas pelo RAG.

### 4. Configurações e Utilitários
* **`src/config.py`**: Arquivo central de parâmetros. Aqui se define o modelo de IA, o modelo de Embedding (`all-MiniLM-L6-v2`), e os tamanhos de corte de texto (Chunks).

---

## Fluxo de Chamadas (Ordem de Execução)

Quando o usuário clica em **"Iniciar Processamento Inteligente"**, o sistema segue esta sequência:

1.  **Input**: `app_streamlit` recebe os dados e salva os arquivos na pasta do projeto.
2.  **Parsing**: `mrc_parser` lê os riscos do Excel.
3.  **Indexação**: `rag_engine` cria o banco de dados vetorial (`vector_db`) com os PDFs de normas.
4.  **Cérebro**: `audit_generator` envia os riscos e o contexto para o Llama 3.1.
5.  **Fundamentação**: `excel_generator` pede ao `rag_engine` para buscar o artigo de lei exato para cada procedimento gerado.
6.  **Saída**: `docx_generator` e `excel_generator` gravam os arquivos finais na pasta `/output`.

---

## Como Executar a Aplicação

### 1. Preparação do Ambiente
Certifique-se de ter o Python 3.10+ instalado. No terminal, dentro da pasta do projeto, crie e ative seu ambiente virtual, depois instale as dependências:

```bash
python -m venv venv
venv\Scripts\activate

# Atualizar o pip e instalar todas as dependências do projeto
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configuração de Chaves

Crie um arquivo chamado `OPEN_API_Key.env` na raiz do projeto com o seguinte conteúdo:
```env
OPEN_API_KEY=seu_token_aqui
```
Obs.: Por segurança, o arquivo `.env` não é versionado no repositório.

### 3. Execução da Aplicação
Para subir o servidor web do Streamlit e interagir com o sistema pelo navegador:
```bash
streamlit run app_streamlit.py
```

## Fluxo de Uso:
    1. Upload da MRC: Insira a planilha Excel com os riscos.
    2. Upload de Normas: Insira os PDFs (Portarias, Resoluções) para o RAG.
    3. Processamento: Clique em "Iniciar Processamento Inteligente".
    4. Download: Baixe os documentos gerados na seção 4 da interface.

# Observações Técnicas
    - Truncamento de JSON: Caso a geração massiva falhe, ajuste o max_tokens para 4000 em src/audit_generator.py.
    - Qualidade do PDF: O sistema requer PDFs pesquisáveis (com camada de texto) para indexação correta no RAG.

## Segurança e Boas Práticas
- As chaves de API não são armazenadas no repositório
- O projeto utiliza variáveis de ambiente para proteção de credenciais
- O arquivo `.env` é ignorado via `.gitignore`
- O arquivo `.env` deve ser adicionado na raiz do projeto
Essa abordagem segue boas práticas de desenvolvimento seguro e proteção de dados.