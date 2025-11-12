# Correcao: Problema de Virgula Apagada Durante Digitacao

## Problema Reportado

Usuario reportou que virgulas sao apagadas automaticamente durante a digitacao no filtro geral da GUI. O comportamento ocorre porque:

1. Debounce muito curto (250ms) dispara enquanto usuario ainda esta digitando
2. Filtro processa texto incompleto
3. Possivel interferencia do processamento automatico com o input do usuario

## Diagnostico

### Debounce Atual
```json
"debounce_delay": 250  // 0.25 segundos - MUITO CURTO
```

### Comportamento Observado
- Usuario digita: "termo1,"
- Debounce dispara aos 250ms
- Filtro processa "termo1," (incompleto)
- Usuario continua: "termo2"
- Possivel conflito entre processamento e input

## Correcao Aplicada

### 1. Aumento do Debounce

Arquivo: [config/gui_main_preferences.json](config/gui_main_preferences.json)

```json
"debounce_delay": 800  // 0.8 segundos - tempo mais seguro
```

**Justificativa:**
- 800ms da tempo suficiente para usuario completar digitacao
- Velocidade media de digitacao: 40-60 palavras/minuto = ~300-400ms entre palavras
- 800ms e um equilibrio entre responsividade e evitar disparo prematuro

### 2. Testes de Regressao

Arquivo: [tests/test_filter_regression.py](tests/test_filter_regression.py)

Criados testes automatizados para garantir:
- Virgulas sao preservadas como separadores
- Operadores logicos (||, v, OU, OR, AND) tratados como literais
- Sem splitting por operadores antigos
- Filtros funcionam corretamente com multiplos termos

**Status:** 7/7 testes passando

## Recomendacoes Adicionais

### Para Usuario

1. **Teste apos reiniciar GUI:**
   ```bash
   python main.py --gui
   ```

2. **Comportamento esperado:**
   - Digite normalmente: "termo1,termo2,termo3"
   - Aguarde 0.8s apos parar de digitar
   - Filtro deve processar todos os termos preservando virgulas

3. **Se problema persistir:**
   - Feche TODAS instancias da GUI
   - Limpe cache Python:
     ```bash
     find . -name "__pycache__" -type d -exec rm -rf {} +
     ```
   - Reinicie aplicacao

### Para Desenvolvimento

1. **Considerar Opcao de Debounce Configuravel:**
   - Adicionar slider na GUI para ajuste do debounce
   - Permitir usuario escolher entre "Instantaneo" (100ms), "Rapido" (400ms), "Normal" (800ms), "Lento" (1500ms)

2. **Adicionar Indicador Visual:**
   - Mostrar icone de "processando" durante debounce
   - Indicar claramente quando filtro esta ativo vs esperando

3. **Testes GUI Automatizados:**
   - Adicionar testes de integracao com PyQt6
   - Simular digitacao com delays realistas
   - Verificar estado do QLineEdit durante/apos processamento

## Verificacao

### Checklist Pre-Deploy

- [x] Debounce aumentado para 800ms
- [x] Testes de regressao criados e passando
- [x] Documentacao atualizada
- [ ] Usuario testou e confirmou correcao
- [ ] Monitoramento de issues similares

### Metricas de Sucesso

- Usuario consegue digitar virgulas sem serem apagadas
- Filtro dispara apenas apos pausa na digitacao
- Nenhuma regressao em funcionalidade de filtros
- Comportamento consistente entre diferentes velocidades de digitacao

## Referencias

- Issue original: Relato usuario sobre virgulas apagadas
- Commit anterior: 6770c9d (remocao de operadores logicos)
- Testes: tests/test_filter_regression.py
- Config: config/gui_main_preferences.json:73

## Rollback

Se necessario reverter:
```bash
git checkout HEAD~1 config/gui_main_preferences.json
```

Ou manualmente ajustar debounce_delay de volta para 250ms (nao recomendado).
