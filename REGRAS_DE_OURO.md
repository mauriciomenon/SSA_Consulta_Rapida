# 🚨 REGRAS DE OURO - SSA Consulta Rápida

## ⛔ NUNCA FAÇA
- Execute scripts na raiz sem ler ESTRUTURA_PROJETO.md
- Modifique core/, armazenamento/, extracao/ sem backup
- Delete data/ssas.db
- Execute múltiplos scripts de correção juntos
- Modifique main.py sem testar

## ✅ SEMPRE FAÇA
- Leia ESTRUTURA_PROJETO.md primeiro
- Faça backup antes de mudanças críticas
- Use scripts_desenvolvimento/ para testes
- Use scripts_manutencao/ para correções
- Documente mudanças importantes

## 🎯 PRIORIDADE ATUAL
1. Corrigir erros de importação (11 arquivos falhando)
2. Estabilizar banco de dados
3. Limpar arquivos desnecessários

## 📞 ARQUIVOS IMPORTANTES
- ESTRUTURA_PROJETO.md (este documento completo)
- main.py (entrada principal)
- armazenamento/database.py (banco)
- config/column_mappings.json (mapeamentos)

## 🔧 COMANDOS SEGUROS
```bash
# Diagnóstico
python scripts_desenvolvimento/simple_test.py

# Verificação
python scripts_manutencao/verificar_integridade.py

# Uso normal
python main.py
```

**Criado em 26/08/2025 - Mantenha sempre visível**
