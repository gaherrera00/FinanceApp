import streamlit as st
from datetime import date
import calendar
from services.sheets import (
    append_gasto,
    get_orcamentos,
    upsert_orcamento,
    upsert_renda_fixa,
    append_renda,
    get_renda_fixa_config,
)

st.set_page_config(page_title="Registrar", layout="wide")

st.markdown(
    """
    <h1 style='text-align:center; font-weight:600; margin-bottom:5px;'>
        Registro Financeiro
    </h1>
    """,
    unsafe_allow_html=True,
)

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


def brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ================= GASTO =================
st.markdown("### Novo gasto")

col1, col2, col3 = st.columns(3)

with col1:
    categoria = st.selectbox(
        "Categoria", categorias, index=None, placeholder="Selecionar"
    )

with col2:
    valor = st.number_input("Valor", min_value=0.0, step=0.01)

with col3:
    data = st.date_input("Data", value=date.today())

if st.button("Salvar gasto"):
    if categoria is None or valor == 0:
        st.error("Preencha corretamente")
    else:
        append_gasto(
            [str(data), categoria, valor, TIPO.get(categoria), CENTROS.get(categoria)]
        )
        st.success("Gasto registrado")
st.divider()

# ================= FAST INPUT =================
st.markdown("### Registro rápido")

cols = st.columns(len(categorias))

for i, cat in enumerate(categorias):
    with cols[i]:
        if st.button(f"+20 {cat}", key=f"fast_{cat}"):
            append_gasto([str(date.today()), cat, 20, TIPO.get(cat), CENTROS.get(cat)])
            st.success(f"{cat} +20 registrado")

st.divider()

# ================= ORÇAMENTO =================
st.markdown("### Orçamento")

orcamentos = get_orcamentos()
orc_dict = {o["categoria"]: float(o["limite"]) for o in orcamentos}

for cat in categorias:
    st.number_input(
        cat.upper(),
        min_value=0.0,
        value=orc_dict.get(cat, 0.0),
        step=10.0,
        key=f"budget_{cat}",
    )

if st.button("Salvar orçamentos", key="save_budgets"):
    for cat in categorias:
        upsert_orcamento(cat, st.session_state[f"budget_{cat}"])
    st.success("Orçamentos atualizados")

st.divider()

# ================= RENDA =================
st.markdown("### Configuração de renda")

renda_fixa_atual, dia_atual = get_renda_fixa_config()

col1, col2 = st.columns(2)

with col1:
    novo_valor_renda = st.number_input(
        "Renda mensal (R$)",
        min_value=0.0,
        value=renda_fixa_atual,
        step=50.0,
        key="renda_fixa_valor",
    )

with col2:
    novo_dia_renda = st.number_input(
        "Dia de recebimento",
        min_value=1,
        max_value=31,
        value=int(dia_atual) if dia_atual else 1,
        step=1,
        key="renda_fixa_dia",
    )

hoje = date.today()
ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)[1]
dia_real = min(int(novo_dia_renda), ultimo_dia_mes)

if dia_real >= hoje.day:
    dias_faltando = dia_real - hoje.day

    if dias_faltando == 0:
        st.info("Hoje é dia de recebimento")
    else:
        st.info(f"Próximo recebimento em {dias_faltando} dia(s)")
else:
    st.info("Ciclo de renda concluído neste mês")

if st.button("Atualizar renda fixa", key="save_renda_fixa"):
    if novo_valor_renda <= 0:
        st.error("Valor inválido")
    else:
        upsert_renda_fixa(novo_valor_renda, int(novo_dia_renda))
        st.success("Renda atualizada")
        st.rerun()

st.divider()

# ================= RENDA AVULSA =================
st.markdown("### Renda avulsa")

col1, col2, col3 = st.columns(3)

with col1:
    avulso_valor = st.number_input(
        "Valor", min_value=0.0, step=10.0, key="avulso_valor"
    )

with col2:
    avulso_data = st.date_input("Data", value=date.today(), key="avulso_data")

with col3:
    avulso_descricao = st.text_input("Descrição", key="avulso_desc")

if st.button("Adicionar renda", key="save_avulso"):
    if avulso_valor <= 0:
        st.error("Valor inválido")
    else:
        descricao = avulso_descricao.strip() or "Renda avulsa"
        append_renda(["avulso", avulso_valor, "", descricao, str(avulso_data)])
        st.success("Renda adicionada")
        st.rerun()

st.divider()

# ================= NAV =================
if st.button("Voltar"):
    st.switch_page("Dashboard.py")
