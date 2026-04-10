import streamlit as st
import pandas as pd
import calendar
from datetime import date
from services.sheets import get_gastos, get_metas, append_meta, calcular_renda_mes

st.set_page_config(page_title="Planejamento", layout="wide")

st.markdown(
    """
    <h1 style='text-align:center; font-weight:600; margin-bottom:5px;'>
        Planejamento Financeiro
    </h1>
    """,
    unsafe_allow_html=True,
)


def brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ===== DADOS =====
try:
    records = get_gastos()
except Exception:
    records = []

if records:
    df = pd.DataFrame(records)
    df.columns = df.columns.astype(str).str.strip().str.lower()

    if "valor" not in df.columns:
        df.columns = ["data", "categoria", "valor"]

    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["valor", "data"])
else:
    df = pd.DataFrame(columns=["data", "categoria", "valor"])

# ===== FILTRO MÊS =====
mes_atual = pd.Timestamp.today().to_period("M")

if not df.empty:
    df["mes"] = df["data"].dt.to_period("M")
    df_mes = df[df["mes"] == mes_atual]
else:
    df_mes = pd.DataFrame(columns=["data", "categoria", "valor"])

# ===== RENDA =====
try:
    RENDA, _, _ = calcular_renda_mes(mes_atual)
except Exception:
    RENDA = 0.0

if RENDA == 0:
    st.warning("Renda não configurada")

total = float(df_mes["valor"].sum()) if not df_mes.empty else 0.0
poupanca = RENDA - total

# ================= PROJEÇÃO =================
st.markdown("### Projeção")

if not df_mes.empty:
    gasto_dia = df_mes.groupby(df_mes["data"].dt.date)["valor"].sum()
    media_diaria = float(gasto_dia.mean())

    hoje = date.today()
    dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
    dias_restantes = dias_no_mes - hoje.day

    projecao = total + (media_diaria * dias_restantes)

    col1, col2 = st.columns(2)

    col1.metric("Projeção mensal", brl(projecao))
    col2.metric("Saldo projetado", brl(RENDA - projecao))

    if RENDA > 0 and projecao > RENDA:
        st.error("Gastos acima da renda projetada")
    elif RENDA > 0:
        st.success("Projeção dentro da renda")
else:
    st.info("Sem dados suficientes para projeção")

st.divider()

# ================= META =================
st.markdown("### Criar meta")

col1, col2, col3 = st.columns(3)

with col1:
    nome = st.text_input("Nome")

with col2:
    valor_total = st.number_input("Valor total", min_value=0.0, step=100.0)

with col3:
    prazo = st.number_input("Prazo (meses)", min_value=1, step=1)

if st.button("Salvar meta"):
    if nome and valor_total > 0:
        append_meta([nome, valor_total, prazo, str(date.today())])
        st.success("Meta criada")
    else:
        st.error("Dados inválidos")

st.divider()

# ================= METAS =================
st.markdown("### Suas metas")

try:
    metas = get_metas()
except Exception:
    metas = []

if not metas:
    st.info("Nenhuma meta cadastrada")
else:
    for meta in metas:
        try:
            nome = meta["nome"]
            valor_total = float(meta["valor_total"])
            prazo = int(meta["prazo_meses"])
        except:
            continue

        if valor_total <= 0 or prazo <= 0:
            continue

        valor_mensal = valor_total / prazo
        economizado = max(poupanca, 0)
        percentual = (economizado / valor_total * 100) if valor_total > 0 else 0.0
        falta = valor_total - economizado

        st.markdown(f"#### {nome}")

        col1, col2, col3 = st.columns(3)

        col1.metric("Total", brl(valor_total))
        col2.metric("Mensal", brl(valor_mensal))
        col3.metric("Progresso", f"{percentual:.1f}%".replace(".", ","))

        st.progress(min(percentual / 100, 1.0))
        st.caption(f"Falta: {brl(falta)}")

        if economizado < valor_mensal:
            st.error("Abaixo do ritmo da meta")

st.divider()

# ================= NAV =================
if st.button("Voltar"):
    st.switch_page("Dashboard.py")
