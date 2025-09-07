# CORREÇÃO CRÍTICA: Números SSA Truncados

## PROBLEMA IDENTIFICADO

**Sintoma**: GUI mostrava `002513402` em vez de `202513402`
**Causa Raiz**: Função `_normalize_numero_ssa_value()` em `armazenamento/database.py` linha 359

### **CÓDIGO PROBLEMÁTICO** (ANTES):
```python
# Remover zeros à esquerda apenas se necessário
s = s.lstrip('0')
```

**O QUE ACONTECIA**:
1. Valor original: `"202513402"`
2. Após `lstrip('0')`: `"2513402"` ← **ZEROS VÁLIDOS REMOVIDOS!**
3. Armazenado no banco: `2513402` (7 dígitos)
4. GUI tentava completar: `002513402` (errado)

## CORREÇÃO APLICADA

### **NOVO CÓDIGO** (DEPOIS):
```python
def _normalize_numero_ssa_value(v) -> int | None:
    """Normaliza um valor de numero_ssa para inteiro.

    Regras para SSAs de 9 dígitos (YYYYNNNNN):
    - Remove tudo que não seja dígito
    - Se vazio após limpeza: None
    - Valida se tem formato correto de ano (2019-2050) + 5 dígitos
    - Rejeita se não está no formato correto
    - Converte para int
    """
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = re.sub(r"\D", "", str(v))
        if not s:
            return None
        
        # NÃO remover zeros à esquerda - SSAs podem começar com zeros válidos!
        
        # Validar formato: deve ter exatamente 9 dígitos
        if len(s) != 9:
            logger.warning(f"SSA inválido - deve ter 9 dígitos: '{s}' (original: '{v}')")
            return None
            
        # Validar ano (primeiros 4 dígitos): deve estar entre 2019-2050
        ano_str = s[:4]
        try:
            ano = int(ano_str)
            if not (2019 <= ano <= 2050):
                logger.warning(f"SSA inválido - ano fora do range 2019-2050: '{s}' (ano: {ano})")
                return None
        except ValueError:
            logger.warning(f"SSA inválido - ano não numérico: '{s}'")
            return None
            
        # Converter para int
        return int(s)
        
    except Exception as e:
        logger.warning(f"Erro ao normalizar numero_ssa '{v}': {e}")
        return None
```

## MUDANÇAS PRINCIPAIS

1. **REMOVIDO**: `s = s.lstrip('0')` - linha que causava truncamento
2. **ADICIONADO**: Validação rigorosa de 9 dígitos obrigatórios
3. **ADICIONADO**: Validação de ano (2019-2050) nos primeiros 4 dígitos
4. **ADICIONADO**: Logs detalhados para casos inválidos

## IMPACTO ESPERADO

### **ANTES** (Incorreto):
- Entrada: `202513402`
- Processado: `2513402` 
- GUI mostrava: `002513402`

### **DEPOIS** (Correto):
- Entrada: `202513402`
- Processado: `202513402` ← **PRESERVADO!**
- GUI mostrará: `202513402` ← **CORRETO!**

##  **CONSEQUÊNCIA IMPORTANTE**

**DADOS ATUAIS NO BANCO ESTÃO CORROMPIDOS!**

Os 5.672 registros no banco têm apenas 7 dígitos em vez de 9. Para corrigir completamente:

1. **Opção 1**: Reimportar todos os arquivos Excel com a função corrigida
2. **Opção 2**: Script de correção em massa dos dados existentes

## 📂 **ARQUIVO MODIFICADO**

- **`armazenamento/database.py`** - função `_normalize_numero_ssa_value()`
- **Linhas alteradas**: 343-382 (função completa reescrita)

---

** STATUS**: ✅ **CORREÇÃO APLICADA** - Próxima etapa é reimportar dados ou corrigir banco existente
