import streamlit as st
import pandas as pd
from datetime import date
from services.sheets import get_gastos, get_metas, append_meta


st.set_page_config(page_title="Planejamento", layout="wide")
st.title("Planejamento")

RENDA = 3000


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

# ===== FILTRO MÊS =====
mes_atual = pd.Timestamp.today().to_period("M")
df["mes"] = df["data"].dt.to_period("M")

df_mes = df[df["mes"] == mes_atual]

total = df_mes["valor"].sum()
poupanca = RENDA - total

# ===== PROJEÇÃO =====
st.subheader("Projeção")

if len(df_mes) > 0:
    gasto_dia = df_mes.groupby(df_mes["data"].dt.date)["valor"].sum()
    media_diaria = gasto_dia.mean()

    dias_restantes = 30 - date.today().day
    projecao = total + (media_diaria * dias_restantes)

    st.metric("Projeção do mês", brl(projecao))

    if projecao > RENDA:
        st.error("Se continuar assim, você vai gastar mais do que ganha")
else:
    st.info("Sem dados suficientes para projeção")

# ===== FORM META =====
st.subheader("Criar meta")

col1, col2, col3 = st.columns(3)

with col1:
    nome = st.text_input("Nome da meta")

with col2:
    valor_total = st.number_input("Valor total", min_value=0.0, step=100.0)

with col3:
    prazo = st.number_input("Prazo (meses)", min_value=1, step=1)

if st.button("Salvar meta"):
    if nome and valor_total > 0:
        append_meta([nome, valor_total, prazo, str(date.today())])
        st.success("Meta criada")
    else:
        st.error("Preencha corretamente")

# ===== METAS =====
st.subheader("Suas metas")

metas = get_metas()

if len(metas) == 0:
    st.info("Nenhuma meta cadastrada")

for meta in metas:
    nome = meta["nome"]
    valor_total = float(meta["valor_total"])
    prazo = int(meta["prazo_meses"])

    valor_mensal = valor_total / prazo

    economizado = max(poupanca, 0)
    percentual = (economizado / valor_total * 100) if valor_total > 0 else 0

    st.markdown(f"### {nome}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Meta total", brl(valor_total))

    with col2:
        st.metric("Meta mensal", brl(valor_mensal))

    with col3:
        st.metric("Progresso", f"{percentual:.1f}%".replace(".", ","))

    st.progress(min(percentual / 100, 1.0))

    falta = valor_total - economizado
    st.caption(f"Falta: {brl(falta)}")

    # ===== ALERTA =====
    if economizado < valor_mensal:
        st.error("Você não está no ritmo da meta")

# ===== VOLTAR =====
if st.button("← Voltar para Dashboard"):
    st.switch_page("app.py")
