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
    st.title("🔍 Busca em Notas Fiscais")
    st.write("Selecione suas notas fiscais e pesquise por produtos")
    
    # Upload de múltiplos arquivos
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
                
                for idx, row in resultados.iterrows():
                    with st.expander(f"📄 {row['arquivo']} ({row['tipo']})", expanded=True):
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
            1. Clique em 'Browse files' ou arraste os arquivos para a área indicada
            2. Você pode selecionar múltiplos arquivos de uma vez
            3. Aguarde o processamento dos arquivos
            4. Digite o nome do produto que deseja buscar
            5. Clique em 'Buscar'
            
            **Tipos de arquivo suportados:**
            - PDFs (digitais ou escaneados)
            - XMLs de Nota Fiscal Eletrônica (NFe)
            
            **Dicas:**
            - Você pode selecionar vários arquivos de uma vez
            - Para selecionar múltiplos arquivos:
              - Windows: Ctrl + clique
              - Mac: Command + clique
            - Você pode arrastar arquivos direto do Finder/Explorer
            """)

if __name__ == "__main__":
    main()
