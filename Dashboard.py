import streamlit as st
import pandas as pd
import plotly.express as px
from services.sheets import get_gastos, get_orcamentos, calcular_renda_mes

# ===== CONFIG =====
st.set_page_config(page_title="Dashboard", layout="wide")

st.markdown(
    """
    <h1 style='text-align:center; font-weight:600; margin-bottom:5px;'>
        Dashboard Financeiro
    </h1>
    """,
    unsafe_allow_html=True,
)

CENTROS = {
    "Essencial": ["fixo", "comida"],
    "Não essencial": ["lazer"],
    "Investimento": ["estudo"],
}

TIPO = {
    "fixo": "essencial",
    "comida": "essencial",
    "lazer": "supérfluo",
    "estudo": "investimento",
}


def brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ===== DADOS =====
try:
    records = get_gastos()
except Exception as e:
    st.error("Falha ao carregar dados")
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

# ===== ENRIQUECIMENTO =====
mes_atual = pd.Timestamp.today().to_period("M")

if not df.empty:
    df["tipo"] = df["categoria"].map(TIPO)
    df["centro"] = df["categoria"].map(
        {cat: centro for centro, cats in CENTROS.items() for cat in cats}
    )
    df["mes"] = df["data"].dt.to_period("M")
    df_mes = df[df["mes"] == mes_atual]
else:
    df_mes = pd.DataFrame()

# ===== RENDA =====
try:
    RENDA, _, _ = calcular_renda_mes(mes_atual)
except Exception:
    RENDA = 0.0

if RENDA == 0:
    st.warning("Configure sua renda em Registrar → Configuração de renda")

# ===== KPIs =====
total = float(df_mes["valor"].sum()) if not df_mes.empty else 0.0
poupanca = RENDA - total
taxa_poupanca = (poupanca / RENDA * 100) if RENDA > 0 else 0.0

# ===== AGRUPAMENTOS =====
if not df_mes.empty:
    grouped = df_mes.groupby("categoria")["valor"].sum().sort_values(ascending=False)
    grouped_tipo = df_mes.groupby("tipo")["valor"].sum()
else:
    grouped = pd.Series(dtype=float)
    grouped_tipo = pd.Series(dtype=float)

# ===== MÊS ANTERIOR =====
mes_anterior = mes_atual - 1
df_ant = (
    df[df["mes"] == mes_anterior]
    if not df.empty and "mes" in df.columns
    else pd.DataFrame()
)
total_ant = float(df_ant["valor"].sum()) if not df_ant.empty else 0.0

variacao = ((total - total_ant) / total_ant * 100) if total_ant > 0 else 0.0

# ===== ORÇAMENTOS =====
try:
    orcamentos = get_orcamentos()
    orc_dict = {o["categoria"]: float(o["limite"]) for o in orcamentos}
except Exception:
    orc_dict = {}

# ===== SCORE =====
score = 100
estourou = False

for cat in grouped.index:
    gasto = float(grouped.get(cat, 0))
    limite = orc_dict.get(cat, 0)

    if limite > 0 and gasto > limite:
        score -= 20
        estourou = True

sup = float(grouped_tipo.get("supérfluo", 0)) if not grouped_tipo.empty else 0.0
perc_sup = (sup / total * 100) if total > 0 else 0.0

if perc_sup > 40:
    score -= 20

if taxa_poupanca < 10:
    score -= 30

score = max(score, 0)

# ===== KPI =====
st.markdown("### Visão geral")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Renda", brl(RENDA))
col2.metric("Gastos", brl(total))
col3.metric("Score", score)

col4.metric(
    "Poupança",
    brl(poupanca),
    f"{taxa_poupanca:.1f}%".replace(".", ","),
    delta_color="inverse" if poupanca < 0 else "normal",
)

st.divider()

# ===== ALERTAS =====
if estourou:
    st.error("Orçamento ultrapassado")

if variacao > 10:
    st.warning("Aumento de gastos em relação ao mês anterior")

if taxa_poupanca < 10 and RENDA > 0:
    st.error("Baixa capacidade de poupança")

st.divider()

# ===== ORÇAMENTO =====
st.markdown("### Orçamento por categoria")

if grouped.empty:
    st.info("Sem gastos registrados neste mês")
else:
    cols = st.columns(len(grouped))

    for i, cat in enumerate(grouped.index):
        with cols[i]:
            gasto = float(grouped.get(cat, 0))
            limite = orc_dict.get(cat, 0)
            percentual = (gasto / limite * 100) if limite > 0 else 0.0

            st.markdown(
                f"<div style='font-weight:600; font-size:13px;'>{cat.upper()}</div>",
                unsafe_allow_html=True,
            )

            st.metric(
                "Gasto",
                brl(gasto),
                f"{percentual:.1f}%".replace(".", ","),
                delta_color="inverse" if percentual >= 100 else "normal",
            )

            st.progress(min(percentual / 100, 1.0))
            st.caption(f"{brl(gasto)} / {brl(limite)}")

st.divider()

# ===== INSIGHTS =====
st.markdown("### Insights")

col1, col2, col3 = st.columns(3)

col1.metric("Maior gasto", grouped.idxmax() if not grouped.empty else "—")
col2.metric("Supérfluo", f"{perc_sup:.1f}%".replace(".", ","))
col3.metric("Variação", f"{variacao:.1f}%".replace(".", ","))

st.divider()

# ===== GRÁFICOS =====
st.markdown("### Evolução")

if not df_mes.empty:
    gasto_dia = df_mes.groupby(df_mes["data"].dt.date)["valor"].sum()
    st.line_chart(gasto_dia)
else:
    st.info("Sem dados para evolução")

st.markdown("### Distribuição")

if not grouped.empty:
    fig = px.pie(values=grouped.values, names=grouped.index)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para distribuição")

st.divider()

# ===== CTA =====
if st.button("Registrar gasto"):
    st.switch_page("pages/1_Registrar.py")
