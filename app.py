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
import glob

# Configuração da página
st.set_page_config(
    page_title="Hiper Center - Busca em Notas Fiscais",
    page_icon="🔍",
    layout="wide"
)

def processar_pasta_local(caminho_pasta):
    """
    Lista todos os arquivos PDF e XML em uma pasta
    """
    arquivos = []
    try:
        # Procura por PDFs
        pdfs = glob.glob(os.path.join(caminho_pasta, "**/*.pdf"), recursive=True)
        # Procura por XMLs
        xmls = glob.glob(os.path.join(caminho_pasta, "**/*.xml"), recursive=True)
        
        # Processa PDFs encontrados
        for pdf_path in pdfs:
            with open(pdf_path, 'rb') as f:
                arquivo = io.BytesIO(f.read())
                arquivo.name = os.path.basename(pdf_path)
                arquivos.append(arquivo)
        
        # Processa XMLs encontrados
        for xml_path in xmls:
            with open(xml_path, 'rb') as f:
                arquivo = io.BytesIO(f.read())
                arquivo.name = os.path.basename(xml_path)
                arquivos.append(arquivo)
                
        return arquivos
    except Exception as e:
        st.error(f"Erro ao processar pasta: {str(e)}")
        return []

# [Manter as funções anteriores: extrair_texto_xml, extrair_texto_pdf, criar_zip_resultado, get_download_link]

def processar_arquivos(arquivos_uploaded):
    """
    Processa os arquivos carregados
    """
    index = []
    
    for arquivo in arquivos_uploaded:
        with st.spinner(f'Processando {arquivo.name}...'):
            try:
                # Determina o tipo do arquivo
                tipo = 'PDF' if arquivo.name.lower().endswith('.pdf') else 'XML'
                
                # Processa o arquivo de acordo com seu tipo
                if tipo == 'PDF':
                    texto = extrair_texto_pdf(arquivo)
                else:
                    texto = extrair_texto_xml(arquivo.getvalue())
                
                index.append({
                    'arquivo': arquivo.name,
                    'tipo': tipo,
                    'conteudo': texto
                })
            except Exception as e:
                st.warning(f"Erro ao processar {arquivo.name}: {str(e)}")
                continue
    
    return pd.DataFrame(index)

def main():
    st.title("Hiper Center - 🔍 Busca em Notas Fiscais")
    
    # Instruções de uso (movido para o início)
    with st.expander("ℹ️ Como usar", expanded=True):
        st.markdown("""
            **Opção 1 - Selecionar pasta:**
            1. Digite o caminho completo da pasta que contém suas notas fiscais
            2. Todos os PDFs e XMLs da pasta serão processados automaticamente
            
            **Opção 2 - Selecionar arquivos:**
            1. Clique em 'Browse files' ou arraste os arquivos para a área indicada
            2. Você pode selecionar múltiplos arquivos de uma vez
            
            **Após selecionar os arquivos:**
            1. Aguarde o processamento dos arquivos
            2. Digite o nome do produto que deseja buscar
            3. Clique em 'Buscar'
            4. Use o botão de download para baixar os arquivos encontrados
            
            **Tipos de arquivo suportados:**
            - PDFs (digitais ou escaneados)
            - XMLs de Nota Fiscal Eletrônica (NFe)
            
            **Dicas:**
            - Para selecionar múltiplos arquivos:
              - Windows: Ctrl + clique
              - Mac: Command + clique
            - O arquivo ZIP baixado conterá apenas as notas que contêm o produto buscado
            """)
    
    # Opções de seleção de arquivos
    st.header("📁 Selecione os arquivos")
    
    metodo = st.radio(
        "Como você quer selecionar os arquivos?",
        ["Selecionar pasta", "Selecionar arquivos individuais"]
    )
    
    arquivos = []
    
    if metodo == "Selecionar pasta":
        caminho_pasta = st.text_input(
            "Digite o caminho da pasta",
            placeholder="Ex: C:/Notas ou /Users/seu_usuario/Notas"
        )
        
        if caminho_pasta and os.path.isdir(caminho_pasta):
            arquivos = processar_pasta_local(caminho_pasta)
            if not arquivos:
                st.warning("Nenhum arquivo PDF ou XML encontrado na pasta")
    else:
        arquivos = st.file_uploader(
            "Selecione os arquivos PDF e XML",
            type=['pdf', 'xml'],
            accept_multiple_files=True,
            help="Você pode selecionar múltiplos arquivos de uma vez"
        )
    
    if arquivos:
        # Mostra estatísticas dos arquivos selecionados
        pdfs = sum(1 for f in arquivos if f.name.lower().endswith('.pdf'))
        xmls = sum(1 for f in arquivos if f.name.lower().endswith('.xml'))
        st.success(f"✅ Selecionado(s): {len(arquivos)} arquivo(s)")
        st.write(f"- {pdfs} PDFs\n- {xmls} XMLs")
        
        # Lista os arquivos selecionados
        with st.expander("📄 Arquivos selecionados", expanded=False):
            for arquivo in arquivos:
                tipo = 'PDF' if arquivo.name.lower().endswith('.pdf') else 'XML'
                st.write(f"- {arquivo.name} ({tipo})")
        
        # Processamento dos arquivos
        if 'df_index' not in st.session_state or st.button("🔄 Reprocessar arquivos"):
            with st.spinner('Processando arquivos...'):
                st.session_state.df_index = processar_arquivos(arquivos)
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
            mascara = st.session_state.df_index['conteudo'].str.lower().str.contains(
                termo_busca.lower(),
                regex=False
            )
            resultados = st.session_state.df_index[mascara]
            
            st.header("📋 Resultados")
            if len(resultados) == 0:
                st.warning(f"Nenhuma nota fiscal encontrada com o produto '{termo_busca}'")
            else:
                st.success(f"Encontrado em {len(resultados)} nota(s) fiscal(is)")
                
                # Criar ZIP com os resultados
                arquivos_encontrados = resultados['arquivo'].tolist()
                zip_buffer = criar_zip_resultado(arquivos_encontrados, arquivos)
                
                # Botão de download
                st.markdown("### 📥 Download dos Resultados")
                st.markdown(
                    get_download_link(
                        zip_buffer,
                        f"notas_fiscais_{termo_busca.replace(' ', '_')}.zip"
                    ),
                    unsafe_allow_html=True
                )
                
                # Mostra os resultados
                for idx, row in resultados.iterrows():
                    with st.expander(f"📄 {row['arquivo']} ({row['tipo']})", expanded=True):
                        st.write("Trechos relevantes:")
                        texto = row['conteudo'].lower()
                        posicao = texto.find(termo_busca.lower())
                        inicio = max(0, posicao - 100)
                        fim = min(len(texto), posicao + 100)
                        contexto = "..." + texto[inicio:fim] + "..."
                        st.markdown(f"*{contexto}*")

if __name__ == "__main__":
    main()
