import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image
import pdf2image
import io
import os
import tempfile

# Configuração da página
st.set_page_config(
    page_title="Busca em Notas Fiscais",
    page_icon="🔍",
    layout="wide"
)

# Estilo CSS personalizado
st.markdown("""
    <style>
        .main {
            padding: 2rem;
        }
        .stButton>button {
            width: 100%;
        }
        .pdf-result {
            padding: 1rem;
            border-radius: 5px;
            border: 1px solid #ddd;
            margin: 0.5rem 0;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def extrair_texto_pdf(arquivo):
    """
    Extrai texto de arquivos PDF, sejam eles digitais ou escaneados
    """
    try:
        # Primeiro tenta ler como PDF digital
        reader = PdfReader(arquivo)
        texto = ""
        for pagina in reader.pages:
            texto += pagina.extract_text()
            
        # Se não encontrou texto, trata como PDF escaneado
        if not texto.strip():
            # Converte PDF para imagem
            with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
                tmp.write(arquivo.getvalue())
                tmp.flush()
                imagens = pdf2image.convert_from_path(tmp.name)
                
            texto = ""
            for imagem in imagens:
                # Extrai texto da imagem usando OCR
                texto += pytesseract.image_to_string(imagem, lang='por')
                
        return texto
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
        return ""

def criar_indice(arquivos_uploaded):
    """
    Cria um índice de todos os PDFs e seus conteúdos
    """
    index = []
    
    for arquivo in arquivos_uploaded:
        with st.spinner(f'Processando {arquivo.name}...'):
            texto = extrair_texto_pdf(arquivo)
            index.append({
                'arquivo': arquivo.name,
                'conteudo': texto
            })
    
    return pd.DataFrame(index)

def main():
    # Título
    st.title("🔍 Busca em Notas Fiscais")
    st.write("Faça upload de suas notas fiscais em PDF e pesquise por produtos")
    
    # Sidebar para upload e configurações
    with st.sidebar:
        st.header("📁 Upload de Arquivos")
        arquivos = st.file_uploader(
            "Selecione os PDFs das notas fiscais",
            type=['pdf'],
            accept_multiple_files=True
        )
        
        if arquivos:
            st.success(f"✅ {len(arquivos)} arquivo(s) carregado(s)")
    
    # Área principal
    if arquivos:
        if 'df_index' not in st.session_state:
            with st.spinner('Processando arquivos...'):
                st.session_state.df_index = criar_indice(arquivos)
            st.success('✅ Processamento concluído!')
        
        # Área de busca
        st.header("🔎 Buscar Produtos")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            termo_busca = st.text_input(
                "Digite o nome do produto",
                placeholder="Ex: Café, Açúcar, etc."
            )
        
        with col2:
            buscar = st.button("Buscar", use_container_width=True)
        
        # Realiza a busca
        if termo_busca and buscar:
            mascara = st.session_state.df_index['conteudo'].str.lower().str.contains(
                termo_busca.lower(),
                regex=False
            )
            resultados = st.session_state.df_index[mascara]
            
            # Mostra resultados
            st.header("📋 Resultados")
            if len(resultados) == 0:
                st.warning(f"Nenhuma nota fiscal encontrada com o produto '{termo_busca}'")
            else:
                st.success(f"Encontrado em {len(resultados)} nota(s) fiscal(is)")
                
                for idx, row in resultados.iterrows():
                    with st.expander(f"📄 {row['arquivo']}", expanded=True):
                        st.write("Trechos relevantes:")
                        # Extrai e mostra o contexto onde o termo foi encontrado
                        texto = row['conteudo'].lower()
                        posicao = texto.find(termo_busca.lower())
                        inicio = max(0, posicao - 100)
                        fim = min(len(texto), posicao + 100)
                        contexto = "..." + texto[inicio:fim] + "..."
                        st.markdown(f"*{contexto}*")
    else:
        # Mensagem inicial
        st.info("👆 Faça upload dos arquivos PDF usando o menu lateral")
        
        # Exemplo de uso
        with st.expander("ℹ️ Como usar"):
            st.markdown("""
                1. Clique em 'Browse files' no menu lateral
                2. Selecione um ou mais arquivos PDF de notas fiscais
                3. Aguarde o processamento
                4. Digite o nome do produto que deseja buscar
                5. Clique em 'Buscar'
                
                Os resultados mostrarão em quais notas fiscais o produto foi encontrado.
            """)

if __name__ == "__main__":
    main()
