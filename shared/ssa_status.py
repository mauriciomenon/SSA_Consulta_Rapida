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
    "ALE": "Aguardando Liberacao do Equipamento",
    "AMP": "Aguardando Manutencao Periodica",
    "APG": "Aguardando Programacao",
    "APL": "Aguardando Planejamento",
    "APV": "Aguardando Provisionamento",
    "ASE": "Aguardando Aprovacao do Setor na Emissao",
    "ASL": "Aguardando Servicos de Laboratorio",
    "ASO": "Aguardando Servicos de Oficina",
    "SAD": "Aguardando Aprovacao da Divisao na Execucao",
    "SAS": "Aguardando Aprovacao do Setor na Execucao",
    "SCA": "Servico Cancelado",
    "SCC": "Cancelada no Cadastramento",
    "SCD": "Cancelada Aguardando Aprovacao da Divisao",
    "SCS": "Cancelada Aguardando Aprovacao do Setor",
    "SEE": "Servico em Execucao",
    "SES": "Servico com Execucao Simples",
    "SPG": "Servico Programado",
    "SRP": "Servico Reprogramado",
    "STE": "Servico Terminado",
}

# Codigos e nomes pelo Manual G05 (3.9.x); AIP/ASI nao existem no SAM (sao ALE/ASL).
SSA_STATUS_CODES = frozenset(SSA_STATUS_DESCRIPTIONS)

# DEC-01/DEC-02 (RD-01a): encerrada = nunca sai do estado. STE e SES encerram
# normalmente; SCA e SCC sao encerramento anormal. Unica definicao para
# "Ocultar", macro "para baixar", derivadas encerradas e ordenacao padrao.
SSA_ENCERRADAS_NORMAL = frozenset({"STE", "SES"})
SSA_ENCERRADAS_ANORMAL = frozenset({"SCA", "SCC"})
SSA_ENCERRADAS = SSA_ENCERRADAS_NORMAL | SSA_ENCERRADAS_ANORMAL
SSA_ENCERRADAS_LABEL = "STE/SES/SCA/SCC"

SSA_ACCEPTED_STATUS_VALUES = SSA_STATUS_CODES | {
    "ABERTA",
    "ABERTO",
    "EM ANDAMENTO",
    "EM_ANALISE",
    "EM_EXECUCAO",
    "EXECUTADA",
    "FECHADA",
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


def status_code_series(series):
    """Versao vetorizada de get_status_code para uma pandas.Series."""
    return (
        series.astype("string")
        .fillna("")
        .str.split(" - ", n=1)
        .str[0]
        .str.strip()
        .str.upper()
    )


def is_encerrada(value) -> bool:
    return get_status_code(value) in SSA_ENCERRADAS
