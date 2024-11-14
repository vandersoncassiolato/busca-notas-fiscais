# [Manter imports anteriores]

def main():
    st.title("Hiper Center - 🔍 Busca em Notas Fiscais")
    
    # Instruções de uso
    with st.expander("ℹ️ Como usar", expanded=True):
        st.markdown("""
            **Selecione os arquivos de uma das formas:**
            1. Arraste uma pasta inteira para a área de upload
            2. Selecione múltiplos arquivos
            3. Combine as duas opções anteriores
            
            **Após selecionar:**
            1. Aguarde o processamento dos arquivos
            2. Digite o nome do produto que deseja buscar
            3. Clique em 'Buscar'
            4. Use o botão de download para baixar os arquivos encontrados
            
            **Tipos de arquivo suportados:**
            - PDFs (digitais ou escaneados)
            - XMLs de Nota Fiscal Eletrônica (NFe)
            
            **Dicas:**
            - Você pode arrastar uma pasta inteira do seu computador
            - Para selecionar múltiplos arquivos:
              - Windows: Ctrl + clique
              - Mac: Command + clique
            - O arquivo ZIP baixado conterá apenas as notas que contêm o produto buscado
            """)
    
    # Área única de upload
    st.header("📁 Selecione os arquivos ou pasta")
    
    arquivos = st.file_uploader(
        "Arraste uma pasta ou selecione os arquivos",
        type=['pdf', 'xml'],
        accept_multiple_files=True,
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
            # Agrupa por "pasta" (se houver estrutura de pastas no upload)
            arquivos_por_pasta = {}
            for arquivo in arquivos:
                pasta = os.path.dirname(arquivo.name)
                if pasta not in arquivos_por_pasta:
                    arquivos_por_pasta[pasta] = []
                arquivos_por_pasta[pasta].append(arquivo.name)
            
            # Mostra arquivos agrupados
            for pasta, arquivos_pasta in arquivos_por_pasta.items():
                if pasta:
                    st.write(f"📁 {pasta}")
                for arquivo in sorted(arquivos_pasta):
                    nome = os.path.basename(arquivo)
                    tipo = 'PDF' if nome.lower().endswith('.pdf') else 'XML'
                    st.write(f"{'   ' if pasta else ''}• {nome} ({tipo})")

        # [Resto do código continua igual]

# [Resto do código continua igual]
