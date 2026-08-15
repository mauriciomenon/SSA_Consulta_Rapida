from __future__ import annotations

import sys

from utils.robust_logging import get_robust_logger


_LOGGER = get_robust_logger().get_logger(__name__, "maintenance")


def emit(message: str = "") -> None:
    text = str(message)
    _LOGGER.info(text)
    sys.stdout.write(f"{text}\n")


def calculate_speedup(baseline_seconds: float, optimized_seconds: float) -> float:
    return (
        (baseline_seconds / optimized_seconds)
        if optimized_seconds > 0
        else float("inf")
    )


def report_boolean_results(
    results: list[bool],
    *,
    all_success_message: str,
    high_partial_message: str,
    partial_message: str,
    failure_message: str,
) -> bool:
    passed = sum(results)
    total = len(results)

    emit("INFO RESUMO DOS TESTES")
    emit("-" * 40)
    emit(f"  Testes aprovados: {passed}/{total}")

    if passed == total:
        emit(all_success_message)
        status = "EXCELENTE"
    elif passed >= total * 0.75:
        emit(high_partial_message)
        status = "PARCIAL_ALTO"
    elif passed >= total * 0.5:
        emit(partial_message)
        status = "PARCIAL_BAIXO"
    else:
        emit(failure_message)
        status = "NECESSITA CORRECAO"

    emit()
    emit(f"  Status final: {status}")
    emit(f"  Gate de release: {'OK' if passed == total else 'FALHA'}")
    return passed == total
