import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image
import pdf2image
import io
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import zipfile
import base64

# Configuração da página
st.set_page_config(
    page_title="Hiper Center - Busca em Notas Fiscais",
    page_icon="🔍",
    layout="wide"
)

# Inicializa variável de controle de reinicialização
if 'reiniciar_clicado' not in st.session_state:
    st.session_state.reiniciar_clicado = False

def reiniciar_sistema():
    st.session_state.reiniciar_clicado = True
    st.session_state.clear()

def extrair_texto_xml(conteudo):
    """
    Extrai informações relevantes de arquivos XML de NFe
    """
    try:
        root = ET.fromstring(conteudo)
        
        # Define o namespace padrão da NFe
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Extrai informações principais
        info = []
        
        # Informações da nota
        nfe_info = root.find('.//nfe:infNFe', ns)
        if nfe_info is not None:
            chave = nfe_info.get('Id', '')
            info.append(f"Chave: {chave}")
        
        # Dados do emitente
        emit = root.find('.//nfe:emit', ns)
        if emit is not None:
            nome_emit = emit.find('nfe:xNome', ns)
            cnpj_emit = emit.find('nfe:CNPJ', ns)
            if nome_emit is not None:
                info.append(f"Emitente: {nome_emit.text}")
            if cnpj_emit is not None:
                info.append(f"CNPJ: {cnpj_emit.text}")
        
        # Dados dos produtos
        produtos = root.findall('.//nfe:det', ns)
        for prod in produtos:
            prod_info = prod.find('nfe:prod', ns)
            if prod_info is not None:
                codigo = prod_info.find('nfe:cProd', ns)
                descricao = prod_info.find('nfe:xProd', ns)
                quantidade = prod_info.find('nfe:qCom', ns)
                valor = prod_info.find('nfe:vUnCom', ns)
                
                prod_text = []
                if descricao is not None:
                    prod_text.append(f"Produto: {descricao.text}")
                if codigo is not None:
                    prod_text.append(f"Código: {codigo.text}")
                if quantidade is not None:
                    prod_text.append(f"Qtd: {quantidade.text}")
                if valor is not None:
                    prod_text.append(f"Valor: {valor.text}")
                    
                info.append(" | ".join(prod_text))
        
        return "\n".join(info)
    except Exception as e:
        st.error(f"Erro ao processar XML: {str(e)}")
        return ""

def extrair_texto_pdf(arquivo):
    """
    Extrai texto de arquivos PDF, sejam eles digitais ou escaneados
    """
    try:
        reader = PdfReader(arquivo)
        texto = ""
        for pagina in reader.pages:
            texto += pagina.extract_text()
            
        if not texto.strip():
            with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
                tmp.write(arquivo.getvalue())
                tmp.flush()
                imagens = pdf2image.convert_from_path(tmp.name)
                
            texto = ""
            for imagem in imagens:
                texto += pytesseract.image_to_string(imagem, lang='por')
                
        return texto
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return ""
def criar_zip_resultado(arquivos_encontrados, todos_arquivos):
    """
    Cria um arquivo ZIP com os arquivos encontrados na busca
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for arquivo_nome in arquivos_encontrados:
            arquivo_original = next(
                (arq for arq in todos_arquivos if arq.name == arquivo_nome),
                None
            )
            
            if arquivo_original:
                arquivo_original.seek(0)
                zip_file.writestr(arquivo_original.name, arquivo_original.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer

def get_download_link(buffer, filename):
    """
    Cria um link de download para o arquivo ZIP
    """
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f'<a href="data:application/zip;base64,{b64}" download="{filename}" class="download-button">📥 Baixar todas em ZIP</a>'

def get_individual_download_link(arquivo, nome_arquivo):
    """
    Cria um link de download para um único arquivo
    """
    try:
        arquivo.seek(0)
        b64 = base64.b64encode(arquivo.getvalue()).decode()
        mime_type = 'application/pdf' if nome_arquivo.lower().endswith('.pdf') else 'application/xml'
        return f'<a href="data:{mime_type};base64,{b64}" download="{nome_arquivo}" class="download-button-small">⬇️ Baixar arquivo</a>'
    except Exception as e:
        return f"Erro ao gerar link: {str(e)}"

def processar_arquivos(arquivos_uploaded, progress_bar, status_text):
    """
    Processa os arquivos carregados com barra de progresso
    """
    index = []
    total_arquivos = len(arquivos_uploaded)
    
    for i, arquivo in enumerate(arquivos_uploaded):
        try:
            # Atualiza a barra de progresso
            progress_bar.progress((i + 1) / total_arquivos)
            status_text.text(f'Processando: {arquivo.name} ({i + 1} de {total_arquivos})')
            
            # Determina o tipo do arquivo
            tipo = 'PDF' if arquivo.name.lower().endswith('.pdf') else 'XML'
            
            # Processa o arquivo de acordo com seu tipo
            arquivo.seek(0)  # Reset do ponteiro do arquivo
            if tipo == 'PDF':
                texto = extrair_texto_pdf(arquivo)
            else:
                texto = extrair_texto_xml(arquivo.getvalue())
            
            if texto:  # Só adiciona se extraiu algum texto
                index.append({
                    'arquivo': arquivo.name,
                    'tipo': tipo,
                    'conteudo': texto
                })
            else:
                st.warning(f"Nenhum texto extraído de {arquivo.name}")
                
        except Exception as e:
            st.warning(f"Erro ao processar {arquivo.name}: {str(e)}")
            continue
    
    if not index:
        st.error("Nenhum arquivo foi processado com sucesso.")
        return pd.DataFrame(columns=['arquivo', 'tipo', 'conteudo'])
    
    return pd.DataFrame(index)
def main():
    st.title("Hiper Center - 🔍 Busca em Notas Fiscais")
    
    with st.expander("ℹ️ Como usar", expanded=False):
        st.markdown("""
            **Selecione os arquivos de uma das formas:**
            1. Arraste uma pasta inteira para a área de upload
            2. Selecione múltiplos arquivos
            3. Combine as duas opções anteriores
            
            **Após selecionar:**
            1. Aguarde o processamento dos arquivos
            2. Digite o nome do produto que deseja buscar
            3. Clique em 'Buscar'
            4. Use os botões de download conforme necessário:
               - Download individual de cada nota
               - Download em ZIP de todas as notas encontradas
            
            **Tipos de arquivo suportados:**
            - PDFs (digitais ou escaneados)
            - XMLs de Nota Fiscal Eletrônica (NFe)
            
            **Dicas:**
            - Você pode arrastar uma pasta inteira do seu computador
            - Para selecionar múltiplos arquivos:
              - Windows: Ctrl + clique
              - Mac: Command + clique
            """)
    
    st.header("📁 Selecione os arquivos ou pasta")
    
    if st.button("🔄 Reiniciar"):
        reiniciar_sistema()
    
    if st.session_state.reiniciar_clicado:
        st.experimental_rerun()
        st.session_state.reiniciar_clicado = False
    
    arquivos = st.file_uploader(
        "Arraste uma pasta ou selecione os arquivos",
        type=['pdf', 'xml'],
        accept_multiple_files=True,
        help="Você pode arrastar uma pasta inteira ou selecionar arquivos individuais"
    )
    
    st.markdown("""
        <style>
        .download-button {
            display: inline-block;
            padding: 0.5rem 1rem;
            background-color: white !important;
            color: black !important;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s;
            border: 1px solid #ddd;
        }
        .download-button:hover {
            background-color: #f8f9fa !important;
        }
        .download-button-small {
            display: inline-block;
            padding: 0.3rem 0.7rem;
            background-color: white !important;
            color: black !important;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s;
            font-size: 0.9em;
            border: 1px solid #ddd;
        }
        .download-button-small:hover {
            background-color: #f8f9fa !important;
        }
        
        .stButton > button {
            background-color: white !important;
            color: black !important;
            border: 1px solid #ddd !important;
        }
        .stButton > button:hover {
            background-color: #f8f9fa !important;
            border: 1px solid #ddd !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
