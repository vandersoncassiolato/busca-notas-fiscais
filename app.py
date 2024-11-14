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
import requests
import re
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Busca em Notas Fiscais",
    page_icon="🔍",
    layout="wide"
)

def extrair_id_pasta_drive(url):
    """
    Extrai o ID da pasta do Google Drive a partir da URL
    """
    padrao = r"folders/([a-zA-Z0-9-_]+)"
    match = re.search(padrao, url)
    if match:
        return match.group(1)
    return None

def obter_arquivos_pasta(pasta_id):
    """
    Lista arquivos de uma pasta compartilhada do Google Drive
    """
    url = f"https://drive.google.com/drive/folders/{pasta_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Aqui você precisaria implementar a lógica para extrair os links dos arquivos
            # Como o Google Drive não permite listagem direta, você precisaria de uma lista
            # de IDs dos arquivos ou links diretos
            pass
    except Exception as e:
        st.error(f"Erro ao acessar pasta: {str(e)}")
        return []

def baixar_arquivo_drive(file_id):
    """
    Baixa um arquivo do Google Drive usando link direto
    """
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception as e:
        st.error(f"Erro ao baixar arquivo: {str(e)}")
        return None

def extrair_texto_xml(arquivo):
    """
    Extrai informações relevantes de arquivos XML de NFe
    """
    try:
        conteudo = arquivo.read()
        tree = ET.ElementTree(ET.fromstring(conteudo))
        root = tree.getroot()
        
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

def processar_links(links_text):
    """
    Processa os links colados pelo usuário e extrai os IDs dos arquivos
    """
    links = links_text.split('\n')
    arquivos = []
    
    for link in links:
        link = link.strip()
        if not link:
            continue
            
        # Extrai ID do arquivo do link do Drive
        file_id_match = re.search(r"[-\w]{25,}", link)
        if file_id_match:
            file_id = file_id_match.group(0)
            tipo = 'PDF' if link.lower().endswith('.pdf') else 'XML' if link.lower().endswith('.xml') else None
            
            if tipo:
                arquivos.append({
                    'id': file_id,
                    'tipo': tipo,
                    'link': link
                })
    
    return arquivos

def main():
    st.title("🔍 Busca em Notas Fiscais")
    st.write("Cole os links dos arquivos do Google Drive e pesquise por produtos")
    
    # Área de input dos links
    st.header("📁 Links dos Arquivos")
    links_text = st.text_area(
        "Cole os links dos arquivos (um por linha)",
        help="Os links devem ser públicos ou compartilhados com acesso",
        height=150
    )
    
    if links_text:
        arquivos = processar_links(links_text)
        
        if arquivos:
            st.success(f"✅ Encontrados {len(arquivos)} arquivo(s) válido(s)")
            
            # Processamento dos arquivos
            if 'df_index' not in st.session_state:
                with st.spinner('Processando arquivos...'):
                    index = []
                    for arquivo in arquivos:
                        with st.spinner(f'Processando arquivo {arquivo["id"]}...'):
                            conteudo = baixar_arquivo_drive(arquivo['id'])
                            if conteudo:
                                if arquivo['tipo'] == 'PDF':
                                    texto = extrair_texto_pdf(conteudo)
                                else:
                                    texto = extrair_texto_xml(conteudo)
                                
                                index.append({
                                    'arquivo': arquivo['id'],
                                    'tipo': arquivo['tipo'],
                                    'link': arquivo['link'],
                                    'conteudo': texto
                                })
                    
                    st.session_state.df_index = pd.DataFrame(index)
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
                        with st.expander(f"📄 Arquivo {row['tipo']}", expanded=True):
                            st.write("Link do arquivo:")
                            st.markdown(f"[Abrir no Drive]({row['link']})")
                            
                            st.write("Trechos relevantes:")
                            texto = row['conteudo'].lower()
                            posicao = texto.find(termo_busca.lower())
                            inicio = max(0, posicao - 100)
                            fim = min(len(texto), posicao + 100)
                            contexto = "..." + texto[inicio:fim] + "..."
                            st.markdown(f"*{contexto}*")
        
        else:
            st.warning("Nenhum link válido encontrado")
    
    # Instruções de uso
    with st.expander("ℹ️ Como usar"):
        st.markdown("""
            1. No Google Drive, clique com botão direito em cada arquivo
            2. Selecione "Obter link"
            3. Configure o acesso como "Qualquer pessoa com o link"
            4. Cole os links aqui (um por linha)
            5. Aguarde o processamento
            6. Digite o nome do produto que deseja buscar
            7. Clique em 'Buscar'
            
            **Importante:**
            - Os arquivos precisam estar compartilhados com acesso "Qualquer pessoa com o link"
            - São aceitos arquivos PDF e XML
            - O link deve terminar com .pdf ou .xml
            - O processamento pode demorar alguns minutos
        """)

if __name__ == "__main__":
    main()
