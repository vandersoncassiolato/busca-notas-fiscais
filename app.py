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

def extrair_texto_xml(arquivo):
    """
    Extrai informações relevantes de arquivos XML de NFe
    """
    try:
        tree = ET.parse(arquivo)
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
            imagens = pdf2image.convert_from_path(arquivo)
            texto = ""
            for imagem in imagens:
                texto += pytesseract.image_to_string(imagem, lang='por')
                
        return texto
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return ""

def processar_pasta(caminho_pasta):
    """
    Processa todos os arquivos PDF e XML de uma pasta
    """
    arquivos = []
    
    # Converte o caminho para objeto Path
    pasta = Path(caminho_pasta)
    
    # Lista todos os arquivos PDF e XML na pasta
    for arquivo in pasta.glob('*.*'):
        if arquivo.suffix.lower() in ['.pdf', '.xml']:
            arquivos.append({
                'caminho': str(arquivo),
                'nome': arquivo.name,
                'tipo': 'PDF' if arquivo.suffix.lower() == '.pdf' else 'XML'
            })
    
    return arquivos

def criar_indice(arquivos):
    """
    Cria um índice de todos os arquivos e seus conteúdos
    """
    index = []
    
    for arquivo in arquivos:
        with st.spinner(f'Processando {arquivo["nome"]}...'):
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
    
    return pd.DataFrame(index)

def main():
    st.title("🔍 Busca em Notas Fiscais")
    st.write("Selecione a pasta com suas notas fiscais e pesquise por produtos")
    
    # Input da pasta
    caminho_pasta = st.text_input(
        "Caminho da pasta com as notas fiscais",
        placeholder="Ex: C:/Users/Seu_Usuario/Documentos/Notas_Fiscais",
        help="Digite o caminho completo da pasta onde estão os arquivos PDF e XML"
    )
    
    if caminho_pasta and os.path.isdir(caminho_pasta):
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
            if 'df_index' not in st.session_state:
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
        
        else:
            st.warning("Nenhum arquivo PDF ou XML encontrado na pasta")
    elif caminho_pasta:
        st.error("Pasta não encontrada. Verifique o caminho e tente novamente.")
    
    # Instruções de uso
    with st.expander("ℹ️ Como usar"):
        st.markdown("""
            1. Digite o caminho completo da pasta onde estão suas notas fiscais
               - Exemplo Windows: C:/Users/Seu_Usuario/Documentos/Notas_Fiscais
               - Exemplo Linux/Mac: /home/seu_usuario/documentos/notas_fiscais
            2. Aguarde o processamento dos arquivos
            3. Digite o nome do produto que deseja buscar
            4. Clique em 'Buscar'
            
            **Importante:**
            - A pasta deve conter arquivos PDF e/ou XML
            - O sistema processa automaticamente todos os arquivos da pasta
            - Para PDFs escaneados, o processo pode ser mais lento
        """)

if __name__ == "__main__":
    main()
