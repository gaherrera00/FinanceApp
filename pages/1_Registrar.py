import streamlit as st
from datetime import date
from services.sheets import append_gasto, get_orcamentos, upsert_orcamento


st.set_page_config(page_title="Registrar", layout="wide")
st.title("Registrar gasto")

# ===== CONFIG =====
categorias = ["fixo", "comida", "lazer", "estudo"]

CENTROS = {
    "fixo": "Essencial",
    "comida": "Essencial",
    "lazer": "Não essencial",
    "estudo": "Investimento",
}

TIPO = {
    "fixo": "essencial",
    "comida": "essencial",
    "lazer": "supérfluo",
    "estudo": "investimento",
}

# ===== FORM PRINCIPAL =====
st.subheader("Novo gasto")

col1, col2, col3 = st.columns(3)

with col1:
    categoria = st.selectbox("Categoria", categorias, index=None, placeholder="Escolha")

with col2:
    valor = st.number_input("Valor", min_value=0.0, step=0.01)

with col3:
    data = st.date_input("Data", value=date.today())

if st.button("Salvar gasto"):
    if categoria is None or valor == 0:
        st.error("Preencha corretamente")
    else:
        tipo = TIPO.get(categoria)
        centro = CENTROS.get(categoria)

        append_gasto([str(data), categoria, valor, tipo, centro])

        st.success("Salvo")

# ===== INPUT RÁPIDO (UX) =====
st.subheader("Registro rápido")

cols = st.columns(len(categorias))

for i, cat in enumerate(categorias):
    with cols[i]:
        if st.button(f"+20 {cat}", key=f"fast_{cat}"):
            append_gasto([str(date.today()), cat, 20, TIPO.get(cat), CENTROS.get(cat)])
            st.success(f"+20 em {cat}")

# ===== ORÇAMENTO =====
st.subheader("Orçamento por categoria")

orcamentos = get_orcamentos()
orc_dict = {o["categoria"]: float(o["limite"]) for o in orcamentos}

for cat in categorias:
    st.number_input(
        f"{cat}",
        min_value=0.0,
        value=orc_dict.get(cat, 0.0),
        step=10.0,
        key=f"budget_{cat}",
    )

if st.button("Salvar orçamentos", key="save_budgets"):
    for cat in categorias:
        upsert_orcamento(cat, st.session_state[f"budget_{cat}"])

    st.success("Orçamentos atualizados")

# ===== VOLTAR =====
if st.button("← Voltar para Dashboard"):
    st.switch_page("Dashboard.py")
