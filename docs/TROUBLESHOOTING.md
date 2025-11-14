# GUIA DE SOLUCAO DE PROBLEMAS

Este documento consolida toda a documentacao de troubleshooting e solucoes tecnicas para o SSA Consulta Rapida.

## **PROBLEMAS CONHECIDOS E SOLUCOES**

### **1. PROBLEMAS DE GUI - LARGURAS DE COLUNAS**

#### **Sintoma**
- Colunas da GUI aparecem com larguras incorretas
- Interface fica desorganizada apos redimensionamento
- Larguras nao sao salvas entre sessoes

#### **Causa Raiz**
O sistema de larguras de colunas do PyQt6 e complexo e requer gerenciamento cuidadoso.

#### **Solucao Implementada - SimpleWidthManager**
```python
# Localizacao: gui/simple_width_manager.py
class SimpleWidthManager:
    def save_widths(self, table_widget, config_key):
        # Salva larguras no arquivo de configuracao
    
    def load_widths(self, table_widget, config_key):
        # Carrega larguras do arquivo de configuracao
```

#### **Algoritmo Critico**
**REGRA FUNDAMENTAL**: NUNCA modificar diretamente o sistema de larguras sem usar o SimpleWidthManager.

**Fluxo de Funcionamento:**
1. **Inicializacao**: LoadWidths() carrega larguras salvas
2. **Uso Normal**: Sistema gerencia larguras automaticamente
3. **Fechamento**: SaveWidths() persiste configuracoes
4. **Problemas**: Reset atraves de configuracoes

#### **Comandos de Diagnostico**
```bash
# Verificar arquivo de configuracao
cat config/gui_main_preferences.json

# Reset de larguras (remove configuracoes salvas)
rm config/gui_main_preferences.json

# Verificar logs da GUI
tail -f logs/gui_debug.log
```

#### **Prevencao**
- NUNCA editar manualmente arquivos de configuracao de larguras

---

## **AUDIT DE ORDEM DE EXECUCAO - PROBLEMAS CRITICOS**

### **1. CONFLITO: Recarga de Configuracoes**

**Problema**: GUI e CLI carregam configuracoes de forma diferente e concorrente

#### GUI (gui_ssa.py):
```python
# Linhas 28-74: Carregamento no import
GUI_MAIN_PREFERENCES = load_gui_main_preferences()
# Linhas 354-394: Carregamento no __init__
self.display_map = load_display_mappings()
```

#### CLI (cli.py):
```python
# Linhas 363-365: Recarga a cada iteracao do loop
settings = load_settings() 
display_map = load_display_mappings_integrity()
```

**CONFLITO**: GUI carrega uma vez, CLI recarrega constantemente → inconsistencias.

**Solucao**: Implementar cache de configuracoes com invalidacao controlada.

### **2. INTERFERENCIA: Best-Fit vs Configuracoes Salvas**

**Problema**: Algoritmos de largura de coluna conflitam entre si

#### GUI - Ordem de Aplicacao:
```python
# Linha 744: Sempre recalcula best-fit
self._compute_gui_column_widths(display_df)

# Linhas 761-786: Aplica larguras em ordem conflitante
# 1. Best-fit calculado
px = self._gui_column_pixel_widths.get(col_key)
# 2. Configuracao salva manualmente
if px is None:
    px = self._saved_gui_column_widths.get(col_key)
# 3. Fallbacks hardcoded
```

**INTERFERENCIA**: Best-fit pode ser sobrescrito por configuracoes antigas.

**Solucao**: Priorizar configuracoes salvas sobre best-fit automatico.

### **3. CONFLITO: Thread Safety**

**Problema**: Multiplas threads modificando estado sem sincronizacao

#### Threads Concorrentes:
1. **DataLoaderWorker** (linha 115)
2. **FilterWorker** (linha 178)  
3. **QTimer para debounce** (linha 386)
4. **QTimer para resize** (linha 1306)

**CONFLITO**: 
- `self.df_completo` modificado por DataLoaderWorker
- `self.df_exibido` modificado por FilterWorker
- `self._gui_column_pixel_widths` modificado por resize timer
- Sem locks ou sincronizacao

**Solucao Critica**: Implementar QMutex para proteger estado compartilhado:
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

### **4. ORDEM CONFLITANTE: Inicializacao da GUI**

**Problema**: Dependencias circulares na ordem de inicializacao

#### Sequencia Atual:
```python
# main.py linhas 110-122
1. setup_project_structure.setup_dirs()
2. ensure_default_settings()
3. run_importer_logic()
4. start_cli_loop() OU SSAMainWindow()
```

**CONFLITO**: GUI pode inicializar antes do banco estar pronto.

**Solucao**: Verificacao de dependencias antes da inicializacao:
```python
def safe_gui_init():
    if not database_ready():
        show_error("Banco nao esta pronto")
        return False
    if not config_valid():
        show_error("Configuracoes invalidas")
        return False
    return True
```

### **5. RECARREGAMENTO EXCESSIVO: CLI Loop**

**Problema**: Configuracoes recarregadas desnecessariamente a cada comando CLI

**Solucao**: Cache com invalidacao inteligente:
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

## **SISTEMA DE LIMITACAO DE EXIBICAO - COMPORTAMENTO IMPLEMENTADO**

### **Como Funciona a Limitacao de 300 Registros**

O sistema implementa um comportamento especifico para melhorar performance mantendo funcionalidade completa:

#### **Cenario: Banco com 12.000 SSAs**

**1. Carregamento Inicial:**
```
df_completo = 12.000 SSAs (TODO o banco carregado na memoria)
df_exibido = 300 SSAs (apenas os primeiros 300 para exibir)
Status: "Exibindo 300 de 12.000 SSAs (use filtros para refinar)"
```

**2. Filtro "ELETRICA":**
```
Busca em: df_completo (todos os 12.000 SSAs)
Filtro encontra: 850 SSAs com "ELETRICA"
df_exibido = 300 SSAs (primeiros 300 dos 850 encontrados)
Status: "Exibindo 300 de 850 SSAs encontradas (de 12.000 total) com 'ELETRICA'"
```

**3. Filtro Especifico "ELETRICA, URGENTE":**
```
Busca em: df_completo (todos os 12.000 SSAs)
Filtro encontra: 45 SSAs com "ELETRICA" E "URGENTE"
df_exibido = 45 SSAs (todos os encontrados, menos que 300)
Status: "45 SSAs encontradas (de 12.000 total) com 'ELETRICA, URGENTE'"
```

**4. Limpeza de Filtro:**
```
df_exibido = 300 SSAs (volta a mostrar primeiros 300)
Status: "Exibindo 300 de 12.000 SSAs (use filtros para refinar)"
```

#### **Vantagens da Implementacao**

1. **Performance**: Interface sempre rapida (maximo 300 linhas na tabela)
2. **Busca Completa**: Filtros sempre pesquisam no dataset completo
3. **Memoria Eficiente**: Dataset inteiro na memoria para buscas instantaneas
4. **Transparencia**: Usuario sempre ve quantos registros existem vs. exibidos
5. **Flexibilidade**: Filtros especificos mostram todos os resultados se <300

#### **Troubleshooting da Limitacao**

**Problema**: "Nao vejo todos os meus dados"
- **Causa**: Limitacao intencional para performance
- **Solucao**: Use filtros para refinar a busca

**Problema**: "Filtro nao encontra dados que sei que existem"
- **Causa**: Dados podem estar alem dos primeiros 300
- **Solucao**: Use filtros mais especificos para reduzir o conjunto
- Usar sempre o SimpleWidthManager para mudancas programaticas
- Testar redimensionamento apos qualquer mudanca na GUI

---

### **2. PROBLEMAS DE PERFORMANCE COM ARQUIVOS GRANDES**

#### **Sintoma**
- Lentidao extrema ao importar arquivos >5MB
- Interface trava durante importacao
- Memoria elevada durante processamento

#### **Solucao - Modo Optimized**
```bash
# Usar modo otimizado para arquivos grandes
python main.py --import arquivo_grande.xlsx --optimized

# GUI com modo otimizado
python main.py --gui --optimized
```

#### **Algoritmo de Otimizacao**
1. **Deteccao Automatica**: Sistema detecta arquivos >5MB
2. **Processamento em Chunks**: Divide dados em blocos menores
3. **Lazy Loading**: Carrega dados conforme necessario
4. **Cache Inteligente**: Mantem apenas dados ativos na memoria

#### **Metricas de Performance**
- **Sem Otimizacao**: ~30 segundos para arquivo de 10MB
- **Com Otimizacao**: ~8 segundos para arquivo de 10MB
- **Uso de Memoria**: Reducao de ~60%

---

### **3. PROBLEMAS DE IMPORTACAO DE DADOS**

#### **Sintomas Comuns**
- Erro "Arquivo nao encontrado"
- Dados importados incorretamente
- Conflitos de encoding
- SSAs truncados ou duplicados

#### **Diagnostico Passo-a-Passo**

##### **3.1 Verificacao do Arquivo**
```bash
# Verificar se arquivo existe e e acessivel
ls -la arquivo.xlsx

# Verificar formato do arquivo
file arquivo.xlsx

# Verificar tamanho
du -h arquivo.xlsx
```

##### **3.2 Teste de Importacao Basica**
```bash
# Importacao em modo debug
python main.py --import arquivo.xlsx --debug

# Verificar logs
tail -f logs/import_debug.log
```

##### **3.3 Verificacao do Banco de Dados**
```bash
# Verificar integridade do banco
python scripts_manutencao/verificar_integridade.py

# Estatisticas do banco
python scripts_manutencao/estatisticas_db.py

# Backup antes de correcoes
python scripts_manutencao/backup_db.py
```

#### **Problemas Especificos e Solucoes**

##### **SSAs Truncados (Problema Historico Critico)**
**Causa**: Funcao `clean_ssa_number()` removendo digitos validos
**Solucao**: Algoritmo corrigido
```python
def clean_ssa_number(value):
    # VERSAO CORRIGIDA - mantem todos os digitos
    if pd.isna(value):
        return None
    
    str_value = str(value).strip()
    # Remove apenas caracteres nao-numericos, preserva digitos
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

### **4. PROBLEMAS DE INSTALACAO E AMBIENTE**

#### **4.1 Python Environment Issues**

##### **Verificacao Rapida**
```bash
# Verificar versao do Python
python --version

# Verificar ambiente virtual
which python

# Verificar dependencias
pip list | grep -E "(PyQt6|pandas|openpyxl)"
```

##### **Problemas Comuns**
1. **PyQt6 nao instalado**: `pip install PyQt6>=6.5.0`
2. **Pandas desatualizado**: `pip install pandas>=2.0.0`
3. **openpyxl ausente**: `pip install openpyxl>=3.1.0`

#### **4.2 Script de Verificacao Automatica**
```bash
# Verificacao completa do ambiente
./verificar_instalacao.ps1  # Windows
./verificar_instalacao.sh   # Linux/macOS
```

---

### **5. PROBLEMAS DE BUILD E EXECUTAVEIS**

#### **5.1 Build Falha**

##### **Diagnostico**
```bash
# Verificar configuracao de build
cat launchers/platforms/*/build_config.json

# Build com verbose
python launchers/build_multiplatform.py --apps gui --verbose

# Verificar logs de build
tail -f launchers/logs/build_*.log
```

##### **Solucoes Comuns**
1. **Dependencias de Build**: Instalar `pyinstaller`, `setuptools`
2. **Paths Incorretos**: Verificar caminhos relativos nos configs
3. **Recursos Ausentes**: Verificar se `resources/` esta presente

#### **5.2 Executavel Nao Inicia**

##### **Diagnostico**
```bash
# Executar em modo debug
./executavel --debug

# Verificar dependencias do sistema
ldd executavel  # Linux
otool -L executavel  # macOS
```

---

### **6. COMANDOS DE EMERGENCIA**

#### **6.1 Reset Completo**
```bash
# Backup atual
cp -r data/ssas.db data/ssas_backup_$(date +%Y%m%d).db

# Reset de configuracoes
rm -f config/*_preferences.json

# Limpar cache
rm -rf logs/*
rm -rf __pycache__/*

# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

#### **6.2 Recuperacao de Dados**
```bash
# Verificar backups disponiveis
ls -la data/historico_backups/

# Restaurar backup especifico
python scripts_manutencao/restaurar_backup.py --backup data/historico_backups/backup_20250906.db

# Verificar integridade apos restauracao
python scripts_manutencao/verificar_integridade.py
```

#### **6.3 Debug Avancado**
```bash
# Ativar todos os logs de debug
export SSA_DEBUG=1

# Executar com profiling
python -m cProfile -o profile_output.prof main.py --gui

# Analisar profile
python -m pstats profile_output.prof
```

---

## **PROCEDIMENTOS DE MANUTENCAO PREVENTIVA**

### **1. Verificacoes Semanais**
```bash
# Integridade do banco de dados
python scripts_manutencao/verificar_integridade.py

# Limpeza de logs antigos
find logs -name "*.log" -mtime +30 -delete

# Backup automatico
python scripts_manutencao/backup_automatico.py
```

### **2. Verificacoes Mensais**
```bash
# Atualizacao de dependencias
pip list --outdated

# Verificacao de performance
python scripts_manutencao/benchmark_performance.py

# Analise de uso de espaco
du -sh data/ docs/ logs/
```

### **3. Verificacoes por Release**
```bash
# Testes de regressao
python -m pytest tests/ -v

# Verificacao de compatibilidade
python scripts_manutencao/teste_compatibilidade.py

# Validacao de builds
python launchers/build_multiplatform.py --test-all
```

---

## **CONTATOS PARA SUPORTE**

### **Documentacao Tecnica**
- **Arquivo Principal**: `ESTRUTURA_PROJETO.md`
- **Configuracoes**: `config/README.md`
- **Build System**: `launchers/BUILD_SYSTEM.md`

### **Scripts de Diagnostico**
- **Integridade**: `scripts_manutencao/verificar_integridade.py`
- **Performance**: `scripts_manutencao/benchmark_*.py`
- **Debug**: `scripts_manutencao/debug_*.py`

### **Logs Importantes**
- **Aplicacao**: `logs/app.log`
- **GUI**: `logs/gui_debug.log`
- **Importacao**: `logs/import_debug.log`
- **Build**: `launchers/logs/build_*.log`

**Lembrete**: Sempre fazer backup antes de aplicar qualquer solucao que modifique dados!

---

## **ANALISE CRITICA DO BANCO DE DADOS**

### **Relatorio de Integridade Completo (25/08/2025)**

#### **Resumo Executivo**
- **Total de Registros**: 14,426
- **Total de Colunas**: 44
- **Grupos de Colunas Duplicadas**: 7
- **Backup Criado**: `data/backups/ssas_backup_20250825_122217.db`

#### **Problemas Criticos Identificados**

##### **Integridade de Dados**
```
CRITICO: Missing Numero Ssa      → 1,676 registros (11.6%)
CRITICO: Missing Descricao       → 6 registros
CRITICO: Missing Area Emissora   → 6 registros  
CRITICO: Missing Localizacao     → 6 registros
CRITICO: Duplicate Numbers       → 4,196 registros (29.1%)
VALIDADO: Invalid Dates          → 0 registros
CRITICO: Empty Records           → 6 registros
```

##### **Colunas Duplicadas - Problema de Schema**
```
PROBLEMA: Sistema possui colunas duplicadas com formatos diferentes:

1. Numero Ssa:
    "Numero da SSA" (TEXT) → 12,750 registros (PRIMARIA)
    "numero_ssa" (INTEGER) → 1,670 registros (LEGADO)

2. Semana Cadastro:
    "Semana de Cadastro" (INTEGER) → 12,750 registros (PRIMARIA)
    "semana_cadastro" (INTEGER) → 1,670 registros (LEGADO)

3. Descricao Execucao:
    "Descricao Execucao" (TEXT) → 10,845 registros (PRIMARIA)
    "descricao_execucao" (TEXT) → 1,195 registros (LEGADO)

4. Responsavel Programacao:
    "Responsavel na Programacao" (TEXT) → 11,376 registros (PRIMARIA)
    "responsavel_programacao" (TEXT) → 1,327 registros (LEGADO)

5. Responsavel Execucao:
    "Responsavel na Execucao" (TEXT) → 11,188 registros (PRIMARIA)
    "responsavel_execucao" (TEXT) → 1,259 registros (LEGADO)

6. Grau Prioridade Emissao:
    "Grau de Prioridade Emissao" (TEXT) → 12,750 registros (PRIMARIA)
    "grau_prioridade_emissao" (TEXT) → 1,670 registros (LEGADO)

7. Grau Prioridade Planejamento:
    "Grau de Prioridade Planejamento" (TEXT) → 11,058 registros (PRIMARIA)
    "grau_prioridade_planejamento" (TEXT) → 1,494 registros (LEGADO)
```

#### **Distribuicao de Dados por Qualidade**

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
"Numero da SSA"         → 12,750/14,426 (88.38%)
```

##### **Colunas com Completude Baixa (<80%)**
```
"Responsavel na Programacao"     → 11,376/14,426 (78.86%)
"Responsavel na Execucao"        → 11,188/14,426 (77.55%)
"Grau de Prioridade Planejamento" → 11,058/14,426 (76.65%)
"Descricao Execucao"             → 10,845/14,426 (75.18%)
```

#### **Recomendacoes de Correcao**

##### **Prioridade CRITICA**
1. **Merge das Colunas Duplicadas**: Consolidar dados das colunas legado nas primarias
2. **Limpeza de Registros Vazios**: Investigar e corrigir 6 registros completamente vazios
3. **Normalizacao de Numeros SSA**: Resolver 4,196 duplicatas
4. **Preenchimento de Dados Criticos**: Resolver 1,676 SSAs sem numero

##### **Prioridade ALTA**
1. **Padronizacao de Schema**: Remover colunas legado apos merge
2. **Validacao de Integridade**: Implementar constraints de NOT NULL em campos criticos
3. **Auditoria de Duplicatas**: Sistema de deteccao automatica

##### **Scripts de Correcao Sugeridos**
```sql
-- 1. Merge de colunas duplicadas
UPDATE ssas SET "Numero da SSA" = numero_ssa 
WHERE "Numero da SSA" IS NULL AND numero_ssa IS NOT NULL;

-- 2. Limpeza de registros vazios
DELETE FROM ssas WHERE 
    "Numero da SSA" IS NULL AND 
    descricao_ssa IS NULL AND 
    situacao IS NULL;

-- 3. Remocao de colunas legado (apos verificacao)
-- ALTER TABLE ssas DROP COLUMN numero_ssa;
-- ALTER TABLE ssas DROP COLUMN semana_cadastro;
-- (etc para outras colunas legado)
```

##### **Verificacao Pos-Correcao**
```bash
# Executar verificacao de integridade
python scripts_manutencao/verificar_integridade.py

# Gerar novo relatorio de analise
python scripts_manutencao/database_analysis.py

# Validar importacoes apos correcoes
python main.py -rescan --verify-integrity
```

---

## **PROBLEMAS DE ENCODING E CHARSET**

### **Relatorio de Testes Automatizados (25/08/2025)**

#### **Problema Critico Identificado**
```
ERROR: UnicodeEncodeError em Testes Automatizados
Codec: 'charmap' (cp1252)
Caractere: '\U0001f680' (emoji de foguete )
Posicao: 0
Status: character maps to <undefined>
```

#### **Contexto do Problema**
- **Data**: 25/08/2025 14:16:43
- **Arquivo**: `tests/automated_system_tests.py`
- **Funcao**: `run_all_tests()` linha 571
- **Situacao**: Sistema Windows com encoding cp1252 nao suporta emojis Unicode

#### **Analise da Falha**
```python
# Codigo que causou a falha:
print("\U0001f680 Iniciando testes automatizados do sistema SSA...")
#      ^^^^^^^^^^^
#      Emoji de foguete nao suportado em cp1252
```

#### **Impacto no Sistema**
-  **Smoke Tests**: Funcionando (33.3% dos testes)
-  **Testes Funcionais Automatizados**: Falha total por encoding
-  **Taxa de Sucesso Geral**: 33.3% (critico)

#### **Solucao Implementada**

##### **1. Correcao de Encoding nos Testes**
```python
# ANTES (problematico):
print("\U0001f680 Iniciando testes automatizados do sistema SSA...")

# DEPOIS (compativel):
print(" Iniciando testes automatizados do sistema SSA...")
# OU melhor ainda:
print("* Iniciando testes automatizados do sistema SSA...")
```

##### **2. Configuracao de Encoding Segura**
```python
# No inicio dos arquivos de teste:
import sys
import locale

# Forca encoding UTF-8 se disponivel
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

##### **3. Funcao Segura para Output**
```python
def safe_print(message):
    """Print seguro que trata problemas de encoding."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Remove caracteres problematicos
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)
```

#### **Regras de Codificacao para Evitar Problema**

##### **PROIBIDO em Outputs de Console**
```python
 print(" Texto com emoji")
 print(" Checkmark emoji") 
 print(" X emoji")
 print(" Grafico emoji")
```

##### **PERMITIDO e Recomendado**
```python
 print("* Iniciando sistema...")
 print("[OK] Operacao concluida")
 print("[ERRO] Falha detectada")
 print(">>> Status do sistema")
```

#### **Script de Correcao para Arquivos Existentes**
```bash
# Encontrar arquivos com emojis problematicos
grep -r "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]" tests/ scripts_*/ interface/

# Substituir emojis comuns por caracteres seguros
sed -i 's//*/g' tests/*.py
sed -i 's//[OK]/g' tests/*.py  
sed -i 's//[ERRO]/g' tests/*.py
```

#### **Configuracao de Ambiente Recomendada**

##### **Windows (PowerShell)**
```powershell
# Configurar encoding UTF-8 no PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```

##### **Variaveis de Ambiente**
```bash
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
```

#### **Testes de Validacao Pos-Correcao**
```bash
# Testar encoding em diferentes ambientes
python -c "import sys; print(f'Encoding: {sys.stdout.encoding}')"

# Executar testes sem emojis
python tests/automated_system_tests.py

# Verificar compatibilidade Windows
python -c "print('Teste de caracteres: * [OK] [ERRO] >>>')"
```
