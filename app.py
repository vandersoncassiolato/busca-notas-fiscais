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
