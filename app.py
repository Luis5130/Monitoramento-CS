import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import calendar

@st.cache_data
def carregar_dados():
    df = pd.read_csv("dados_semanais.csv")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", dayfirst=True)
    df = df.set_index("Data").sort_index()
    return df

def semana_do_mes(dt):
    cal = calendar.monthcalendar(dt.year, dt.month)
    for i, semana in enumerate(cal, 1):
        if dt.day in semana:
            return i
    return 0

df_original = carregar_dados()

st.title("📊 Análise de Performance: Comparativo Semana do Mês (Histórico)")

min_date = df_original.index.min().date()
max_date = df_original.index.max().date()

data_inicio = st.sidebar.date_input("Data de Início do Gráfico", min_value=min_date, max_value=max_date, value=min_date)
data_fim = st.sidebar.date_input("Data de Fim do Gráfico", min_value=min_date, max_value=max_date, value=max_date)

if data_inicio > data_fim:
    st.sidebar.error("Data de início > data de fim.")
    st.stop()

df_filtrado = df_original.loc[data_inicio:data_fim].copy()
if df_filtrado.empty:
    st.warning("Nenhum dado no período selecionado.")
    st.stop()

df = df_filtrado.copy()
df['Ano'] = df.index.year
df['Mes'] = df.index.month
df['Semana_do_Mes_Num'] = df.index.to_series().apply(semana_do_mes)
df['Label_Mes'] = df.index.strftime('%b')
df['Mes_Ano'] = df['Label_Mes'] + ' ' + df['Ano'].astype(str)

df_grouped = df.groupby(
    ['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano']) \
    .agg({col: 'sum' for col in df_original.columns}).reset_index() \
    .sort_values(['Ano','Mes','Semana_do_Mes_Num'])

metricas = [c for c in df_grouped.columns if c not in ['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano']]
selecionadas = st.sidebar.multiselect("Status CS – DogHero", metricas, default=[metricas[0]] if metricas else [])

# (resto do seu código permanece igual, com gráfico e tabela)
