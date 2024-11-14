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

# Configuração da página
st.set_page_config(
    page_title="Busca em Notas Fiscais",
    page_icon="🔍",
    layout="wide"
)

# [Mantenha as funções extrair_texto_xml e extrair_texto_pdf como estavam]

def processar_pasta(caminho_pasta):
    """
    Processa todos os arquivos PDF e XML de uma pasta
    """
    try:
        # Normaliza o caminho para o formato do sistema
        caminho_pasta = os.path.expanduser(caminho_pasta)
        pasta = Path(caminho_pasta)
        
        if not pasta.exists():
            st.error(f"Pasta não encontrada: {caminho_pasta}")
            st.info("Verifique se o caminho está correto e se você tem permissão de acesso.")
            return []
            
        arquivos = []
        # Lista todos os arquivos PDF e XML na pasta
        for arquivo in pasta.glob('*.*'):
            if arquivo.suffix.lower() in ['.pdf', '.xml']:
                arquivos.append({
                    'caminho': str(arquivo),
                    'nome': arquivo.name,
                    'tipo': 'PDF' if arquivo.suffix.lower() == '.pdf' else 'XML'
                })
                
        return arquivos
    except Exception as e:
        st.error(f"Erro ao processar pasta: {str(e)}")
        return []

def criar_indice(arquivos):
    """
    Cria um índice de todos os arquivos e seus conteúdos
    """
    index = []
    
    for arquivo in arquivos:
        with st.spinner(f'Processando {arquivo["nome"]}...'):
            try:
                if arquivo['tipo'] == 'PDF':
                    texto = extrair_texto_pdf(arquivo['caminho'])
                else:
                    texto = extrair_texto_xml(arquivo['caminho'])
                    
                index.append({
                    'arquivo': arquivo['nome'],
                    'tipo': arquivo['tipo'],
                    'caminho': arquivo['caminho'],
                    'conteudo': texto
                })
            except Exception as e:
                st.warning(f"Erro ao processar {arquivo['nome']}: {str(e)}")
                continue
    
    return pd.DataFrame(index)

def main():
    st.title("🔍 Busca em Notas Fiscais")
    st.write("Selecione a pasta com suas notas fiscais e pesquise por produtos")
    
    # Input da pasta com exemplos específicos para Mac
    st.write("💡 **Dicas para o caminho da pasta:**")
    col1, col2 = st.columns(2)
    with col1:
        st.code("/Users/seunome/Downloads/notas")
        st.caption("Exemplo de caminho completo")
    with col2:
        st.code("~/Downloads/notas")
        st.caption("Usando ~ para pasta do usuário")
    
    caminho_pasta = st.text_input(
        "Caminho da pasta com as notas fiscais",
        value="~/Downloads/notas",
        help="Digite o caminho completo da pasta onde estão os arquivos PDF e XML"
    )
    
    if caminho_pasta:
        # Expande o ~ para o caminho completo do usuário
        caminho_expandido = os.path.expanduser(caminho_pasta)
        st.caption(f"Procurando em: {caminho_expandido}")
        
        # Processa a pasta
        arquivos = processar_pasta(caminho_pasta)
        
        if arquivos:
            st.success(f"✅ Encontrados {len(arquivos)} arquivo(s)")
            
            # Mostra estatísticas
            pdfs = sum(1 for f in arquivos if f['tipo'] == 'PDF')
            xmls = sum(1 for f in arquivos if f['tipo'] == 'XML')
            st.write(f"- {pdfs} PDFs\n- {xmls} XMLs")
            
            # Lista os arquivos encontrados
            with st.expander("📄 Arquivos encontrados", expanded=False):
                for arq in arquivos:
                    st.write(f"- {arq['nome']} ({arq['tipo']})")
            
            # Processamento dos arquivos
            if 'df_index' not in st.session_state or st.button("🔄 Reprocessar arquivos"):
                with st.spinner('Processando arquivos...'):
                    st.session_state.df_index = criar_indice(arquivos)
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
                    
                    for idx, row in resultados.iterrows():
                        with st.expander(f"📄 {row['arquivo']} ({row['tipo']})", expanded=True):
                            st.write("Caminho do arquivo:")
                            st.code(row['caminho'])
                            
                            st.write("Trechos relevantes:")
                            texto = row['conteudo'].lower()
                            posicao = texto.find(termo_busca.lower())
                            inicio = max(0, posicao - 100)
                            fim = min(len(texto), posicao + 100)
                            contexto = "..." + texto[inicio:fim] + "..."
                            st.markdown(f"*{contexto}*")
    
    # Instruções de uso
    with st.expander("ℹ️ Como usar"):
        st.markdown("""
            1. Digite o caminho da pasta onde estão suas notas fiscais
               - Use `/Users/seunome/pasta` para caminho completo
               - Ou use `~/pasta` como atalho para sua pasta de usuário
            2. Aguarde o processamento dos arquivos
            3. Digite o nome do produto que deseja buscar
            4. Clique em 'Buscar'
            
            **Dicas para Mac:**
            - Para descobrir o caminho de uma pasta:
              1. Abra o Finder e navegue até a pasta
              2. Clique com botão direito na pasta
              3. Pressione tecla Option (⌥)
              4. Selecione "Copiar como caminho"
            
            **Importante:**
            - A pasta deve conter arquivos PDF e/ou XML
            - O sistema processa automaticamente todos os arquivos da pasta
            - Para PDFs escaneados, o processo pode ser mais lento
        """)

if __name__ == "__main__":
    main()
