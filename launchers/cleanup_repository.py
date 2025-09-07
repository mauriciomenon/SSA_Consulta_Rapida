#!/usr/bin/env python3
"""
Limpeza Inteligente do Repositório
Remove APENAS arquivos temporários que não deveriam estar no GitHub
PRESERVA arquivos de dados importantes localmente
"""

import os
import sys
import subprocess
from pathlib import Path

def classify_files():
    """Classifica arquivos em categorias para decisão inteligente"""
    
    # Arquivos que são CLARAMENTE temporários e podem ser removidos do git
    definitely_temporary = [
        # Relatórios automáticos com timestamps
        r'.*_report_\d{8}_\d{6}\.(json|md)$',
        r'.*_test_\d{8}_\d{6}\.(json|md)$',
        r'automated_.*\.md$',
        r'comprehensive_test_.*\.json$',
        r'excel_import_test_.*\.json$',
        r'performance_tests_.*\.json$',
        r'migration_report_.*\.md$',
        
        # Exports temporários
        r'all\.(csv|json|xlsx)$',
        
        # Cache e builds
        r'.*/__pycache__/.*',
        r'.*\.pyc$',
        r'.*\.pyo$',
        r'launchers/dist/.*',
        r'launchers/dist_simple/.*',
        r'data/file_cache\.json$',
    ]
    
    # Arquivos que PODEM ser pessoais/importantes - perguntar
    potentially_personal = [
        # Documentação que pode ser pessoal
        r'.*LEMBRETE.*\.md$',
        r'.*NAO_MEXER.*\.md$',
        r'.*CAGADAS.*\.md$',
        r'.*CONVERSA.*\.md$',
        
        # Relatórios que podem ter dados sensíveis
        r'docs_saida/.*\.xlsx$',
        r'docs_saida/.*\.csv$',
    ]
    
    # Arquivos que NUNCA devem ser removidos (importantes para funcionamento)
    never_remove = [
        # Código fonte
        r'.*\.py$',
        r'requirements\.txt$',
        r'pyproject\.toml$',
        
        # Configurações importantes
        r'config/.*\.json$',
        r'\.gitignore$',
        
        # Documentação técnica profissional
        r'README\.md$',
        r'.*ESTRUTURA.*\.md$',
        r'.*REGRAS.*\.md$',
        r'.*RELEASE.*\.md$',
        r'.*CHANGELOG.*\.md$',
        
        # Dados de entrada (não remover, apenas ignorar)
        r'docs_entrada/.*\.xlsx$',
        r'data/ssas\.db$',
    ]
    
    return definitely_temporary, potentially_personal, never_remove

def main():
    print("🧹 === LIMPEZA INTELIGENTE DO REPOSITÓRIO ===")
    print("⚠️  ATENÇÃO: Esta versão é SEGURA e preserva dados importantes")
    
    base_dir = Path(__file__).parent.parent
    os.chdir(base_dir)
    
    # Classificar padrões
    temp_patterns, personal_patterns, never_patterns = classify_files()
    
    # Obter todos os arquivos sendo rastreados
    try:
        result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)
        all_files = result.stdout.strip().split('\\n') if result.stdout.strip() else []
    except Exception as e:
        print(f"❌ Erro obtendo lista de arquivos: {e}")
        return 1
    
    print(f"📊 Total de arquivos rastreados: {len(all_files)}")
    
    # Categorizar arquivos
    temp_files = []
    personal_files = []
    safe_files = []
    
    import re
    
    for file in all_files:
        # Verificar se é arquivo que nunca deve ser removido
        is_never = any(re.match(pattern, file) for pattern in never_patterns)
        if is_never:
            safe_files.append(file)
            continue
            
        # Verificar se é claramente temporário
        is_temp = any(re.match(pattern, file) for pattern in temp_patterns)
        if is_temp:
            temp_files.append(file)
            continue
            
        # Verificar se pode ser pessoal
        is_personal = any(re.match(pattern, file) for pattern in personal_patterns)
        if is_personal:
            personal_files.append(file)
            continue
            
        # Por padrão, considerar seguro
        safe_files.append(file)
    
    print(f"\\n📋 CLASSIFICAÇÃO:")
    print(f"   🗑️  Temporários (remover): {len(temp_files)}")
    print(f"   🤔 Possivelmente pessoais: {len(personal_files)}")
    print(f"   ✅ Seguros (manter): {len(safe_files)}")
    
    if temp_files:
        print(f"\\n�️  ARQUIVOS TEMPORÁRIOS A REMOVER ({len(temp_files)}):")
        for i, file in enumerate(temp_files, 1):
            print(f"   {i:3d}. {file}")
    
    if personal_files:
        print(f"\\n🤔 ARQUIVOS POSSIVELMENTE PESSOAIS ({len(personal_files)}):")
        for i, file in enumerate(personal_files, 1):
            print(f"   {i:3d}. {file}")
    
    if not temp_files and not personal_files:
        print("✅ Nenhum arquivo problemático encontrado!")
        return 0
    
    print("\\n⚠️  IMPORTANTE:")
    print("   - Arquivos serão removidos APENAS do git, não do disco")
    print("   - Dados de entrada (.xlsx) nunca são tocados")
    print("   - Código e configurações são preservados")
    
    # Decisão sobre temporários
    files_to_remove = []
    if temp_files:
        response = input(f"\\n🗑️  Remover {len(temp_files)} arquivos temporários do git? (s/N): ").strip().lower()
        if response in ['s', 'sim', 'y', 'yes']:
            files_to_remove.extend(temp_files)
    
    # Decisão sobre pessoais
    if personal_files:
        print(f"\\n� Arquivos possivelmente pessoais encontrados.")
        print("   Opções:")
        print("   1. Manter no git (público)")
        print("   2. Remover do git (manter privado)")
        print("   3. Revisar um por um")
        
        choice = input("\\nEscolha (1/2/3): ").strip()
        
        if choice == '2':
            files_to_remove.extend(personal_files)
        elif choice == '3':
            for file in personal_files:
                response = input(f"\\nRemover '{file}' do git? (s/N): ").strip().lower()
                if response in ['s', 'sim', 'y', 'yes']:
                    files_to_remove.append(file)
    
    if not files_to_remove:
        print("\\n✅ Nenhum arquivo será removido")
        return 0
    
    # Executar remoção
    print(f"\\n🧹 Removendo {len(files_to_remove)} arquivos do git...")
    removed_count = 0
    
    for file in files_to_remove:
        try:
            result = subprocess.run(['git', 'rm', '--cached', file], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ {file}")
                removed_count += 1
            else:
                print(f"   ⚠️  {file} (erro: {result.stderr.strip()})")
        except Exception as e:
            print(f"   ❌ Erro removendo {file}: {e}")
    
    print(f"\\n🎯 Limpeza concluída: {removed_count} arquivos removidos do git")
    print("\\n💡 PRÓXIMOS PASSOS:")
    print("   1. Verificar se .gitignore está atualizado")
    print("   2. Considerar tornar o repositório privado no GitHub")
    print("   3. Fazer commit e push das alterações")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
