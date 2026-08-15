"""Shared SSA status labels used by GUI and textual renderers."""

from __future__ import annotations

SSA_STATUS_DESCRIPTIONS = {
    "AAD": "Aguardando Atualizacao de Desenhos",
    "AAT": "Aguardando Atendimento de Terceiros",
    "ACC": "Aguardando Condicoes Climaticas",
    "ACS": "Aguardando Condicoes do Sistema",
    "ADI": "Aguardando Aprovacao da Divisao na Emissao",
    "ADM": "Aguardando Departamento de Manutencao",
    "AIM": "Aguardando Departamento de Engenharia de Manutencao",
    "AIP": "Aguardando Liberacao do Equipamento",
    "AMP": "Aguardando Manutencao Periodica",
    "APG": "Aguardando Programacao",
    "APL": "Aguardando Planejamento",
    "APV": "Aguardando Provisionamento",
    "ASE": "Aguardando Aprovacao do Setor na Emissao",
    "ASI": "Aguardando Servicos de Laboratorio",
    "ASO": "Aguardando Servicos de Oficina",
    "SAD": "Aguardando Aprovacao da Divisao na Execucao",
    "SAS": "Aguardando Aprovacao do Setor na Execucao",
    "SCA": "Servico Cancelado",
    "SCD": "Cancelada Aguardando Aprovacao da Divisao",
    "SCS": "Cancelada Aguardando Aprovacao do Setor",
    "SEE": "Servico em Execucao",
    "SES": "Servico com Execucao Simples",
    "SPG": "Servico Programado",
    "SRP": "Servico Reprogramado",
    "STE": "Servico Terminado",
}


def get_status_code(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.split(" - ", 1)[0].strip().upper()


def format_status_display(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    code = get_status_code(text)
    desc = SSA_STATUS_DESCRIPTIONS.get(code)
    if not desc:
        return text
    return f"{code} - {desc}"
