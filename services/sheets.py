import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import calendar
from datetime import date

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Cabeçalhos padrão por aba — criados automaticamente se a aba não existir
_ABA_HEADERS = {
    "gastos": ["data", "categoria", "valor", "tipo", "centro"],
    "orcamentos": ["categoria", "limite"],
    "metas": ["nome", "valor_total", "prazo_meses", "data_inicio"],
    "renda": ["tipo", "valor", "dia_recebimento", "descricao", "data_registro"],
}


@st.cache_resource
def get_client():
    try:
        # Produção (Streamlit Cloud): lê dos secrets
        secret = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(secret, scopes=SCOPES)
    except Exception:
        # Local: lê do arquivo JSON
        creds = Credentials.from_service_account_file(
            "credentials/finance-app-492913-4a8c4dca053f.json", scopes=SCOPES
        )
    return gspread.authorize(creds)


@st.cache_resource
def get_spreadsheet():
    return get_client().open("FinanceApp")


def get_sheet(name):
    """Retorna a worksheet. Se não existir, cria com cabeçalhos automaticamente."""
    spreadsheet = get_spreadsheet()
    try:
        return spreadsheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
        headers = _ABA_HEADERS.get(name, [])
        if headers:
            sheet.append_row(headers)
        return sheet


# ===== GASTOS =====
@st.cache_data(ttl=60)
def get_gastos():
    sheet = get_sheet("gastos")
    return sheet.get_all_records()


def append_gasto(row):
    sheet = get_sheet("gastos")
    sheet.append_row(row)
    st.cache_data.clear()


# ===== ORCAMENTOS =====
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
# Aba "renda" — colunas: tipo | valor | dia_recebimento | descricao | data_registro
# tipo "fixo"   -> renda recorrente mensal
# tipo "avulso" -> pagamento unico (bonus, freela, etc.)


@st.cache_data(ttl=30)
def get_rendas():
    sheet = get_sheet("renda")
    return sheet.get_all_records()


def append_renda(row):
    """row = [tipo, valor, dia_recebimento, descricao, data_registro]"""
    sheet = get_sheet("renda")
    sheet.append_row(row)
    st.cache_data.clear()


def upsert_renda_fixa(valor, dia_recebimento):
    """Atualiza a linha de renda fixa ou cria se nao existir."""
    sheet = get_sheet("renda")
    records = sheet.get_all_records()

    for i, row in enumerate(records, start=2):
        if str(row.get("tipo", "")).strip().lower() == "fixo":
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


def get_renda_fixa_config():
    """Retorna (valor, dia) da renda fixa, ou (0.0, 1) se nao configurada."""
    rendas = get_rendas()
    for r in rendas:
        if str(r.get("tipo", "")).strip().lower() == "fixo":
            try:
                return float(r["valor"]), int(r["dia_recebimento"])
            except (ValueError, TypeError):
                return float(r.get("valor", 0)), 1
    return 0.0, 1


def calcular_renda_mes(mes_period=None):
    """
    Calcula a renda total do mes informado.
    - Renda fixa: conta se o dia de recebimento ja passou no mes atual.
    - Avulsos: soma apenas os registrados no mes informado.
    Retorna: (total, renda_fixa_valor, renda_fixa_dia)
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
                data_reg = pd.to_datetime(data_str)
                if data_reg.to_period("M") == mes_period:
                    total += valor
            except Exception:
                pass

    # Renda fixa so entra se o dia de recebimento ja passou este mes
    if renda_fixa_valor > 0 and renda_fixa_dia is not None:
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        dia_real = min(renda_fixa_dia, ultimo_dia)
        if hoje.day >= dia_real:
            total += renda_fixa_valor

    return total, renda_fixa_valor, renda_fixa_dia
