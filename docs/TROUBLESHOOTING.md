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

---

## **AUDIT DE ORDEM DE EXECUÇÃO - PROBLEMAS CRÍTICOS**

### **1. CONFLITO: Recarga de Configurações**

**Problema**: GUI e CLI carregam configurações de forma diferente e concorrente

#### GUI (gui_ssa.py):
```python
# Linhas 28-74: Carregamento no import
GUI_MAIN_PREFERENCES = load_gui_main_preferences()
# Linhas 354-394: Carregamento no __init__
self.display_map = load_display_mappings()
```

#### CLI (cli.py):
```python
# Linhas 363-365: Recarga a cada iteração do loop
settings = load_settings() 
display_map = load_display_mappings_integrity()
```

**CONFLITO**: GUI carrega uma vez, CLI recarrega constantemente → inconsistências.

**Solução**: Implementar cache de configurações com invalidação controlada.

### **2. INTERFERÊNCIA: Best-Fit vs Configurações Salvas**

**Problema**: Algoritmos de largura de coluna conflitam entre si

#### GUI - Ordem de Aplicação:
```python
# Linha 744: Sempre recalcula best-fit
self._compute_gui_column_widths(display_df)

# Linhas 761-786: Aplica larguras em ordem conflitante
# 1. Best-fit calculado
px = self._gui_column_pixel_widths.get(col_key)
# 2. Configuração salva manualmente
if px is None:
    px = self._saved_gui_column_widths.get(col_key)
# 3. Fallbacks hardcoded
```

**INTERFERÊNCIA**: Best-fit pode ser sobrescrito por configurações antigas.

**Solução**: Priorizar configurações salvas sobre best-fit automático.

### **3. CONFLITO: Thread Safety**

**Problema**: Múltiplas threads modificando estado sem sincronização

#### Threads Concorrentes:
1. **DataLoaderWorker** (linha 115)
2. **FilterWorker** (linha 178)  
3. **QTimer para debounce** (linha 386)
4. **QTimer para resize** (linha 1306)

**CONFLITO**: 
- `self.df_completo` modificado por DataLoaderWorker
- `self.df_exibido` modificado por FilterWorker
- `self._gui_column_pixel_widths` modificado por resize timer
- Sem locks ou sincronização

**Solução Crítica**: Implementar QMutex para proteger estado compartilhado:
```python
from PyQt6.QtCore import QMutex

class ThreadSafeGUI:
    def __init__(self):
        self.data_mutex = QMutex()
        self.config_mutex = QMutex()
    
    def update_data_safe(self, new_data):
        self.data_mutex.lock()
        try:
            self.df_completo = new_data
        finally:
            self.data_mutex.unlock()
```

### **4. ORDEM CONFLITANTE: Inicialização da GUI**

**Problema**: Dependências circulares na ordem de inicialização

#### Sequência Atual:
```python
# main.py linhas 110-122
1. setup_project_structure.setup_dirs()
2. ensure_default_settings()
3. run_importer_logic()
4. start_cli_loop() OU SSAMainWindow()
```

**CONFLITO**: GUI pode inicializar antes do banco estar pronto.

**Solução**: Verificação de dependências antes da inicialização:
```python
def safe_gui_init():
    if not database_ready():
        show_error("Banco não está pronto")
        return False
    if not config_valid():
        show_error("Configurações inválidas")
        return False
    return True
```

### **5. RECARREGAMENTO EXCESSIVO: CLI Loop**

**Problema**: Configurações recarregadas desnecessariamente a cada comando CLI

**Solução**: Cache com invalidação inteligente:
```python
class ConfigCache:
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get_config(self, config_file):
        current_time = os.path.getmtime(config_file)
        if (config_file not in self._cache or 
            self._timestamps[config_file] < current_time):
            self._cache[config_file] = load_config(config_file)
            self._timestamps[config_file] = current_time
        return self._cache[config_file]
```

---

## **SISTEMA DE LIMITAÇÃO DE EXIBIÇÃO - COMPORTAMENTO IMPLEMENTADO**

### **Como Funciona a Limitação de 300 Registros**

O sistema implementa um comportamento específico para melhorar performance mantendo funcionalidade completa:

#### **Cenário: Banco com 12.000 SSAs**

**1. Carregamento Inicial:**
```
df_completo = 12.000 SSAs (TODO o banco carregado na memória)
df_exibido = 300 SSAs (apenas os primeiros 300 para exibir)
Status: "Exibindo 300 de 12.000 SSAs (use filtros para refinar)"
```

**2. Filtro "ELÉTRICA":**
```
Busca em: df_completo (todos os 12.000 SSAs)
Filtro encontra: 850 SSAs com "ELÉTRICA"
df_exibido = 300 SSAs (primeiros 300 dos 850 encontrados)
Status: "Exibindo 300 de 850 SSAs encontradas (de 12.000 total) com 'ELÉTRICA'"
```

**3. Filtro Específico "ELÉTRICA, URGENTE":**
```
Busca em: df_completo (todos os 12.000 SSAs)
Filtro encontra: 45 SSAs com "ELÉTRICA" E "URGENTE"
df_exibido = 45 SSAs (todos os encontrados, menos que 300)
Status: "45 SSAs encontradas (de 12.000 total) com 'ELÉTRICA, URGENTE'"
```

**4. Limpeza de Filtro:**
```
df_exibido = 300 SSAs (volta a mostrar primeiros 300)
Status: "Exibindo 300 de 12.000 SSAs (use filtros para refinar)"
```

#### **Vantagens da Implementação**

1. **Performance**: Interface sempre rápida (máximo 300 linhas na tabela)
2. **Busca Completa**: Filtros sempre pesquisam no dataset completo
3. **Memória Eficiente**: Dataset inteiro na memória para buscas instantâneas
4. **Transparência**: Usuário sempre vê quantos registros existem vs. exibidos
5. **Flexibilidade**: Filtros específicos mostram todos os resultados se <300

#### **Troubleshooting da Limitação**

**Problema**: "Não vejo todos os meus dados"
- **Causa**: Limitação intencional para performance
- **Solução**: Use filtros para refinar a busca

**Problema**: "Filtro não encontra dados que sei que existem"
- **Causa**: Dados podem estar além dos primeiros 300
- **Solução**: Use filtros mais específicos para reduzir o conjunto
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

---

## **ANÁLISE CRÍTICA DO BANCO DE DADOS**

### **Relatório de Integridade Completo (25/08/2025)**

#### **Resumo Executivo**
- **Total de Registros**: 14,426
- **Total de Colunas**: 44
- **Grupos de Colunas Duplicadas**: 7
- **Backup Criado**: `data/backups/ssas_backup_20250825_122217.db`

#### **Problemas Críticos Identificados**

##### **Integridade de Dados**
```
CRÍTICO: Missing Numero Ssa      → 1,676 registros (11.6%)
CRÍTICO: Missing Descricao       → 6 registros
CRÍTICO: Missing Area Emissora   → 6 registros  
CRÍTICO: Missing Localizacao     → 6 registros
CRÍTICO: Duplicate Numbers       → 4,196 registros (29.1%)
VALIDADO: Invalid Dates          → 0 registros
CRÍTICO: Empty Records           → 6 registros
```

##### **Colunas Duplicadas - Problema de Schema**
```
PROBLEMA: Sistema possui colunas duplicadas com formatos diferentes:

1. Numero Ssa:
    "Número da SSA" (TEXT) → 12,750 registros (PRIMÁRIA)
    "numero_ssa" (INTEGER) → 1,670 registros (LEGADO)

2. Semana Cadastro:
    "Semana de Cadastro" (INTEGER) → 12,750 registros (PRIMÁRIA)
    "semana_cadastro" (INTEGER) → 1,670 registros (LEGADO)

3. Descricao Execucao:
    "Descrição Execução" (TEXT) → 10,845 registros (PRIMÁRIA)
    "descricao_execucao" (TEXT) → 1,195 registros (LEGADO)

4. Responsavel Programacao:
    "Responsável na Programação" (TEXT) → 11,376 registros (PRIMÁRIA)
    "responsavel_programacao" (TEXT) → 1,327 registros (LEGADO)

5. Responsavel Execucao:
    "Responsável na Execução" (TEXT) → 11,188 registros (PRIMÁRIA)
    "responsavel_execucao" (TEXT) → 1,259 registros (LEGADO)

6. Grau Prioridade Emissao:
    "Grau de Prioridade Emissão" (TEXT) → 12,750 registros (PRIMÁRIA)
    "grau_prioridade_emissao" (TEXT) → 1,670 registros (LEGADO)

7. Grau Prioridade Planejamento:
    "Grau de Prioridade Planejamento" (TEXT) → 11,058 registros (PRIMÁRIA)
    "grau_prioridade_planejamento" (TEXT) → 1,494 registros (LEGADO)
```

#### **Distribuição de Dados por Qualidade**

##### **Colunas com Alta Completude (>99%)**
```
situacao                 → 14,420/14,426 (99.96%)
localizacao_codigo       → 14,420/14,426 (99.96%)
descricao_localizacao    → 14,420/14,426 (99.96%)
descricao_ssa           → 14,420/14,426 (99.96%)
setor_emissor           → 14,420/14,426 (99.96%)
setor_executor          → 14,420/14,426 (99.96%)
solicitante             → 14,420/14,426 (99.96%)
servico_origem          → 14,420/14,426 (99.96%)
```

##### **Colunas com Completude Moderada (75-95%)**
```
execucao_simples         → 14,413/14,426 (99.91%)
equipamento             → 14,357/14,426 (99.52%)
data_cadastro           → 14,343/14,426 (99.42%)
semana_programada       → 12,773/14,426 (88.54%)
"Número da SSA"         → 12,750/14,426 (88.38%)
```

##### **Colunas com Completude Baixa (<80%)**
```
"Responsável na Programação"     → 11,376/14,426 (78.86%)
"Responsável na Execução"        → 11,188/14,426 (77.55%)
"Grau de Prioridade Planejamento" → 11,058/14,426 (76.65%)
"Descrição Execução"             → 10,845/14,426 (75.18%)
```

#### **Recomendações de Correção**

##### **Prioridade CRÍTICA**
1. **Merge das Colunas Duplicadas**: Consolidar dados das colunas legado nas primárias
2. **Limpeza de Registros Vazios**: Investigar e corrigir 6 registros completamente vazios
3. **Normalização de Números SSA**: Resolver 4,196 duplicatas
4. **Preenchimento de Dados Críticos**: Resolver 1,676 SSAs sem número

##### **Prioridade ALTA**
1. **Padronização de Schema**: Remover colunas legado após merge
2. **Validação de Integridade**: Implementar constraints de NOT NULL em campos críticos
3. **Auditoria de Duplicatas**: Sistema de detecção automática

##### **Scripts de Correção Sugeridos**
```sql
-- 1. Merge de colunas duplicadas
UPDATE ssas SET "Número da SSA" = numero_ssa 
WHERE "Número da SSA" IS NULL AND numero_ssa IS NOT NULL;

-- 2. Limpeza de registros vazios
DELETE FROM ssas WHERE 
    "Número da SSA" IS NULL AND 
    descricao_ssa IS NULL AND 
    situacao IS NULL;

-- 3. Remoção de colunas legado (após verificação)
-- ALTER TABLE ssas DROP COLUMN numero_ssa;
-- ALTER TABLE ssas DROP COLUMN semana_cadastro;
-- (etc para outras colunas legado)
```

##### **Verificação Pós-Correção**
```bash
# Executar verificação de integridade
python scripts_manutencao/verificar_integridade.py

# Gerar novo relatório de análise
python scripts_manutencao/database_analysis.py

# Validar importações após correções
python main.py -rescan --verify-integrity
```

---

## **PROBLEMAS DE ENCODING E CHARSET**

### **Relatório de Testes Automatizados (25/08/2025)**

#### **Problema Crítico Identificado**
```
ERROR: UnicodeEncodeError em Testes Automatizados
Codec: 'charmap' (cp1252)
Caractere: '\U0001f680' (emoji de foguete )
Posição: 0
Status: character maps to <undefined>
```

#### **Contexto do Problema**
- **Data**: 25/08/2025 14:16:43
- **Arquivo**: `tests/automated_system_tests.py`
- **Função**: `run_all_tests()` linha 571
- **Situação**: Sistema Windows com encoding cp1252 não suporta emojis Unicode

#### **Análise da Falha**
```python
# Código que causou a falha:
print("\U0001f680 Iniciando testes automatizados do sistema SSA...")
#      ^^^^^^^^^^^
#      Emoji de foguete não suportado em cp1252
```

#### **Impacto no Sistema**
-  **Smoke Tests**: Funcionando (33.3% dos testes)
-  **Testes Funcionais Automatizados**: Falha total por encoding
-  **Taxa de Sucesso Geral**: 33.3% (crítico)

#### **Solução Implementada**

##### **1. Correção de Encoding nos Testes**
```python
# ANTES (problemático):
print("\U0001f680 Iniciando testes automatizados do sistema SSA...")

# DEPOIS (compatível):
print(" Iniciando testes automatizados do sistema SSA...")
# OU melhor ainda:
print("* Iniciando testes automatizados do sistema SSA...")
```

##### **2. Configuração de Encoding Segura**
```python
# No início dos arquivos de teste:
import sys
import locale

# Força encoding UTF-8 se disponível
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

##### **3. Função Segura para Output**
```python
def safe_print(message):
    """Print seguro que trata problemas de encoding."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Remove caracteres problemáticos
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)
```

#### **Regras de Codificação para Evitar Problema**

##### **PROIBIDO em Outputs de Console**
```python
 print(" Texto com emoji")
 print(" Checkmark emoji") 
 print(" X emoji")
 print(" Gráfico emoji")
```

##### **PERMITIDO e Recomendado**
```python
 print("* Iniciando sistema...")
 print("[OK] Operação concluída")
 print("[ERRO] Falha detectada")
 print(">>> Status do sistema")
```

#### **Script de Correção para Arquivos Existentes**
```bash
# Encontrar arquivos com emojis problemáticos
grep -r "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]" tests/ scripts_*/ interface/

# Substituir emojis comuns por caracteres seguros
sed -i 's//*/g' tests/*.py
sed -i 's//[OK]/g' tests/*.py  
sed -i 's//[ERRO]/g' tests/*.py
```

#### **Configuração de Ambiente Recomendada**

##### **Windows (PowerShell)**
```powershell
# Configurar encoding UTF-8 no PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```

##### **Variáveis de Ambiente**
```bash
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
```

#### **Testes de Validação Pós-Correção**
```bash
# Testar encoding em diferentes ambientes
python -c "import sys; print(f'Encoding: {sys.stdout.encoding}')"

# Executar testes sem emojis
python tests/automated_system_tests.py

# Verificar compatibilidade Windows
python -c "print('Teste de caracteres: * [OK] [ERRO] >>>')"
```
