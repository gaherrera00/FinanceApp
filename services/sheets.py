import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import calendar
from datetime import date

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_file(
        "credentials/finance-app-492913-4a8c4dca053f.json", scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource
def get_spreadsheet():
    client = get_client()
    return client.open("FinanceApp")


def get_sheet(name):
    return get_spreadsheet().worksheet(name)


# ===== GASTOS =====
@st.cache_data(ttl=60)
def get_gastos():
    sheet = get_sheet("gastos")
    return sheet.get_all_records()


def append_gasto(row):
    sheet = get_sheet("gastos")
    sheet.append_row(row)
    st.cache_data.clear()


# ===== ORÇAMENTOS =====
@st.cache_data(ttl=60)
def get_orcamentos():
    sheet = get_sheet("orcamentos")
    return sheet.get_all_records()


def upsert_orcamento(categoria, limite):
    sheet = get_sheet("orcamentos")
    records = sheet.get_all_records()

    for i, row in enumerate(records, start=2):
        if row["categoria"] == categoria:
            sheet.update_cell(i, 2, limite)
            st.cache_data.clear()
            return

    sheet.append_row([categoria, limite])
    st.cache_data.clear()


# ===== METAS =====
@st.cache_data(ttl=60)
def get_metas():
    sheet = get_sheet("metas")
    return sheet.get_all_records()


def append_meta(row):
    sheet = get_sheet("metas")
    sheet.append_row(row)
    st.cache_data.clear()


# ===== RENDA =====
# Aba "renda" com colunas: tipo | valor | dia_recebimento | descricao | data_registro
# tipo: "fixo" (recorrente mensal) ou "avulso" (único)


@st.cache_data(ttl=30)
def get_rendas():
    sheet = get_sheet("renda")
    return sheet.get_all_records()


def append_renda(row):
    """Adiciona uma linha na aba renda. row = [tipo, valor, dia_recebimento, descricao, data_registro]"""
    sheet = get_sheet("renda")
    sheet.append_row(row)
    st.cache_data.clear()


def upsert_renda_fixa(valor, dia_recebimento):
    """Atualiza (ou cria) a entrada de renda fixa mensal."""
    sheet = get_sheet("renda")
    records = sheet.get_all_records()

    for i, row in enumerate(records, start=2):
        if row["tipo"] == "fixo":
            sheet.update(
                f"A{i}:E{i}",
                [
                    [
                        "fixo",
                        valor,
                        dia_recebimento,
                        "Renda fixa mensal",
                        str(date.today()),
                    ]
                ],
            )
            st.cache_data.clear()
            return

    sheet.append_row(
        ["fixo", valor, dia_recebimento, "Renda fixa mensal", str(date.today())]
    )
    st.cache_data.clear()


def calcular_renda_mes(mes_period=None):
    """
    Calcula a renda total que DEVE ter sido recebida no mês informado.
    Considera renda fixa (se o dia de recebimento já passou) + avulsos do mês.
    """
    if mes_period is None:
        mes_period = pd.Timestamp.today().to_period("M")

    rendas = get_rendas()
    hoje = date.today()
    total = 0.0
    renda_fixa_valor = 0.0
    renda_fixa_dia = None

    for r in rendas:
        tipo = str(r.get("tipo", "")).strip().lower()
        valor = float(r.get("valor", 0) or 0)
        dia = r.get("dia_recebimento", "")

        if tipo == "fixo":
            renda_fixa_valor = valor
            try:
                renda_fixa_dia = int(dia)
            except (ValueError, TypeError):
                renda_fixa_dia = 1

        elif tipo == "avulso":
            data_str = str(r.get("data_registro", ""))
            try:
                import pandas as pd

                data_reg = pd.to_datetime(data_str)
                if data_reg.to_period("M") == mes_period:
                    total += valor
            except Exception:
                pass

    # Renda fixa: conta só se o dia de recebimento já passou no mês atual
    if renda_fixa_valor > 0 and renda_fixa_dia is not None:
        ano = hoje.year
        mes = hoje.month
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia_real = min(renda_fixa_dia, ultimo_dia)

        if hoje.day >= dia_real:
            total += renda_fixa_valor

    return total, renda_fixa_valor, renda_fixa_dia


def get_renda_fixa_config():
    """Retorna (valor, dia) da renda fixa, ou (0, 1) se não configurada."""
    rendas = get_rendas()
    for r in rendas:
        if str(r.get("tipo", "")).strip().lower() == "fixo":
            try:
                return float(r["valor"]), int(r["dia_recebimento"])
            except (ValueError, TypeError):
                return float(r.get("valor", 0)), 1
    return 0.0, 1
