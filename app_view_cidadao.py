import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="CISAF - Cidadãos (Prefeitura)", layout="wide")
st.title("CISAF - Perfil dos cidadãos cadastrados na Prefeitura")
st.caption("Fonte: SRC_PREF__CIDADAO_CISAF.csv (dados de origem, antes da carga no MDM)")

CSV_PADRAO = Path(__file__).parent / "SRC_PREF__CIDADAO_CISAF.csv"
SEXO = {"1": "MASCULINO", "M": "MASCULINO", "MASCULINO": "MASCULINO",
        "2": "FEMININO", "F": "FEMININO", "FEMININO": "FEMININO"}
ORDEM_FAIXA = ["CRIANCA", "ADOLESCENTE", "ADULTO", "IDOSO", "NAO_INFORMADO"]


def sem_acento(txt):
    if pd.isna(txt):
        return txt
    return unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode().upper().strip()


def faixa(idade):
    if pd.isna(idade) or idade < 0 or idade > 130:
        return "NAO_INFORMADO"
    if idade <= 12:
        return "CRIANCA"
    if idade <= 17:
        return "ADOLESCENTE"
    if idade <= 59:
        return "ADULTO"
    return "IDOSO"


def mascara_cpf(cpf):
    d = re.sub(r"\D", "", str(cpf))
    return f"***.{d[3:6]}.{d[6:9]}-**" if len(d) == 11 else "INVALIDO"


@st.cache_data
def preparar(origem):
    df = pd.read_csv(origem, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    df.columns = [c.strip().upper() for c in df.columns]
    obrig = {"CPF_PREFEITURA", "DT_NASC_PREF", "SEXO_PREF", "MUNICIPIO_PREF",
             "TIPO_RESIDENCIA", "PROGRAMA_SOCIAL", "NUM_NIS", "TELEFONE_PREF"}
    faltando = obrig - set(df.columns)
    if faltando:
        raise ValueError("Colunas ausentes: " + ", ".join(sorted(faltando)))

    # Prefeitura grava a data em DD/MM/YYYY
    nasc = pd.to_datetime(df["DT_NASC_PREF"], format="%d/%m/%Y", errors="coerce")
    hoje = pd.Timestamp(date.today())
    idade = ((hoje - nasc).dt.days // 365.25).astype("Float64")

    out = pd.DataFrame({
        "cpf": df["CPF_PREFEITURA"].map(mascara_cpf),
        "idade": idade,
        "faixa_etaria": idade.map(faixa),
        "sexo": df["SEXO_PREF"].str.upper().str.strip().map(SEXO).fillna("NAO_INFORMADO"),
        "municipio": df["MUNICIPIO_PREF"].map(sem_acento),
        "tipo_residencia": df["TIPO_RESIDENCIA"].map(sem_acento),
        "programa_social": df["PROGRAMA_SOCIAL"].map(sem_acento),
    })
    qualidade = {
        "Data de nascimento ausente/inválida": int(nasc.isna().sum()),
        "Sexo fora do domínio (1/2)": int((out["sexo"] == "NAO_INFORMADO").sum()),
        "Telefone ausente": int((df["TELEFONE_PREF"].str.strip() == "").sum()),
        "NIS ausente": int((df["NUM_NIS"].str.strip() == "").sum()),
    }
    return out, qualidade, len(df)


with st.sidebar:
    st.header("Dados")
    enviado = st.file_uploader("Enviar outro CSV (opcional)", type="csv")

try:
    if enviado is not None:
        df, qualidade, total = preparar(enviado)
    elif CSV_PADRAO.exists():
        df, qualidade, total = preparar(CSV_PADRAO)
    else:
        st.warning(f"Arquivo {CSV_PADRAO.name} não encontrado. Suba-o no repositório ou envie pela barra lateral.")
        st.stop()
except Exception as e:
    st.error(f"Erro ao ler o CSV: {e}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cidadãos", total)
c2.metric("Idade média", f"{df['idade'].dropna().astype(float).mean():.1f}")
c3.metric("Municípios", df["municipio"].nunique())
c4.metric("Em programa social", int((df["programa_social"] != "NENHUM").sum()))

faixas = [f for f in ORDEM_FAIXA if f in set(df["faixa_etaria"])]
escolhidas = st.multiselect("Filtrar faixa etária", faixas, default=faixas)
f = df[df["faixa_etaria"].isin(escolhidas)]

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Faixa etária x sexo")
    st.bar_chart(f.pivot_table(index="faixa_etaria", columns="sexo", values="cpf",
                               aggfunc="count", fill_value=0))
with col_b:
    st.subheader("Programa social")
    st.bar_chart(f["programa_social"].value_counts())

col_c, col_d = st.columns(2)
with col_c:
    st.subheader("Cidadãos por município")
    st.bar_chart(f["municipio"].value_counts())
with col_d:
    st.subheader("Tipo de residência")
    st.bar_chart(f["tipo_residencia"].value_counts())

st.subheader("Qualidade dos dados de origem")
st.dataframe(pd.DataFrame(qualidade.items(), columns=["Problema", "Registros"]),
             width="stretch", hide_index=True)

st.subheader("Registros (CPF mascarado, sem nome, e-mail ou telefone)")
st.dataframe(f, width="stretch", hide_index=True)

st.info("Escolaridade não existe na base da Prefeitura: vem da Receita Federal. "
        "Por isso este app mostra faixa etária x sexo e não faixa etária x escolaridade.")
