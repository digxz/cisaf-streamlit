import os

import oracledb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="CISAF - Cidadãos por faixa etária e escolaridade", layout="wide")
st.title("CISAF - Cidadãos por faixa etária e escolaridade")
st.caption("Fonte: view V_QTD_TOTAL_FX_ETARIA_ESCOLARIDADE (T_MDM_CIDADAO)")

# ------------------------------------------------------------
# Credenciais: .streamlit/secrets.toml, variáveis de ambiente
# ou preenchimento manual na barra lateral
# ------------------------------------------------------------
def cred(chave, padrao=""):
    try:
        return st.secrets["oracle"][chave]
    except Exception:
        return os.getenv("ORACLE_" + chave.upper(), padrao)


with st.sidebar:
    st.header("Conexão Oracle")
    user = st.text_input("Usuário", cred("user"))
    password = st.text_input("Senha", cred("password"), type="password")
    dsn = st.text_input("DSN (host:porta/servico)", cred("dsn"))
    consultar = st.button("Consultar", type="primary")


@st.cache_data(ttl=60, show_spinner="Consultando o Oracle...")
def carregar(user, password, dsn):
    # Modo thin do python-oracledb: não precisa de Oracle Client instalado
    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        return pd.read_sql(
            "SELECT nm_faixa_etaria, nm_escolaridade, qtd_total "
            "FROM v_qtd_total_fx_etaria_escolaridade",
            conn,
        )


if consultar or (user and password and dsn):
    try:
        df = carregar(user, password, dsn)
    except Exception as e:
        st.error(f"Erro ao consultar a view: {e}")
        st.stop()

    df.columns = [c.lower() for c in df.columns]
    df = df.sort_values("qtd_total", ascending=False)

    c1, c2 = st.columns(2)
    c1.metric("Total de cidadãos", int(df["qtd_total"].sum()))
    c2.metric("Combinações faixa x escolaridade", len(df))

    faixas = sorted(df["nm_faixa_etaria"].dropna().unique())
    escolhidas = st.multiselect("Filtrar faixa etária", faixas, default=faixas)
    filtrado = df[df["nm_faixa_etaria"].isin(escolhidas)]

    st.subheader("Resultado da view")
    st.dataframe(filtrado, use_container_width=True, hide_index=True)

    st.subheader("Quantidade por faixa etária e escolaridade")
    grafico = filtrado.pivot_table(
        index="nm_faixa_etaria",
        columns="nm_escolaridade",
        values="qtd_total",
        aggfunc="sum",
        fill_value=0,
    )
    st.bar_chart(grafico)
else:
    st.info("Informe usuário, senha e DSN na barra lateral e clique em Consultar.")