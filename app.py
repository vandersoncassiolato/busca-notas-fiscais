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
import streamlit.components.v1 as components

# Configuração da página
st.set_page_config(
    page_title="Hiper Center - Busca em Notas Fiscais",
    page_icon="🔍",
    layout="wide"
)

# Inicializa variável de controle de reinicialização
if 'key' not in st.session_state:
    st.session_state.key = 0
if 'confirmar_reinicio' not in st.session_state:
    st.session_state.confirmar_reinicio = False

def reiniciar_sistema():
    st.session_state.clear()
    st.session_state.key = st.session_state.get('key', 0) + 1
    st.experimental_rerun()

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
    
    # Adiciona CSS para o popup
    st.markdown("""
        <style>
        .dialog-container {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
            z-index: 1000;
        }
        .dialog-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 999;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Botão Reiniciar com confirmação
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Reiniciar"):
            st.session_state.confirmar_reinicio = True
    
    # Mostra confirmação se o botão foi clicado
    if st.session_state.confirmar_reinicio:
        with col2:
            if st.button("⚠️ Clique para confirmar a reinicialização"):
                reiniciar_sistema()
            st.warning("Tem certeza? Todos os arquivos serão removidos.")

    # File uploader com key baseada na sessão
    arquivos = st.file_uploader(
        "Arraste uma pasta ou selecione os arquivos",
        type=['pdf', 'xml'],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.key}",
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
    if arquivos:
        # Mostra estatísticas dos arquivos selecionados
        pdfs = sum(1 for f in arquivos if f.name.lower().endswith('.pdf'))
        xmls = sum(1 for f in arquivos if f.name.lower().endswith('.xml'))
        st.success(f"✅ Selecionado(s): {len(arquivos)} arquivo(s)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📄 {pdfs} PDFs")
        with col2:
            st.info(f"📑 {xmls} XMLs")
        
        # Lista os arquivos selecionados
        with st.expander("📄 Arquivos selecionados", expanded=False):
            arquivos_por_pasta = {}
            for arquivo in arquivos:
                pasta = os.path.dirname(arquivo.name)
                if pasta not in arquivos_por_pasta:
                    arquivos_por_pasta[pasta] = []
                arquivos_por_pasta[pasta].append(arquivo.name)
            
            for pasta, arquivos_pasta in arquivos_por_pasta.items():
                if pasta:
                    st.write(f"📁 {pasta}")
                for arquivo in sorted(arquivos_pasta):
                    nome = os.path.basename(arquivo)
                    tipo = 'PDF' if nome.lower().endswith('.pdf') else 'XML'
                    st.write(f"{'   ' if pasta else ''}• {nome} ({tipo})")
        
        # Processamento dos arquivos
        if 'df_index' not in st.session_state or st.button("🔄 Reprocessar arquivos"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner('Processando arquivos...'):
                st.session_state.df_index = processar_arquivos(arquivos, progress_bar, status_text)
            
            progress_bar.empty()
            status_text.empty()
            
            st.success('✅ Processamento concluído!')
        
        # Interface de busca
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
            try:
                if 'df_index' not in st.session_state:
                    st.error("Por favor, faça o upload dos arquivos primeiro.")
                    return
                
                if 'conteudo' not in st.session_state.df_index.columns:
                    st.error("Erro na estrutura dos dados. Tente reprocessar os arquivos.")
                    return
                
                st.session_state.df_index['conteudo'] = st.session_state.df_index['conteudo'].fillna('')
                
                mascara = st.session_state.df_index['conteudo'].str.lower().str.contains(
                    termo_busca.lower(),
                    regex=False,
                    na=False
                )
                
                resultados = st.session_state.df_index[mascara]
                
                st.header("📋 Resultados")
                if len(resultados) == 0:
                    st.warning(f"Nenhuma nota fiscal encontrada com o produto '{termo_busca}'")
                else:
                    st.success(f"Encontrado em {len(resultados)} nota(s) fiscal(is)")
                    
                    arquivos_encontrados = resultados['arquivo'].tolist()
                    zip_buffer = criar_zip_resultado(arquivos_encontrados, arquivos)
                    
                    st.markdown("### 📥 Download dos Resultados")
                    st.markdown(
                        get_download_link(
                            zip_buffer,
                            f"notas_fiscais_{termo_busca.replace(' ', '_')}.zip"
                        ),
                        unsafe_allow_html=True
                    )
                    
                    for idx, row in resultados.iterrows():
                        with st.expander(f"📄 {row['arquivo']} ({row['tipo']})", expanded=True):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.write("Trechos relevantes:")
                                texto = row['conteudo'].lower()
                                posicao = texto.find(termo_busca.lower())
                                inicio = max(0, posicao - 100)
                                fim = min(len(texto), posicao + 100)
                                contexto = "..." + texto[inicio:fim] + "..."
                                st.markdown(f"*{contexto}*")
                            
                            with col2:
                                arquivo_original = next(
                                    (arq for arq in arquivos if arq.name == row['arquivo']),
                                    None
                                )
                                if arquivo_original:
                                    st.markdown(
                                        get_individual_download_link(arquivo_original, row['arquivo']),
                                        unsafe_allow_html=True
                                    )
            
            except Exception as e:
                st.error(f"Erro durante a busca: {str(e)}")
                st.info("Tente reprocessar os arquivos clicando em 'Reprocessar arquivos'")

if __name__ == "__main__":
    main()
    
