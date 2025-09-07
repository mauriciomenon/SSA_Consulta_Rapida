#!/usr/bin/env python3
"""
Script para corrigir vírgulas em toda a documentação
"""

import os
import re
from pathlib import Path

def fix_commas_in_file(file_path):
    """Corrige vírgulas em um arquivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Palavras que devem ter vírgula corrigida
        corrections = {
            'dependencias': 'dependências',
            'funcionalidade': 'funcionalidade',  # já está correto
            'aplicacoes': 'aplicações',
            'configuracao': 'configuração',
            'otimizacao': 'otimização',
            'separacao': 'separação',
            'reducao': 'redução',
            'especifica': 'específica',
            'compativel': 'compatível',
            'suportadas': 'suportadas',  # já está correto
            'necessarias': 'necessárias',
            'minimas': 'mínimas',
            'executavel': 'executável',
            'conflitantes': 'conflitantes',  # já está correto
            'eficiente': 'eficiente',  # já está correto
            'multipla': 'múltipla',
            'especificas': 'específicas',
            'funcionais': 'funcionais',  # já está correto
            'automaticos': 'automáticos',
            'grafica': 'gráfica',
            'pratica': 'prática',
            'unica': 'única',
            'multiplataforma': 'multi-plataforma',
            'compilacao': 'compilação',
            'otimizacoes': 'otimizações',
            'especifico': 'específico',
            'multiplos': 'múltiplos',
            'instalacao': 'instalação',
            'distribuicao': 'distribuição',
            'confiavel': 'confiável'
        }
        
        # Aplicar correções
        original_content = content
        for wrong, correct in corrections.items():
            content = re.sub(r'\b' + wrong + r'\b', correct, content, flags=re.IGNORECASE)
        
        # Se houve mudanças, salvar
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corrigido: {file_path}")
            return True
        else:
            print(f"📝 Sem mudanças: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Erro em {file_path}: {e}")
        return False

def main():
    """Corrige vírgulas em todos os arquivos .md do launchers/"""
    launchers_dir = Path("launchers")
    
    if not launchers_dir.exists():
        print("❌ Diretório launchers/ não encontrado")
        return
    
    # Encontrar todos os arquivos .md
    md_files = list(launchers_dir.rglob("*.md"))
    
    print(f"🔍 Encontrados {len(md_files)} arquivos .md")
    
    corrected_count = 0
    for md_file in md_files:
        if fix_commas_in_file(md_file):
            corrected_count += 1
    
    print(f"\n📊 Resumo:")
    print(f"   Total de arquivos: {len(md_files)}")
    print(f"   Arquivos corrigidos: {corrected_count}")
    print(f"   Arquivos sem mudanças: {len(md_files) - corrected_count}")

if __name__ == "__main__":
    main()
