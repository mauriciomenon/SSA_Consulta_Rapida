# 📋 SSA Consulta Rápida - Estrutura do Projeto v3.10

## 🚨 INSTRUÇÕES CRÍTICAS - LEIA ANTES DE QUALQUER COISA

### ⛔ O QUE **NUNCA** FAZER
- **JAMAIS** execute scripts na raiz sem entender sua função
- **JAMAIS** modifique arquivos nas pastas `core/`, `armazenamento/`, `extracao/` sem backup
- **JAMAIS** delete o arquivo `data/ssas.db` - é o banco principal
- **JAMAIS** execute múltiplos scripts de correção simultaneamente
- **JAMAIS** modifique `main.py` sem testar em ambiente isolado

### 🎯 RUMO A TOMAR - PRIORIDADES
1. **PRIMEIRO**: Resolver erros de importação (ver seção Problemas Críticos)
2. **SEGUNDO**: Estabilizar o banco de dados
3. **TERCEIRO**: Limpar arquivos desnecessários da raiz
4. **QUARTO**: Implementar melhorias graduais

### 📚 ARQUIVOS GUIA ESSENCIAIS
- `main.py` - Ponto de entrada principal
- `armazenamento/database.py` - Lógica do banco de dados
- `extracao/extractor.py` - Lógica de extração de Excel
- `config/column_mappings.json` - Mapeamento de colunas
- `CHANGELOG_IMPLEMENTACOES.md` - Histórico de mudanças

---

## 🏗️ ESTRUTURA ATUAL DO PROJETO

### 📁 **Pastas Principais (CORE - NÃO MEXER)**
```
├── armazenamento/          # 🔒 Gestão do banco SQLite
├── core/                   # 🔒 Lógica central da aplicação  
├── extracao/              # 🔒 Extração de dados Excel
├── gui/                   # 🔒 Interface gráfica
├── interface/             # 🔒 Interface CLI
├── config/                # ⚙️ Configurações JSON
├── data/                  # 💾 Banco de dados SQLite
├── utils/                 # 🛠️ Utilitários auxiliares
```

### 📁 **Pastas de Dados**
```
├── docs_entrada/          # 📥 Arquivos Excel para importação
├── docs_saida/           # 📤 Relatórios gerados
├── exportacao/           # 📊 Exports diversos
├── logs/                 # 📝 Logs da aplicação
```

### 📁 **Pastas Organizadas (RECÉM CRIADAS)**
```
├── scripts_manutencao/    # 🔧 Scripts de manutenção/correção
├── scripts_desenvolvimento/ # 🧪 Scripts de teste/debug
├── tests/                # ✅ Testes automatizados
```

---

## 📋 INVENTÁRIO DETALHADO DE ARQUIVOS

### 🚀 **Arquivos Principais (RAIZ)**
| Arquivo | Função | Status | Pode Mexer? |
|---------|--------|--------|-------------|
| `main.py` | Ponto de entrada principal | ✅ Funcionando | ⚠️ Com cuidado |
| `build.py` | Compilação/distribuição | ✅ OK | ✅ Sim |
| `requirements.txt` | Dependências Python | ✅ OK | ✅ Sim |
| `pyproject.toml` | Configuração do projeto | ✅ OK | ✅ Sim |
| `README.md` | Documentação básica | ✅ OK | ✅ Sim |

### ⚙️ **Configurações (config/)**
| Arquivo | Função | Criticidade |
|---------|--------|-------------|
| `column_mappings.json` | Mapeamento colunas Excel→DB | 🔴 CRÍTICO |
| `column_priority.json` | Prioridade de colunas | 🟡 Importante |
| `display_mappings.json` | Exibição na interface | 🟡 Importante |
| `default_settings.json` | Configurações padrão | 🟢 Normal |
| `settings.json` | Configurações do usuário | 🟢 Normal |
| `schema.sql` | Esquema do banco | 🔴 CRÍTICO |

### 🔧 **Scripts de Manutenção (scripts_manutencao/)**
| Arquivo | Função | Quando Usar |
|---------|--------|-------------|
| `correcao_completa_*.py` | Correções críticas | 🚨 Emergências |
| `debug_*.py` | Diagnóstico de problemas | 🔍 Investigação |
| `verificar_*.py` | Verificações de integridade | ✅ Validação |
| `limpar_*.py` | Limpeza de dados | 🧹 Manutenção |
| `analisar_*.py` | Análise de dados | 📊 Relatórios |

### 🧪 **Scripts de Desenvolvimento (scripts_desenvolvimento/)**
| Arquivo | Função | Finalidade |
|---------|--------|------------|
| `test_*.py` | Testes diversos | 🧪 Validação |
| `teste_*.py` | Testes experimentais | 🔬 Experimentos |
| `simple_test.py` | Teste básico | 🎯 Diagnóstico rápido |

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. 🔥 **Erros de Importação Críticos**
```
ERROR - Falha na inserção: Reindexing only valid with uniquely valued Index objects
ERROR - '>=' not supported between instances of 'NaTType' and 'str'
WARNING - Erro ao converter coluna desde: The truth value of a Series is ambiguous
```

**Arquivos Problemáticos:**
- `Em Execução_15-08-2025_0416PM.xlsx`
- `Em Execução_15-08-2025_0417PM.xlsx`
- `Não Planejadas em Espera_15-08-2025_0410PM.xlsx`
- `Pendentes de Execução_*.xlsx`
- `SSAs Pendentes Geral_*.xlsx`
- `Todas as SSAs_*.xlsx`

**Localização do Problema:**
- Arquivo: `armazenamento/database.py` - função `insert_dataframe_with_smart_upsert()`
- Arquivo: `extracao/extractor.py` - validação de datas

### 2. 🔍 **Diagnóstico Recomendado**
Execute na ordem:
```bash
python scripts_desenvolvimento/simple_test.py
python scripts_manutencao/debug_db.py
python scripts_manutencao/verificar_integridade.py
```

---

## 🎯 PLANO DE AÇÃO RECOMENDADO

### **FASE 1: Estabilização (URGENTE)**
1. **Backup do banco atual**
   ```bash
   copy data\ssas.db data\ssas_backup_$(date).db
   ```

2. **Executar diagnóstico**
   ```bash
   python scripts_desenvolvimento/test_import_verification.py
   ```

3. **Corrigir erros de data/NaT**
   - Editar `armazenamento/database.py`
   - Corrigir comparação de datas com valores NaT

### **FASE 2: Limpeza**
1. Mover scripts restantes para pastas apropriadas
2. Criar logs estruturados
3. Documentar correções

### **FASE 3: Melhoria**
1. Implementar validação robusta de dados
2. Melhorar tratamento de erros
3. Otimizar performance

---

## 🔍 FLUXO DE FUNCIONAMENTO

### **Importação de Dados**
```
docs_entrada/*.xlsx → extracao/extractor.py → armazenamento/database.py → data/ssas.db
```

### **Consulta de Dados**
```
Usuário → interface/cli.py → core/app_logic.py → armazenamento/database.py → data/ssas.db
```

### **Configuração**
```
config/*.json → core/config_manager.py → Toda a aplicação
```

---

## 📊 ESTATÍSTICAS ATUAIS

- **Total de SSAs**: 11.145
- **Arquivos com erro**: 11 de 24
- **Taxa de sucesso**: ~54%
- **Tamanho do banco**: ~4.7 MB

---

## 🛠️ COMANDOS ESSENCIAIS

### **Uso Normal**
```bash
python main.py                    # Interface CLI normal
python main.py --rescan          # Reimportar todos os arquivos
python main.py --mode update     # Atualizar banco
```

### **Diagnóstico**
```bash
python scripts_desenvolvimento/simple_test.py          # Teste básico
python scripts_manutencao/debug_db.py                 # Debug do banco
python scripts_manutencao/verificar_integridade.py    # Verificar integridade
```

### **Emergência**
```bash
python scripts_manutencao/limpar_banco.py             # Limpar banco
python scripts_manutencao/emergency_cleanup.py       # Limpeza de emergência
```

---

## 🚨 CONTATOS DE EMERGÊNCIA

- **Arquivo Principal**: `main.py`
- **Configuração Crítica**: `config/column_mappings.json`
- **Banco de Dados**: `data/ssas.db`
- **Log Principal**: `logs/app.log`

---

## 📝 ANOTAÇÕES IMPORTANTES

1. **O sistema está funcional mas instável** - 54% dos arquivos importam com sucesso
2. **Problemas principais são de validação de dados** - datas inválidas e índices duplicados
3. **A estrutura core está correta** - não mexer sem necessidade
4. **Foco na correção de bugs** antes de implementar novas funcionalidades

---

*Documento gerado automaticamente em 26/08/2025*
*Mantenha este documento atualizado conforme mudanças no projeto*
