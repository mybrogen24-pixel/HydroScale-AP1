"""Utilitários de entrada, apresentação e exportação do HydroScale."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import math

import pandas as pd


def parse_ptbr_number(value: Any) -> float | None:
    """Aceita números brasileiros, ponto decimal e notação científica.

    Campos vazios continuam vazios; a validação de obrigatoriedade fica na
    camada que conhece o contexto do campo.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(" ", "")
    # Trata milhares brasileiros (22.032,75) e US (22,032.75), sem perder 1,19e-6.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def format_br(value: Any, decimals: int = 3, scientific: bool = False) -> str:
    """Formata números somente para visualização, no padrão pt-BR."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    if scientific:
        mantissa, exponent = f"{number:.{decimals}e}".split("e")
        return f"{mantissa.replace('.', ',')}e{int(exponent):+d}"
    formatted = f"{number:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def normalize_experimental_data(table: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Converte a tabela editável em pontos numéricos e relata linhas inválidas."""
    if table is None or table.empty:
        return pd.DataFrame(columns=["Vm", "RTm"]), []
    rename = {}
    for column in table.columns:
        normalized = str(column).strip().lower().replace(" ", "")
        if normalized in {"vm", "vm(m/s)", "velocidade"}:
            rename[column] = "Vm"
        if normalized in {"rtm", "rtm(n)", "resistencia"}:
            rename[column] = "RTm"
    parsed = table.rename(columns=rename)
    if not {"Vm", "RTm"}.issubset(parsed.columns):
        return pd.DataFrame(columns=["Vm", "RTm"]), [
            "A tabela precisa das colunas Vm (m/s) e RTm (N)."
        ]

    records: list[dict[str, float]] = []
    warnings: list[str] = []
    for row_number, row in parsed.iterrows():
        vm = parse_ptbr_number(row["Vm"])
        rtm = parse_ptbr_number(row["RTm"])
        empty_row = vm is None and rtm is None
        if empty_row:
            continue
        if vm is None or rtm is None:
            warnings.append(f"Linha {row_number + 1}: informe Vm e RTm como números válidos.")
            continue
        records.append({"Vm": vm, "RTm": rtm})
    return pd.DataFrame(records, columns=["Vm", "RTm"]), warnings


def results_to_csv(results: pd.DataFrame) -> bytes:
    return results.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def results_to_xlsx(results: pd.DataFrame, inputs: dict[str, Any]) -> bytes:
    """Gera uma planilha portátil, com resultados e parâmetros em abas separadas."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        results.to_excel(writer, index=False, sheet_name="Resultados")
        pd.DataFrame(
            {"Parâmetro": list(inputs.keys()), "Valor": list(inputs.values())}
        ).to_excel(writer, index=False, sheet_name="Características")
    return output.getvalue()

