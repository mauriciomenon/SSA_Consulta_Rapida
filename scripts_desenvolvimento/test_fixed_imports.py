import os
import json
from extracao.extractor import extract_data_from_excel
from armazenamento.database import Database

def test_specific_files():
    """Testa os arquivos que estavam dando erro"""
    
    # Arquivos que sabemos que estavam problemáticos
    problem_files = [
        "docs_entrada/Em Execução_15-08-2025_0416PM.xlsx",
        "docs_entrada/Em Execução_15-08-2025_0417PM.xlsx", 
        "docs_entrada/SSAs Pendentes com Execução Parcial_15-08-2025_0416PM.xlsx",
        "docs_entrada/Não Planejadas em Espera_15-08-2025_0410PM.xlsx"
    ]
    
    print("🔍 Testando arquivos que anteriormente falhavam...")
    print("=" * 50)
    
    for file_path in problem_files:
        if os.path.exists(file_path):
            print(f"\n📁 Testando: {os.path.basename(file_path)}")
            try:
                # Tentar processar o arquivo
                df = extract_data_from_excel(file_path)
                
                if df is not None and len(df) > 0:
                    print(f"   ✅ SUCESSO - {len(df)} registros processados")
                    
                    # Verificar se tem as colunas problemáticas
                    problem_columns = ['registros_espera', 'numero_desvios', 'total_tempo_tex_executada', 'parciais', 'num_reprobaciones']
                    
                    found_columns = []
                    for col in problem_columns:
                        if col in df.columns:
                            non_null_count = df[col].notna().sum()
                            if non_null_count > 0:
                                found_columns.append(f"{col}({non_null_count})")
                    
                    if found_columns:
                        print(f"   📊 Colunas especiais encontradas: {', '.join(found_columns)}")
                    
                    print(f"   📋 Colunas disponíveis: {list(df.columns)[:5]}..." if len(df.columns) > 5 else f"   📋 Colunas: {list(df.columns)}")
                    
                else:
                    print("   ⚠️  Processado mas sem dados")
                    
            except Exception as e:
                print(f"   ❌ ERRO: {str(e)}")
        else:
            print(f"\n📁 {os.path.basename(file_path)} - ❌ Arquivo não encontrado")
    
    print("\n" + "=" * 50)
    print("✅ Teste concluído!")

if __name__ == "__main__":
    test_specific_files()
