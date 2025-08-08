import pandas as pd
import os

def clean_text(text):
    """Remove caracteres problemáticos."""
    if pd.isna(text):
        return ""
    
    text = str(text)
    # Remove quebras de linha e tabs
    text = text.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
    # Remove múltiplos espaços
    text = ' '.join(text.split())
    # Limita o tamanho do texto
    if len(text) > 20:
        text = text[:17] + "..."
    
    return text

def format_dataframe_for_cli(df, display_map=None):
    """
    Formata um DataFrame para exibição no CLI com formatação ultra-simplificada.
    """
    if df.empty:
        return "\nNenhum registro para exibir.\n"
    
    try:
        # Pega apenas 3 colunas e máximo 15 linhas
        df_display = df.iloc[:15, :3].copy()
        
        # Limpa todas as células
        for col in df_display.columns:
            df_display[col] = df_display[col].apply(clean_text)
        
        # Trunca nomes das colunas
        df_display.columns = [str(col)[:12] for col in df_display.columns]
        
        # Cria tabela manualmente sem bibliotecas externas
        result = []
        
        # Cabeçalho
        header = " | ".join([f"{col:12}" for col in df_display.columns])
        result.append(header)
        result.append("-" * len(header))
        
        # Dados
        for _, row in df_display.iterrows():
            row_str = " | ".join([f"{str(val):12}" for val in row])
            result.append(row_str)
        
        return "\n".join(result)
        
    except Exception as e:
        # Fallback ainda mais simples
        try:
            result = []
            result.append(f"Registros: {len(df)}")
            result.append(f"Colunas: {len(df.columns)}")
            
            # Mostra apenas os primeiros valores da primeira coluna
            if len(df.columns) > 0:
                first_col = df.columns[0]
                result.append(f"\n{first_col}:")
                for i, val in enumerate(df[first_col].head(5)):
                    result.append(f"  {i+1}. {str(val)[:30]}")
            
            return "\n".join(result)
        except:
            return f"Total de registros: {len(df)}"
