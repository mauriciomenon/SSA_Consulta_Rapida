# GUIA DE SOLUÇÃO DE PROBLEMAS

Este documento consolida toda a documentação de troubleshooting e soluções técnicas para o SSA Consulta Rápida.

## **PROBLEMAS CONHECIDOS E SOLUÇÕES**

### **1. PROBLEMAS DE GUI - LARGURAS DE COLUNAS**

#### **Sintoma**
- Colunas da GUI aparecem com larguras incorretas
- Interface fica desorganizada após redimensionamento
- Larguras não são salvas entre sessões

#### **Causa Raiz**
O sistema de larguras de colunas do PyQt6 é complexo e requer gerenciamento cuidadoso.

#### **Solução Implementada - SimpleWidthManager**
```python
# Localização: gui/simple_width_manager.py
class SimpleWidthManager:
    def save_widths(self, table_widget, config_key):
        # Salva larguras no arquivo de configuração
    
    def load_widths(self, table_widget, config_key):
        # Carrega larguras do arquivo de configuração
```

#### **Algoritmo Crítico**
**REGRA FUNDAMENTAL**: NUNCA modificar diretamente o sistema de larguras sem usar o SimpleWidthManager.

**Fluxo de Funcionamento:**
1. **Inicialização**: LoadWidths() carrega larguras salvas
2. **Uso Normal**: Sistema gerencia larguras automaticamente
3. **Fechamento**: SaveWidths() persiste configurações
4. **Problemas**: Reset através de configurações

#### **Comandos de Diagnóstico**
```bash
# Verificar arquivo de configuração
cat config/gui_main_preferences.json

# Reset de larguras (remove configurações salvas)
rm config/gui_main_preferences.json

# Verificar logs da GUI
tail -f logs/gui_debug.log
```

#### **Prevenção**
- NUNCA editar manualmente arquivos de configuração de larguras
- Usar sempre o SimpleWidthManager para mudanças programáticas
- Testar redimensionamento após qualquer mudança na GUI

---

### **2. PROBLEMAS DE PERFORMANCE COM ARQUIVOS GRANDES**

#### **Sintoma**
- Lentidão extrema ao importar arquivos >5MB
- Interface trava durante importação
- Memória elevada durante processamento

#### **Solução - Modo Optimized**
```bash
# Usar modo otimizado para arquivos grandes
python main.py --import arquivo_grande.xlsx --optimized

# GUI com modo otimizado
python main.py --gui --optimized
```

#### **Algoritmo de Otimização**
1. **Detecção Automática**: Sistema detecta arquivos >5MB
2. **Processamento em Chunks**: Divide dados em blocos menores
3. **Lazy Loading**: Carrega dados conforme necessário
4. **Cache Inteligente**: Mantém apenas dados ativos na memória

#### **Métricas de Performance**
- **Sem Otimização**: ~30 segundos para arquivo de 10MB
- **Com Otimização**: ~8 segundos para arquivo de 10MB
- **Uso de Memória**: Redução de ~60%

---

### **3. PROBLEMAS DE IMPORTAÇÃO DE DADOS**

#### **Sintomas Comuns**
- Erro "Arquivo não encontrado"
- Dados importados incorretamente
- Conflitos de encoding
- SSAs truncados ou duplicados

#### **Diagnóstico Passo-a-Passo**

##### **3.1 Verificação do Arquivo**
```bash
# Verificar se arquivo existe e é acessível
ls -la arquivo.xlsx

# Verificar formato do arquivo
file arquivo.xlsx

# Verificar tamanho
du -h arquivo.xlsx
```

##### **3.2 Teste de Importação Básica**
```bash
# Importação em modo debug
python main.py --import arquivo.xlsx --debug

# Verificar logs
tail -f logs/import_debug.log
```

##### **3.3 Verificação do Banco de Dados**
```bash
# Verificar integridade do banco
python scripts_manutencao/verificar_integridade.py

# Estatísticas do banco
python scripts_manutencao/estatisticas_db.py

# Backup antes de correções
python scripts_manutencao/backup_db.py
```

#### **Problemas Específicos e Soluções**

##### **SSAs Truncados (Problema Histórico Crítico)**
**Causa**: Função `clean_ssa_number()` removendo dígitos válidos
**Solução**: Algoritmo corrigido
```python
def clean_ssa_number(value):
    # VERSÃO CORRIGIDA - mantém todos os dígitos
    if pd.isna(value):
        return None
    
    str_value = str(value).strip()
    # Remove apenas caracteres não-numéricos, preserva dígitos
    cleaned = re.sub(r'[^\d]', '', str_value)
    
    return int(cleaned) if cleaned else None
```

##### **Conflitos de Encoding**
```python
# Detectar encoding do arquivo
import chardet
with open('arquivo.xlsx', 'rb') as f:
    result = chardet.detect(f.read())
    print(f"Encoding detectado: {result['encoding']}")
```

##### **Dados Duplicados**
```sql
-- Verificar duplicatas no banco
SELECT numero_ssa, COUNT(*) as count 
FROM ssas 
GROUP BY numero_ssa 
HAVING COUNT(*) > 1;
```

---

### **4. PROBLEMAS DE INSTALAÇÃO E AMBIENTE**

#### **4.1 Python Environment Issues**

##### **Verificação Rápida**
```bash
# Verificar versão do Python
python --version

# Verificar ambiente virtual
which python

# Verificar dependências
pip list | grep -E "(PyQt6|pandas|openpyxl)"
```

##### **Problemas Comuns**
1. **PyQt6 não instalado**: `pip install PyQt6>=6.5.0`
2. **Pandas desatualizado**: `pip install pandas>=2.0.0`
3. **openpyxl ausente**: `pip install openpyxl>=3.1.0`

#### **4.2 Script de Verificação Automática**
```bash
# Verificação completa do ambiente
./verificar_instalacao.ps1  # Windows
./verificar_instalacao.sh   # Linux/macOS
```

---

### **5. PROBLEMAS DE BUILD E EXECUTÁVEIS**

#### **5.1 Build Falha**

##### **Diagnóstico**
```bash
# Verificar configuração de build
cat launchers/platforms/*/build_config.json

# Build com verbose
python launchers/build_multiplatform.py --apps gui --verbose

# Verificar logs de build
tail -f launchers/logs/build_*.log
```

##### **Soluções Comuns**
1. **Dependências de Build**: Instalar `pyinstaller`, `setuptools`
2. **Paths Incorretos**: Verificar caminhos relativos nos configs
3. **Recursos Ausentes**: Verificar se `resources/` está presente

#### **5.2 Executável Não Inicia**

##### **Diagnóstico**
```bash
# Executar em modo debug
./executavel --debug

# Verificar dependências do sistema
ldd executavel  # Linux
otool -L executavel  # macOS
```

---

### **6. COMANDOS DE EMERGÊNCIA**

#### **6.1 Reset Completo**
```bash
# Backup atual
cp -r data/ssas.db data/ssas_backup_$(date +%Y%m%d).db

# Reset de configurações
rm -f config/*_preferences.json

# Limpar cache
rm -rf logs/*
rm -rf __pycache__/*

# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

#### **6.2 Recuperação de Dados**
```bash
# Verificar backups disponíveis
ls -la data/historico_backups/

# Restaurar backup específico
python scripts_manutencao/restaurar_backup.py --backup data/historico_backups/backup_20250906.db

# Verificar integridade após restauração
python scripts_manutencao/verificar_integridade.py
```

#### **6.3 Debug Avançado**
```bash
# Ativar todos os logs de debug
export SSA_DEBUG=1

# Executar com profiling
python -m cProfile -o profile_output.prof main.py --gui

# Analisar profile
python -m pstats profile_output.prof
```

---

## **PROCEDIMENTOS DE MANUTENÇÃO PREVENTIVA**

### **1. Verificações Semanais**
```bash
# Integridade do banco de dados
python scripts_manutencao/verificar_integridade.py

# Limpeza de logs antigos
find logs -name "*.log" -mtime +30 -delete

# Backup automático
python scripts_manutencao/backup_automatico.py
```

### **2. Verificações Mensais**
```bash
# Atualização de dependências
pip list --outdated

# Verificação de performance
python scripts_manutencao/benchmark_performance.py

# Análise de uso de espaço
du -sh data/ docs/ logs/
```

### **3. Verificações por Release**
```bash
# Testes de regressão
python -m pytest tests/ -v

# Verificação de compatibilidade
python scripts_manutencao/teste_compatibilidade.py

# Validação de builds
python launchers/build_multiplatform.py --test-all
```

---

## **CONTATOS PARA SUPORTE**

### **Documentação Técnica**
- **Arquivo Principal**: `ESTRUTURA_PROJETO.md`
- **Configurações**: `config/README.md`
- **Build System**: `launchers/BUILD_SYSTEM.md`

### **Scripts de Diagnóstico**
- **Integridade**: `scripts_manutencao/verificar_integridade.py`
- **Performance**: `scripts_manutencao/benchmark_*.py`
- **Debug**: `scripts_manutencao/debug_*.py`

### **Logs Importantes**
- **Aplicação**: `logs/app.log`
- **GUI**: `logs/gui_debug.log`
- **Importação**: `logs/import_debug.log`
- **Build**: `launchers/logs/build_*.log`

**Lembrete**: Sempre fazer backup antes de aplicar qualquer solução que modifique dados!
