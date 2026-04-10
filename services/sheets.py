import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


@st.cache_resource
def get_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]


def connect():
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


@st.cache_data(ttl=60)
def get_orcamentos():
    sheet = get_sheet("orcamentos")
    return sheet.get_all_records()


@st.cache_data(ttl=60)
def get_metas():
    sheet = get_sheet("metas")
    return sheet.get_all_records()


# ===== ORÇAMENTOS =====
def get_orcamentos():
    sheet = get_sheet("orcamentos")
    return sheet.get_all_records()


def append_meta(row):
    sheet = get_sheet("metas")
    sheet.append_row(row)
    st.cache_data.clear()


def upsert_orcamento(categoria, limite):
    sheet = get_sheet("orcamentos")
    records = sheet.get_all_records()

    for i, row in enumerate(records, start=2):
        if row["categoria"] == categoria:
            sheet.update_cell(i, 2, limite)
            return

    sheet.append_row([categoria, limite])
