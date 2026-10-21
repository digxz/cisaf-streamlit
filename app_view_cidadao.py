from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="CISAF - Cidadãos por faixa etária e escolaridade", layout="wide")
st.title("CISAF - Cidadãos por faixa etária e escolaridade")
st.caption("Fonte: view V_QTD_TOTAL_FX_ETARIA_ESCOLARIDADE (T_MDM_CIDADAO), exportada em CSV")

CSV_PADRAO = Path(__file__).parent / "view_qtd_total_fx_etaria_escolaridade.csv"


def ler_csv(origem):
    # sep=None detecta automaticamente vírgula ou ponto e vírgula
    df = pd.read_csv(origem, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = [c.strip().strip('"').lower() for c in df.columns]
    # Aceita QTD_TOTAL ou o alias antigo QTDE_CIDADAOS
    df = df.rename(columns={"qtde_cidadaos": "qtd_total"})
    obrigatorias = {"nm_faixa_etaria", "nm_escolaridade", "qtd_total"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes no CSV: {', '.join(sorted(faltando))}")
    df["qtd_total"] = pd.to_numeric(df["qtd_total"], errors="coerce").fillna(0).astype(int)
    return df


with st.sidebar:
    st.header("Dados")
    enviado = st.file_uploader("Enviar outro CSV (opcional)", type="csv")

try:
    if enviado is not None:
        df = ler_csv(enviado)
    elif CSV_PADRAO.exists():
        df = ler_csv(CSV_PADRAO)
    else:
        st.warning(
            f"Arquivo {CSV_PADRAO.name} não encontrado no repositório. "
            "Suba o CSV exportado da view ou envie pela barra lateral."
        )
        st.stop()
except Exception as e:
    st.error(f"Erro ao ler o CSV: {e}")
    st.stop()

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