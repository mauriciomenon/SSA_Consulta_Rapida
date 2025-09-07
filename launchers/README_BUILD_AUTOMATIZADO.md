# Build Automatizado com Limpeza e Git Operations

## Visão Geral

O sistema de build foi atualizado para incluir limpeza automática de artefatos e operações git automáticas após builds bem-sucedidos.

## Funcionalidades Principais

### 1. Limpeza Automática de Artefatos (`--auto-cleanup`)

Remove automaticamente após build bem-sucedido:
- Cache Python (`__pycache__`, `*.pyc`, `*.pyo`)
- Arquivos temporários do PyInstaller (`build/`, `*.spec`)
- Logs antigos (mantém apenas os 5 mais recentes)
- Arquivos temporários do sistema (`.DS_Store`, `Thumbs.db`)
- Diretório `dist_simple` (builds de desenvolvimento)

### 2. Limpeza Online (`--cleanup-online`)

Remove arquivos desnecessários do controle de versão:
- Executáveis compilados
- Logs de build
- Cache de arquivos
- Backups de banco de dados
- Arquivos temporários

### 3. Operações Git Automáticas (`--auto-git`)

Após build bem-sucedido:
- Adiciona arquivos importantes (código, configurações, documentação)
- Exclui executáveis e artefatos temporários
- Cria commit com timestamp automático
- Faz push para o repositório remoto

## Uso

### Build Completo com Todas as Funcionalidades

```bash
# Build com limpeza e git automáticos
python launchers/build_multiplatform.py --auto-cleanup --auto-git

# Build com mensagem de commit personalizada
python launchers/build_multiplatform.py --auto-cleanup --auto-git --git-message "Nova versão v3.0.7"

# Apenas GUI com operações automáticas
python launchers/build_multiplatform.py --apps gui --auto-cleanup --auto-git
```

### Script de Conveniência

```bash
# Build completo (CLI + GUI) com tudo automático
python launchers/build_complete.py

# Apenas GUI
python launchers/build_complete.py --apps gui

# Com mensagem personalizada
python launchers/build_complete.py --git-message "Correções críticas"

# Sem git automático
python launchers/build_complete.py --no-git

# Apenas limpeza
python launchers/build_complete.py --cleanup-only
```

### Operações Independentes

```bash
# Apenas limpeza online
python launchers/build_multiplatform.py --cleanup-online

# Apenas build sem automações
python launchers/build_multiplatform.py

# Limpeza tradicional
python launchers/build_multiplatform.py --clean-all
```

## Argumentos Disponíveis

### Novos Argumentos

- `--auto-cleanup`: Limpeza automática após build
- `--auto-git`: Commit e push automáticos
- `--git-message "mensagem"`: Mensagem personalizada para commit
- `--cleanup-online`: Limpar arquivos desnecessários do git

### Argumentos Existentes

- `--apps cli gui`: Escolher aplicações para build
- `--platform macos_arm64`: Plataforma específica
- `--clean`: Limpeza tradicional
- `--clean-all`: Limpeza completa
- `--debug`: Logs detalhados

## Workflow Recomendado

### 1. Desenvolvimento

```bash
# Build rápido para testes
python launchers/build_simple.py --apps gui

# Build com limpeza local
python launchers/build_multiplatform.py --apps gui --auto-cleanup
```

### 2. Release

```bash
# Build completo para release
python launchers/build_complete.py --git-message "Release v3.0.7"
```

### 3. Manutenção

```bash
# Limpeza completa do projeto
python launchers/build_complete.py --cleanup-only

# Verificar status
python launchers/build_multiplatform.py --detect-platform
python launchers/build_multiplatform.py --list-platforms
```

## Arquivos Gerenciados

### Incluídos no Git
- Código fonte (`*.py`)
- Configurações (`config/*.json`)
- Documentação (`*.md`)
- Scripts de build (`launchers/*.py`)
- Configurações de plataforma (`launchers/platforms/*/build_config.json`)

### Excluídos do Git
- Executáveis (`launchers/dist/`)
- Ambientes virtuais (`launchers/platforms/*/venv/`)
- Logs (`launchers/logs/`)
- Cache (`data/file_cache.json`)
- Backups automáticos (`data/*.backup_*`)

## Logs e Monitoramento

### Localização dos Logs
- Build: `launchers/logs/build.log`
- Aplicação: `logs/`

### Informações dos Logs
- Timestamps de todas as operações
- Detalhes de limpeza (quantos arquivos removidos)
- Status das operações git
- Erros e warnings

## Segurança e Backup

### Proteções Implementadas
- Verificação de repositório git válido antes de operações
- Backup automático antes de limpezas
- Logs detalhados de todas as operações
- Validação de plataforma antes de build

### Recuperação
- Logs mantêm histórico de operações
- Git permite reverter commits se necessário
- Builds incrementais preservam trabalho anterior

## Troubleshooting

### Problemas Comuns

1. **Erro de Git**
   ```bash
   # Verificar status do repositório
   git status
   
   # Build sem git automático
   python launchers/build_complete.py --no-git
   ```

2. **Limpeza Excessiva**
   ```bash
   # Build sem limpeza
   python launchers/build_complete.py --no-cleanup
   ```

3. **Problemas de Permissão**
   ```bash
   # Verificar permissões
   ls -la launchers/dist/
   
   # Limpeza manual
   python launchers/build_multiplatform.py --clean-all
   ```
