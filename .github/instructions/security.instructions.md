---
applyTo: '**/*.py,**/*.js,**/*.ts,**/requirements*.txt,**/package*.json,**/Dockerfile,**/*.yaml,**/*.yml'
description: Regras de seguranca - analise obrigatoria apos edicoes
---

# Instrucoes de Seguranca

## REGRA CRITICA

Apos QUALQUER edicao em arquivos de codigo ou configuracao:

1. **Executar Codacy**: `codacy_cli_analyze` no arquivo editado
2. **Se houver issues de seguranca**: Corrigir imediatamente
3. **Se mudou dependencias**: Executar verificacao Sonatype

## Arquivos Sensiveis (Requer Atencao Extra)

### Python (*.py)
- Verificar SQL injection em queries
- Verificar path traversal em file operations
- Verificar command injection em subprocess
- Usar parametros em queries SQL, nunca concatenacao

### Dependencias (requirements*.txt, package*.json)
- Verificar CVEs com Sonatype antes de adicionar
- Usar versoes fixas, nao ranges
- Preferir versoes recomendadas por score

### Docker (Dockerfile, docker-compose*)
- Usar imagens oficiais
- Nao rodar como root
- Nao expor secrets em ENV

### Config (*.yaml, *.yml, *.json)
- Nao commitar secrets
- Usar variaveis de ambiente para credenciais

## Ferramentas de Seguranca Disponiveis

| Situacao | Ferramenta | Comando |
|----------|------------|---------|
| Apos editar codigo | Codacy | `codacy_cli_analyze` |
| Verificar dependencia | Sonatype | `getComponentVersion` |
| Scan completo de seguranca | Snyk | `snyk_code_scan` |
| Scan de container | Snyk | `snyk_container_scan` |
| Scan de IaC | Snyk | `snyk_iac_scan` |
| Code smells | SonarQube | `sonarqube_analyze_file` |

## Padroes Seguros para Este Projeto

### Database (SQLite)
```python
# CORRETO - Parametros
cursor.execute("SELECT * FROM ssas WHERE numero = ?", (numero,))

# ERRADO - Concatenacao (SQL Injection)
cursor.execute(f"SELECT * FROM ssas WHERE numero = '{numero}'")
```

### File Operations
```python
# CORRETO - Validar path
from pathlib import Path
safe_path = Path(base_dir) / filename
if not safe_path.is_relative_to(base_dir):
    raise ValueError("Path traversal detectado")

# ERRADO - Path direto
open(user_input_path)
```

### Subprocess
```python
# CORRETO - Lista de argumentos
subprocess.run(["ls", "-la", directory], check=True)

# ERRADO - Shell=True com input do usuario
subprocess.run(f"ls -la {user_input}", shell=True)
```
