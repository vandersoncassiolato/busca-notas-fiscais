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

def reiniciar_sistema():
    """
    Reinicia o sistema limpando a sessão
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# [Manter todas as funções anteriores: extrair_texto_xml, extrair_texto_pdf, etc.]

def main():
    st.title("Hiper Center - 🔍 Busca em Notas Fiscais")
    
    # Instruções de uso (agora fechado por padrão)
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
    
    # Área única de upload com botão reiniciar
    st.header("📁 Selecione os arquivos ou pasta")
    
    # Botão Reiniciar
    if st.button("🔄 Reiniciar", type="primary"):
        reiniciar_sistema()
        st.rerun()
    
    # CSS para os botões (agora branco com texto preto)
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
        
        /* Estilo para botões Streamlit padrão */
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
    
    # [Continuar com o resto do código existente...]

if __name__ == "__main__":
    main()
