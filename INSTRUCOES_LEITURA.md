<!-- DEPRECATED: incorporado ao README principal; mantido temporariamente para histórico. Será removido. -->
# SSA CONSULTA RÁPIDA – Instruções de Leitura

## Novidades v4.0.0 – Performance Otimizada

### Visão Geral de Melhorias

- Imports acelerados (até ~90%)
- GUI: ganhos de 3x até ordens de magnitude com cache LRU
- Streamlit: ganho massivo via cache TTL
- Banco: consultas até 5–20x mais rápidas
- Logging estruturado com métricas integradas

##  **NOVIDADES v4.0.0 - PERFORMANCE MASSIVAMENTE OTIMIZADA**

###  Visão Geral de Melhorias
- Imports acelerados (até ~90%)
- GUI: ganhos de 3x até ordens de magnitude com cache LRU
- Streamlit: ganho massivo via cache TTL
- Banco: consultas até 5–20x mais rápidas
- Logging estruturado com métricas integradas

###  **DOCUMENTAÇÃO ATUALIZADA:**

### Leitura Essencial (mover para `docs/` em breve)

- `README.md` – ponto de partida
- `docs/CHANGELOG_IMPLEMENTACOES.md` – histórico técnico
- `docs/GUIA_MODO_OPTIMIZED.md` – modo otimizado (padrão)
- `docs/COMANDOS_RAPIDOS.md` – comandos comuns

### Documentação Técnica

- `docs/ESTRUTURA_PROJETO.md` – topologia
- `utils/robust_logging.py` – logging
- `config/logging.json` – configuração

### Relatórios de Performance

- Relatórios em `docs_saida/`
- Métricas presentes no logging

### Início Rápido

```bash
python main.py --help       # Opções CLI
python main.py --gui        # Interface gráfica
python main.py --streamlit  # Interface web
```

Todas as interfaces utilizam as otimizações acima.

---
Documento legado: conteúdo será integrado ao `README.md` e este arquivo removido.

