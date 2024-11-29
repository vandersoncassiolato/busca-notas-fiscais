# Parte 1: Imports e configurações iniciais
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
    page_title="Hiper Materiais - Busca em Notas Fiscais",
    page_icon="🔍",
    layout="wide"
)

# Inicializa variável de controle de reinicialização
if 'key' not in st.session_state:
    st.session_state.key = 0
if 'mostrar_confirmacao' not in st.session_state:
    st.session_state.mostrar_confirmacao = False

# Função de utilidade para normalizar CNPJ
def normalizar_cnpj(cnpj):
    """
    Remove caracteres especiais do CNPJ
    """
    if cnpj:
        return ''.join(filter(str.isdigit, cnpj))
    return ''

# Funções de controle do sistema
def reiniciar_sistema():
    """
    Reinicia o sistema limpando a sessão
    """
    st.session_state.key += 1
    st.session_state.mostrar_confirmacao = False
    for key in list(st.session_state.keys()):
        if key not in ['key', 'mostrar_confirmacao']:
            del st.session_state[key]

def toggle_confirmacao():
    st.session_state.mostrar_confirmacao = True

def cancelar_reinicio():
    st.session_state.mostrar_confirmacao = False

def get_theme_colors():
    """
    Retorna as cores baseadas no tema atual do Streamlit
    """
    try:
        # Tenta pegar o tema atual de forma mais segura
        if st._config.get_option("theme.base") == "dark":
            return {
                'button_bg': '#2E2E2E',
                'button_text': '#FFFFFF',
                'button_border': '#404040',
                'button_hover': '#3E3E3E',
            }
        else:
            return {
                'button_bg': '#FFFFFF',
                'button_text': '#000000',
                'button_border': '#DDDDDD',
                'button_hover': '#F8F9FA',
            }
    except:
        # Fallback para cores claras em caso de erro
        return {
            'button_bg': '#FFFFFF',
            'button_text': '#000000',
            'button_border': '#DDDDDD',
            'button_hover': '#F8F9FA',
        }
def extrair_texto_xml(conteudo):
    """
    Extrai informações relevantes de arquivos XML de NFe
    """
    try:
        root = ET.fromstring(conteudo)
        
        # Define o namespace padrão da NFe
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Lista para armazenar todas as informações
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
                cnpj_formatado = f"{cnpj_emit.text}"  # CNPJ sem formatação
                cnpj_com_formato = f"{cnpj_emit.text[:2]}.{cnpj_emit.text[2:5]}.{cnpj_emit.text[5:8]}/{cnpj_emit.text[8:12]}-{cnpj_emit.text[12:]}"  # CNPJ formatado
                info.append(f"CNPJ Emitente: {cnpj_formatado}")
                info.append(f"CNPJ Emitente Formatado: {cnpj_com_formato}")
        
        # Dados do destinatário
        dest = root.find('.//nfe:dest', ns)
        if dest is not None:
            nome_dest = dest.find('nfe:xNome', ns)
            cnpj_dest = dest.find('nfe:CNPJ', ns)
            if nome_dest is not None:
                info.append(f"Destinatário: {nome_dest.text}")
            if cnpj_dest is not None:
                cnpj_formatado = f"{cnpj_dest.text}"  # CNPJ sem formatação
                cnpj_com_formato = f"{cnpj_dest.text[:2]}.{cnpj_dest.text[2:5]}.{cnpj_dest.text[5:8]}/{cnpj_dest.text[8:12]}-{cnpj_dest.text[12:]}"  # CNPJ formatado
                info.append(f"CNPJ Destinatário: {cnpj_formatado}")
                info.append(f"CNPJ Destinatário Formatado: {cnpj_com_formato}")
        
        # Dados dos produtos
        produtos = root.findall('.//nfe:det', ns)
        for prod in produtos:
            prod_info = prod.find('nfe:prod', ns)
            if prod_info is not None:
                codigo = prod_info.find('nfe:cProd', ns)
                descricao = prod_info.find('nfe:xProd', ns)
                ncm = prod_info.find('nfe:NCM', ns)
                quantidade = prod_info.find('nfe:qCom', ns)
                valor = prod_info.find('nfe:vUnCom', ns)
                
                prod_text = []
                if codigo is not None:
                    prod_text.append(f"Código: {codigo.text}")
                if descricao is not None:
                    prod_text.append(f"Produto: {descricao.text}")
                if ncm is not None:
                    prod_text.append(f"NCM: {ncm.text}")
                if quantidade is not None:
                    prod_text.append(f"Qtd: {quantidade.text}")
                if valor is not None:
                    prod_text.append(f"Valor: {valor.text}")
                    
                info.append(" | ".join(prod_text))
        
        # Adiciona valores totais
        total = root.find('.//nfe:ICMSTot', ns)
        if total is not None:
            vnf = total.find('nfe:vNF', ns)
            if vnf is not None:
                info.append(f"Valor Total NF: {vnf.text}")
        
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
    st.title("Hiper Materiais - 🔍 Busca em Notas Fiscais")

    st.markdown("""
        <style>
        /* Reduz o espaço superior */
        .block-container {
            padding-top: 2rem !important;
        }
        /* Esconde os ícones do topo direito */
        section[data-testid="stSidebar"] > div {
            display: none;
        }

        /* Esconde o menu superior direito completo */
        .menu {
            display: none !important;
        }

        /* Esconde os botões de ação no topo */
        .stActionButton, .stDeployButton {
            display: none !important;
        }

        /* Esconde o Manage app no rodapé */
        footer {
            display: none !important;
        }

        /* Remove a barra de ferramentas superior */
        .stToolbar {
            display: none !important;
        }

        /* Esconde elementos específicos do header */
        [data-testid="stHeader"] {
            display: none !important;
        }

        /* Esconde todos os controles da interface do Streamlit */
        .main .block-container div[data-testid="stDecoration"] {
            display: none !important;
        }

        /* Remove os ícones de GitHub e outros */
        .st-emotion-cache-1dp5vir {
            display: none !important;
        }

        /* Remove elementos do rodapé */
        .st-emotion-cache-h5rgaw {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.expander("ℹ️ Como usar", expanded=False):
        st.markdown("""
            **Selecione os arquivos de uma das formas:**
            1. Arraste uma pasta inteira para a área de upload
            2. Selecione múltiplos arquivos
            
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
            """)
    
    # CSS global
    colors = get_theme_colors()
    st.markdown(f"""
        <style>
        .download-button {{
            display: inline-block;
            padding: 0.5rem 1rem;
            background-color: {colors['button_bg']} !important;
            color: {colors['button_text']} !important;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s;
            border: 1px solid {colors['button_border']};
        }}
        .download-button:hover {{
            background-color: {colors['button_hover']} !important;
        }}
        .download-button-small {{
            display: inline-block;
            padding: 0.3rem 0.7rem;
            background-color: {colors['button_bg']} !important;
            color: {colors['button_text']} !important;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s;
            font-size: 0.9em;
            border: 1px solid {colors['button_border']};
        }}
        .download-button-small:hover {{
            background-color: {colors['button_hover']} !important;
        }}
        
        .stButton > button {{
            background-color: {colors['button_bg']} !important;
            color: {colors['button_text']} !important;
            border: 1px solid {colors['button_border']} !important;
        }}
        .stButton > button:hover {{
            background-color: {colors['button_hover']} !important;
        }}
        
        div[data-testid="column"] {{
            display: flex;
            align-items: flex-start;
            padding-top: 1px;
        }}
        
        div[data-testid="column"] > div {{
            width: 100%;
        }}
        
        div.stButton > button {{
            margin-top: 1px;
            height: 45px;
        }}
        </style>
    """, unsafe_allow_html=True)
    # Botões de reiniciar
    col1, col2 = st.columns([1, 5])
    with col1:
        st.button("🔄 Reiniciar", on_click=toggle_confirmacao)
    
    with col2:
        if st.session_state.mostrar_confirmacao:
            st.warning("⚠️ Deseja realmente reiniciar?")
            col_conf1, col_conf2, col_conf3 = st.columns([1, 1, 3])
            with col_conf1:
                if st.button("Confirmar", type="primary"):
                    reiniciar_sistema()
                    st.rerun()
            with col_conf2:
                st.button("Cancelar", on_click=cancelar_reinicio)

    st.header("📁 Selecione os arquivos ou pasta")
    
    arquivos = st.file_uploader(
        "Arraste uma pasta ou selecione os arquivos",
        type=['pdf', 'xml'],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.key}",
        help="Você pode arrastar uma pasta inteira ou selecionar arquivos individuais"
    )
    
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
        
        # CSS para alinhamento do botão
        st.markdown("""
            <style>
            div[data-testid="column"] {
                display: flex;
                align-items: flex-start;
                padding-top: 1px;
            }
            
            div[data-testid="column"] > div {
                width: 100%;
            }
            
            div.stButton > button {
                margin-top: 1px;
                height: 30px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        search_col1, search_col2 = st.columns([5, 1])
        
        with search_col1:
            termo_busca = st.text_input(
                "Digite o nome do produto",
                placeholder="Ex: Fechadura, Parafuso, etc.",
                label_visibility="collapsed",
                key="search_input",
                on_change=lambda: st.session_state.update({'search_triggered': True})
            )
        
        with search_col2:
            buscar = st.button("Buscar", use_container_width=True)

        # Realizar busca
        if (termo_busca and st.session_state.get('search_triggered', False)) or buscar:
            st.session_state.search_triggered = False  # Reset do trigger
            try:
                if 'df_index' not in st.session_state:
                    st.error("Por favor, faça o upload dos arquivos primeiro.")
                    return
                
                if 'conteudo' not in st.session_state.df_index.columns:
                    st.error("Erro na estrutura dos dados. Tente reprocessar os arquivos.")
                    return
                
                # Normaliza o termo de busca se parecer um CNPJ
                termo_busca_normalizado = ''.join(filter(str.isdigit, termo_busca))

                st.session_state.df_index['conteudo'] = st.session_state.df_index['conteudo'].fillna('')

                # Busca modificada para diferentes tipos de conteúdo
                if termo_busca_normalizado and len(termo_busca_normalizado) > 6:  # Se parece ser um CNPJ ou NCM
                    # Busca com regex para CNPJ (formatado ou não) e NCM
                    padrao_busca = f"({termo_busca}|{termo_busca_normalizado})"
                    mascara = st.session_state.df_index['conteudo'].str.lower().str.contains(
                        padrao_busca,
                        regex=True,
                        na=False
                    )
                else:  # Busca normal por texto
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
