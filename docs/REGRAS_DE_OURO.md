#  REGRAS DE OURO - SSA Consulta Rapida

##  NUNCA FACA
- Execute scripts na raiz sem ler ESTRUTURA_PROJETO.md
- Modifique core/, armazenamento/, extracao/ sem backup
- Delete data/ssas.db
- Execute multiplos scripts de correcao juntos
- Modifique main.py sem testar

##  SEMPRE FACA
- Leia ESTRUTURA_PROJETO.md primeiro
- Faca backup antes de mudancas criticas
- Use scripts_desenvolvimento/ para testes
- Use scripts_manutencao/ para correcoes
- Documente mudancas importantes

##  PRIORIDADE ATUAL
1. Corrigir erros de importacao (11 arquivos falhando)
2. Estabilizar banco de dados
3. Limpar arquivos desnecessarios

##  ARQUIVOS IMPORTANTES
- ESTRUTURA_PROJETO.md (este documento completo)
- main.py (entrada principal)
- armazenamento/database.py (banco)
- config/column_mappings.json (mapeamentos)

##  COMANDOS SEGUROS
```bash
# Diagnostico
python scripts_desenvolvimento/simple_test.py

# Verificacao
python scripts_manutencao/verificar_integridade.py

# Uso normal
python main.py
```

**Criado em 26/08/2025 - Mantenha sempre visivel**

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

