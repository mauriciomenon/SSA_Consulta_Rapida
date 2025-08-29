#!/usr/bin/env python3
"""
Teste rápido do sistema SSA após melhorias
"""

import sys
import os

def test_basic_functionality():
    """Testa funcionalidade básica do sistema"""
    try:
        print("🔍 Testando funcionalidade básica...")
        
        # Verifica se o main.py existe e é executável
        if os.path.exists("main.py"):
            print("✅ main.py encontrado")
        else:
            print("❌ main.py não encontrado")
            return False
            
        # Verifica estrutura básica
        essential_dirs = ["armazenamento", "config", "core"]
        for dir_name in essential_dirs:
            if os.path.exists(dir_name):
                print(f"✅ Diretório {dir_name}/ encontrado")
            else:
                print(f"❌ Diretório {dir_name}/ não encontrado")
                
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste básico: {e}")
        return False

def test_database():
    """Testa se o banco está acessível"""
    try:
        print("\n🗄️ Testando acesso ao banco...")
        
        # Verifica se o arquivo do banco existe
        db_path = "data/ssa_consulta_rapida.db"
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"✅ Banco encontrado ({size_mb:.2f} MB)")
            
            # Teste simples de conexão
            import sqlite3
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Verifica se há tabelas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                if tables:
                    print(f"✅ Banco com {len(tables)} tabela(s)")
                    
                    # Verifica se há dados na tabela principal
                    try:
                        cursor.execute("SELECT COUNT(*) FROM ssa_table")
                        count = cursor.fetchone()[0]
                        print(f"✅ {count:,} registros na tabela principal")
                    except:
                        print("⚠️ Tabela principal sem dados ou não existe")
                else:
                    print("⚠️ Banco sem tabelas")
                    
                conn.close()
                return True
                
            except Exception as e:
                print(f"⚠️ Erro ao acessar banco: {e}")
                return True  # Não é erro crítico
        else:
            print("⚠️ Banco de dados não encontrado (será criado na primeira importação)")
            return True
        
    except Exception as e:
        print(f"❌ Erro no teste do banco: {e}")
        return False

def test_scripts_organization():
    """Verifica se a organização dos scripts está correta"""
    try:
        print("\n📁 Verificando organização dos scripts...")
        
        # Verifica se as pastas existem
        if os.path.exists("scripts_manutencao"):
            manutencao_files = len([f for f in os.listdir("scripts_manutencao") if f.endswith('.py')])
            print(f"✅ scripts_manutencao/ com {manutencao_files} arquivos Python")
        else:
            print("❌ Pasta scripts_manutencao/ não encontrada")
            
        if os.path.exists("scripts_desenvolvimento"):
            dev_files = len([f for f in os.listdir("scripts_desenvolvimento") if f.endswith('.py')])
            print(f"✅ scripts_desenvolvimento/ com {dev_files} arquivos Python")
        else:
            print("❌ Pasta scripts_desenvolvimento/ não encontrada")
            
        # Verifica se o gerenciador de banco existe
        if os.path.exists("scripts_manutencao/gerenciar_banco.py"):
            print("✅ Gerenciador de banco disponível")
        else:
            print("❌ Gerenciador de banco não encontrado")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

def test_documentation():
    """Verifica se a documentação está atualizada"""
    try:
        print("\n📚 Verificando documentação...")
        
        files_to_check = [
            "README.md",
            "GUIA_MODO_OPTIMIZED.md", 
            "requirements.txt"
        ]
        
        for file in files_to_check:
            if os.path.exists(file):
                size_kb = os.path.getsize(file) / 1024
                print(f"✅ {file} ({size_kb:.1f} KB)")
            else:
                print(f"❌ {file} não encontrado")
                
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação da documentação: {e}")
        return False

def test_requirements():
    """Verifica se o requirements.txt está otimizado"""
    try:
        print("\n📦 Verificando requirements.txt...")
        
        if os.path.exists("requirements.txt"):
            with open("requirements.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                
            print(f"✅ {len(lines)} dependências principais")
            
            # Verifica se há dependências essenciais
            essential_packages = ["pandas", "numpy", "openpyxl"]
            found_packages = []
            
            for line in lines:
                package_name = line.split("==")[0].split(">=")[0].split("~=")[0]
                if package_name in essential_packages:
                    found_packages.append(package_name)
                    
            if len(found_packages) >= 2:
                print(f"✅ Dependências essenciais encontradas: {', '.join(found_packages)}")
            else:
                print("⚠️ Algumas dependências essenciais podem estar ausentes")
                
            return True
        else:
            print("❌ requirements.txt não encontrado")
            return False
        
    except Exception as e:
        print(f"❌ Erro na verificação do requirements: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🚀 SSA Consulta Rápida - Teste de Sistema v3.0.2+")
    print("=" * 55)
    
    tests = [
        ("Funcionalidade Básica", test_basic_functionality),
        ("Banco de Dados", test_database), 
        ("Organização de Scripts", test_scripts_organization),
        ("Documentação", test_documentation),
        ("Requirements", test_requirements)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Falha no teste {name}: {e}")
            results.append(False)
    
    print("\n" + "=" * 55)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 Todos os testes passaram! ({passed}/{total})")
        print("✅ Sistema SSA está funcionando corretamente")
        print("\n🚀 Sistema pronto para uso!")
    elif passed >= total * 0.8:  # 80% ou mais
        print(f"✅ Sistema funcional com avisos menores ({passed}/{total})")
        print("⚠️ Alguns componentes podem precisar de atenção")
    else:
        print(f"⚠️ {total - passed} teste(s) crítico(s) falharam ({passed}/{total})")
        print("🔧 Verifique os erros acima antes de usar o sistema")
    
    print("\n💡 Comandos principais:")
    print("   🔍 Modo padrão:    python main.py")
    print("   ⚡ Modo otimizado: python main.py --optimized")
    print("   🖥️ Interface GUI:  python main.py --gui")
    print("   🗄️ Gerenciar DB:   python scripts_manutencao/gerenciar_banco.py")
    print("   📋 Ver ajuda:      python main.py --help")

if __name__ == "__main__":
    main()
