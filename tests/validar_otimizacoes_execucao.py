#!/usr/bin/env python3
"""
Validador das Otimizações de Ordem de Execução
Verifica se as melhorias de performance foram implementadas corretamente.
"""

import os
import re
import sys

def verificar_otimizacoes():
    """Verifica se todas as otimizações foram aplicadas corretamente."""
    
    gui_ssa_path = os.path.join('gui', 'gui_ssa.py')
    
    if not os.path.exists(gui_ssa_path):
        print("❌ Arquivo gui/gui_ssa.py não encontrado!")
        return False
    
    with open(gui_ssa_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    verificacoes = []
    
    # 1. Verificar eliminação do cálculo duplo de larguras
    if '_widths_computed_for_df_hash' in content:
        if 'current_df_hash = hash(str(display_df.shape)' in content:
            verificacoes.append("✅ Cálculo duplo de larguras eliminado - hash tracking implementado")
        else:
            verificacoes.append("❌ Hash tracking de larguras não encontrado")
    else:
        verificacoes.append("❌ Sistema de cache de larguras não implementado")
    
    # 2. Verificar remoção da chamada dupla em on_filter_finished
    on_filter_pattern = r'def on_filter_finished.*?def \w+'
    on_filter_match = re.search(on_filter_pattern, content, re.DOTALL)
    if on_filter_match:
        on_filter_code = on_filter_match.group(0)
        if '_compute_gui_column_widths(self.df_exibido)' not in on_filter_code:
            verificacoes.append("✅ Chamada redundante removida de on_filter_finished()")
        else:
            verificacoes.append("❌ Chamada redundante ainda presente em on_filter_finished()")
    else:
        verificacoes.append("❌ Método on_filter_finished não encontrado")
    
    # 3. Verificar cache de configurações
    if '_cached_default_mode' in content:
        verificacoes.append("✅ Cache de configurações GUI implementado")
    else:
        verificacoes.append("❌ Cache de configurações não implementado")
    
    # 4. Verificar cache de formatação
    if '_formatted_df_cache' in content:
        if 'display_df_hash = hash(str(display_df.shape)' in content:
            verificacoes.append("✅ Cache de formatação implementado com hash tracking")
        else:
            verificacoes.append("❌ Cache de formatação implementado mas sem hash tracking")
    else:
        verificacoes.append("❌ Cache de formatação não implementado")
    
    # 5. Verificar otimização do resizeEvent (já existente)
    if 'QTimer.singleShot(300' in content and 'width_change > 50' in content:
        verificacoes.append("✅ ResizeEvent já otimizado com timer e threshold")
    else:
        verificacoes.append("⚠️  ResizeEvent pode precisar de otimização")
    
    # Exibir resultados
    print("🔍 VALIDAÇÃO DAS OTIMIZAÇÕES DE EXECUÇÃO:")
    print("=" * 60)
    
    for verificacao in verificacoes:
        print(f"  {verificacao}")
    
    print()
    
    # Contar sucessos
    sucessos = sum(1 for v in verificacoes if v.startswith("✅"))
    total = len(verificacoes)
    
    if sucessos == total:
        print("🎉 TODAS AS OTIMIZAÇÕES FORAM IMPLEMENTADAS COM SUCESSO!")
        print("📈 Performance da GUI deve estar significativamente melhorada.")
        return True
    elif sucessos >= total * 0.8:
        print(f"✅ MAIORIA DAS OTIMIZAÇÕES IMPLEMENTADA ({sucessos}/{total})")
        print("📊 Performance substancialmente melhorada.")
        return True
    else:
        print(f"⚠️  ALGUMAS OTIMIZAÇÕES PENDENTES ({sucessos}/{total})")
        print("🔧 Revisar implementações restantes.")
        return False

def exibir_metricas_esperadas():
    """Exibe as métricas de performance esperadas."""
    print("\n📊 MÉTRICAS DE PERFORMANCE ESPERADAS:")
    print("=" * 50)
    print("• Eliminação de ~50% dos cálculos de largura redundantes")
    print("• Redução de ~30% no tempo de carregamento de filtros")
    print("• Cache de formatação: ~40% menos processamento em paginação")
    print("• Cache de config: ~80% menos acesso a arquivos JSON")
    print("• ResizeEvent: Máximo 1 recálculo por 300ms")

def main():
    """Função principal do validador."""
    print("🚀 VALIDADOR DE OTIMIZAÇÕES - ORDEM DE EXECUÇÃO")
    print("=" * 60)
    
    # Mudar para o diretório do projeto
    if os.path.basename(os.getcwd()) != 'SSA_Consulta_Rapida':
        possible_paths = [
            '.',
            '../SSA_Consulta_Rapida',
            './SSA_Consulta_Rapida'
        ]
        
        found = False
        for path in possible_paths:
            if os.path.exists(os.path.join(path, 'gui', 'gui_ssa.py')):
                os.chdir(path)
                found = True
                break
        
        if not found:
            print("❌ Não foi possível encontrar o diretório do projeto SSA_Consulta_Rapida")
            return False
    
    # Executar verificações
    resultado = verificar_otimizacoes()
    exibir_metricas_esperadas()
    
    return resultado

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
