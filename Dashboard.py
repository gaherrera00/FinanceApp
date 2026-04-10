import streamlit as st
import pandas as pd
import plotly.express as px
from services.sheets import get_gastos, get_orcamentos


# ===== CONFIG =====
st.set_page_config(page_title="Dashboard", layout="wide")
st.title("Dashboard")

# ===== CONFIG FIXA (MVP) =====
RENDA = 3000

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
records = get_gastos()
df = pd.DataFrame(records)

df.columns = df.columns.astype(str).str.strip().str.lower()

if "valor" not in df.columns:
    df.columns = ["data", "categoria", "valor"]

df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
df["data"] = pd.to_datetime(df["data"])
df = df.dropna()

# ===== ENRIQUECIMENTO =====
df["tipo"] = df["categoria"].map(TIPO)
df["centro"] = df["categoria"].map(
    {cat: centro for centro, cats in CENTROS.items() for cat in cats}
)

# ===== FILTRO MÊS =====
mes_atual = pd.Timestamp.today().to_period("M")
df["mes"] = df["data"].dt.to_period("M")

df_mes = df[df["mes"] == mes_atual]

# ===== KPIs =====
total = df_mes["valor"].sum()
poupanca = RENDA - total
taxa_poupanca = (poupanca / RENDA * 100) if RENDA > 0 else 0

# ===== AGRUPAMENTOS =====
grouped = df_mes.groupby("categoria")["valor"].sum().sort_values(ascending=False)
grouped_tipo = df_mes.groupby("tipo")["valor"].sum()

# ===== MÊS ANTERIOR =====
mes_anterior = mes_atual - 1
df_ant = df[df["mes"] == mes_anterior]

total_ant = df_ant["valor"].sum()
variacao = ((total - total_ant) / total_ant * 100) if total_ant > 0 else 0

# ===== ORÇAMENTOS =====
orcamentos = get_orcamentos()
orc_dict = {o["categoria"]: float(o["limite"]) for o in orcamentos}

# ===== SCORE =====
score = 100
estourou = False

for cat in grouped.index:
    gasto = grouped.get(cat, 0)
    limite = orc_dict.get(cat, 0)

    if limite > 0 and gasto > limite:
        score -= 20
        estourou = True

sup = grouped_tipo.get("supérfluo", 0)
perc_sup = (sup / total * 100) if total > 0 else 0

if perc_sup > 40:
    score -= 20

if taxa_poupanca < 10:
    score -= 30

score = max(score, 0)

# ===== TOPO =====
col1, col2, col3 = st.columns(3)

col1.metric("Total gasto", brl(total))
col2.metric("Score financeiro", score)
col3.metric("Poupança", f"{taxa_poupanca:.1f}%".replace(".", ","))

# ===== ALERTAS =====
if estourou:
    st.error("Você estourou um ou mais orçamentos")

if variacao > 10:
    st.warning("Seus gastos aumentaram vs mês passado")

if taxa_poupanca < 10:
    st.error("Baixa capacidade de poupança")

# ===== CONTROLE =====
st.subheader("Orçamento por categoria")

if len(grouped) > 0:
    cols = st.columns(len(grouped))

    for i, cat in enumerate(grouped.index):
        with cols[i]:
            gasto = grouped.get(cat, 0)
            limite = orc_dict.get(cat, 0)

            percentual = (gasto / limite * 100) if limite > 0 else 0

            st.markdown(f"**{cat.upper()}**")

            st.metric(
                "Gasto",
                brl(gasto),
                f"{percentual:.1f}%".replace(".", ","),
                delta_color="inverse" if percentual >= 100 else "normal",
            )

            st.progress(min(percentual / 100, 1.0))
            st.caption(f"{brl(gasto)} / {brl(limite)}")

# ===== INSIGHTS =====
st.subheader("Insights")

col1, col2, col3 = st.columns(3)

with col1:
    if len(grouped) > 0:
        st.metric("Maior gasto", grouped.idxmax())

with col2:
    st.metric("Supérfluo (%)", f"{perc_sup:.1f}%".replace(".", ","))

with col3:
    st.metric("Variação mensal", f"{variacao:.1f}%".replace(".", ","))

# ===== GASTO POR DIA =====
st.subheader("Gasto por dia")

gasto_dia = df_mes.groupby(df_mes["data"].dt.date)["valor"].sum()
st.line_chart(gasto_dia)

# ===== GRÁFICO =====
st.subheader("Distribuição")

if len(grouped) > 0:
    fig = px.pie(values=grouped.values, names=grouped.index)
    st.plotly_chart(fig, use_container_width=True)

# ===== CTA =====
if st.button("+ Registrar gasto"):
    st.switch_page("pages/1_Registrar.py")
