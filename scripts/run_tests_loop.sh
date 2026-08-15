#!/usr/bin/env bash
set -euo pipefail

MARK_EXPR="not legacy"
ITERATIONS="${1:-0}" # 0 = infinito
SLEEP="${SLEEP_BETWEEN:-0}"

echo "== Loop de testes iniciado =="
echo "Expressao de marcacao: $MARK_EXPR"
if [[ "$ITERATIONS" == "0" ]]; then
  echo "Modo: infinito (Ctrl+C para parar)"
else
  echo "Iteracoes planejadas: $ITERATIONS"
fi

COUNT=0
FAIL=0
START_ALL=$(date +%s)

while :; do
  COUNT=$((COUNT+1))
  echo "\n[Iteracao $COUNT] $(date '+%Y-%m-%d %H:%M:%S')" | tee /dev/stderr
  START=$(date +%s)
  if ! pytest -m "$MARK_EXPR" -q; then
     echo "Falha na iteracao $COUNT" | tee /dev/stderr
     FAIL=1
     break
  fi
  # Simulacao de import + exercicio GUI (1 ciclo) apos iteracao de testes bem-sucedida
  if [[ -f "scripts/simulate_import_and_gui.py" ]]; then
    echo "[Iteracao $COUNT] Executando simulacao de import + GUI" | tee /dev/stderr
    python scripts/simulate_import_and_gui.py --iterations 1 || echo "[WARN] Simulacao retornou codigo nao-zero" >&2
  fi
  DUR=$(( $(date +%s) - START ))
  echo "Iteracao $COUNT concluida em ${DUR}s" | tee /dev/stderr
  if [[ "$ITERATIONS" != "0" && $COUNT -ge $ITERATIONS ]]; then
     echo "Limite de iteracoes alcancado ($ITERATIONS)." | tee /dev/stderr
     break
  fi
  if [[ "$SLEEP" != "0" ]]; then
    echo "Aguardando ${SLEEP}s..."; sleep "$SLEEP";
  fi
done

TOTAL=$(( $(date +%s) - START_ALL ))
if [[ $FAIL -eq 0 ]]; then
  echo "\nResultado final: SUCESSO apos $COUNT iteracao(oes) em ${TOTAL}s" | tee /dev/stderr
  exit 0
else
  echo "\nResultado final: FALHA na iteracao $COUNT (tempo total ${TOTAL}s)" | tee /dev/stderr
  exit 1
fi
