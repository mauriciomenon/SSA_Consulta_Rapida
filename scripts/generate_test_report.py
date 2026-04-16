"""Gera relatório de testes:
- Executa pytest com JUnit XML
- Lê XML e sumariza em Markdown
- (Opcional) gera gráfico de barras se matplotlib disponível
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from defusedxml import ElementTree as ET

REPORTS_DIR = "reports"
JUNIT_XML = os.path.join(REPORTS_DIR, "tests_junit.xml")
SUMMARY_MD = os.path.join(REPORTS_DIR, "test_summary.md")
PNG_OUT = os.path.join(REPORTS_DIR, "test_outcomes.png")


def run_pytest():
    cmd = [sys.executable, "-m", "pytest", "-q", f"--junitxml={JUNIT_XML}"]
    print("Running tests:", " ".join(cmd))
    res = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    # Guardar stdout bruto
    with open(
        os.path.join(REPORTS_DIR, "pytest_raw_output.txt"), "w", encoding="utf-8"
    ) as fh:
        fh.write(res.stdout)
    return res.returncode


def parse_junit(path: str):
    tree = ET.parse(path)
    root = tree.getroot()
    # Pytest usa testesuites -> testsuite
    tests = int(root.attrib.get("tests", 0))
    failures = int(root.attrib.get("failures", 0))
    errors = int(root.attrib.get("errors", 0))
    skipped = int(root.attrib.get("skipped", 0))
    # xfail/ xpass não vêm diretos; vamos contar por atributos no nível de testcase
    xfails = 0
    for tc in root.iter("testcase"):
        for ch in tc:
            if (
                ch.tag == "skipped"
                and "xfail" in (ch.attrib.get("message") or "").lower()
            ):
                xfails += 1
    passed = tests - failures - errors - skipped
    return {
        "tests": tests,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "xfails_detected": xfails,
    }


def write_markdown(summary: dict):
    lines = [
        "# Test Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    for k in ["tests", "passed", "failures", "errors", "skipped", "xfails_detected"]:
        lines.append(f"| {k} | {summary[k]} |")
    # Pass rate
    denom = summary["tests"] or 1
    pass_rate = (summary["passed"] / denom) * 100
    lines.append("")
    lines.append(f"Pass rate: {pass_rate:.2f}%")
    with open(SUMMARY_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("Markdown summary written to", SUMMARY_MD)


def maybe_plot(summary: dict):
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        print("matplotlib not installed; skipping chart.")
        return
    labels = ["passed", "failures", "errors", "skipped"]
    values = [summary[label_key] for label_key in labels]
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(labels, values, color=["#2E7D32", "#C62828", "#6D4C41", "#0277BD"])
    ax.set_title("Test Outcomes")
    for i, v in enumerate(values):
        ax.text(i, v + 0.1, str(v), ha="center", va="bottom")
    fig.tight_layout()
    plt.savefig(PNG_OUT, dpi=130)
    print("Chart written to", PNG_OUT)


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    code = run_pytest()
    if not os.path.exists(JUNIT_XML):
        print("JUnit XML not produced, aborting summary.")
        sys.exit(code)
    summary = parse_junit(JUNIT_XML)
    write_markdown(summary)
    maybe_plot(summary)
    # Também salvar JSON simples
    with open(
        os.path.join(REPORTS_DIR, "test_summary.json"), "w", encoding="utf-8"
    ) as fh:
        json.dump(summary, fh, indent=2)
    sys.exit(code)


if __name__ == "__main__":
    main()
