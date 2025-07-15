import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- Carregar dados do arquivo CSV ---
@st.cache_data
def carregar_dados():
    csv_file_path = "dados_semanais.csv" # Certifique-se de que este arquivo existe na mesma pasta

    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{csv_file_path}' não foi encontrado. Por favor, certifique-se de que ele está na mesma pasta do script.")
        st.stop()

    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", dayfirst=True)
    df = df.set_index("Data")
    df = df.sort_index()

    return df

df = carregar_dados()

st.title("📊 Análise de Performance Semanal (WoW)")

# --- Calcular Semana Anterior e WoW (Week-over-Week) ---
# Vamos trabalhar diretamente com o DataFrame semanal 'df'
df_semanal_com_comparativo = df.copy() # Cria uma cópia para não modificar o df original diretamente

metricas_disponiveis = df_semanal_com_comparativo.columns.tolist()
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=0 # Padrão para a primeira métrica disponível
)

df_semanal_com_comparativo['Semana Anterior'] = df_semanal_com_comparativo[metrica_principal].shift(1)
df_semanal_com_comparativo['WoW (%)'] = ((df_semanal_com_comparativo[metrica_principal] - df_semanal_com_comparativo['Semana Anterior']) / df_semanal_com_comparativo['Semana Anterior']) * 100
df_semanal_com_comparativo['WoW (%)'] = df_semanal_com_comparativo['WoW (%)'].replace([np.inf, -np.inf], np.nan).fillna(0) # Tratar infinitos e NaN

# --- Gráfico de Linhas para Comparação Semanal (WoW) ---
st.header(f"Evolução Semanal de {metrica_principal} (Contagem) - WoW")

fig_wow = go.Figure()

# Linha 'Realizado' (Semana Atual)
fig_wow.add_trace(go.Scatter(
    x=df_semanal_com_comparativo.index,
    y=df_semanal_com_comparativo[metrica_principal],
    mode='lines+markers',
    name='Realizado (Semana Atual)',
    line=dict(color='blue', width=2),
    hovertemplate="<b>%{x|%d %b %Y}</b><br>Realizado: %{y:,.0f}<extra></extra>"
))

# Linha 'Semana Anterior'
fig_wow.add_trace(go.Scatter(
    x=df_semanal_com_comparativo.index,
    y=df_semanal_com_comparativo['Semana Anterior'],
    mode='lines+markers',
    name='Semana Anterior',
    line=dict(color='purple', width=2),
    hovertemplate="<b>%{x|%d %b %Y}</b><br>Semana Anterior: %{y:,.0f}<extra></extra>"
))

# Linha 'WoW' (Diferença Percentual)
fig_wow.add_trace(go.Scatter(
    x=df_semanal_com_comparativo.index,
    y=df_semanal_com_comparativo['WoW (%)'],
    mode='lines+markers',
    name='WoW (%)',
    line=dict(color='orange', width=2, dash='dash'),
    yaxis='y2', # Usa um segundo eixo Y
    hovertemplate="<b>%{x|%d %b %Y}</b><br>WoW: %{y:.2f}%<extra></extra>"
))

# Adicionar rótulos de porcentagem na linha WoW
for i, row in df_semanal_com_comparativo.iterrows():
    # Apenas para pontos onde WoW não é 0 ou NaN (primeira semana)
    if pd.notna(row['WoW (%)']) and row['WoW (%)'] != 0:
        fig_wow.add_annotation(
            x=i,
            y=row['WoW (%)'],
            text=f"{row['WoW (%)']:.2f}%",
            showarrow=False,
            xshift=0,
            yshift=10 if row['WoW (%)'] >= 0 else -10,
            font=dict(color='orange', size=10),
            yref='y2'
        )
    # Adicionar rótulos de valor para Realizado e Semana Anterior
    if pd.notna(row[metrica_principal]):
        fig_wow.add_annotation(
            x=i,
            y=row[metrica_principal],
            text=f"{row[metrica_principal]:,.0f}",
            showarrow=False,
            yshift=10,
            font=dict(color='blue', size=10),
            yref='y'
        )
    if pd.notna(row['Semana Anterior']):
        fig_wow.add_annotation(
            x=i,
            y=row['Semana Anterior'],
            text=f"{row['Semana Anterior']:.0f}",
            showarrow=False,
            yshift=-10,
            font=dict(color='purple', size=10),
            yref='y'
        )

fig_wow.update_layout(
    title=f"Evolução Semanal de {metrica_principal} com Comparativo Semana-a-Semana (WoW)",
    xaxis_title="Data",
    yaxis=dict(
        title=f"{metrica_principal} (Contagem)",
        tickformat=",.0f"
    ),
    yaxis2=dict(
        title="WoW (%)",
        overlaying='y',
        side='right',
        tickformat=".2f",
        showgrid=False
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode="x unified",
    height=500
)
st.plotly_chart(fig_wow, use_container_width=True)

st.markdown("---") # Separador visual

# --- SEÇÃO DE VISUALIZAÇÃO DE DADOS BRUTOS (OPCIONAL) ---
st.header("Visualização de Dados Semanais Brutos por Período Selecionado")

min_date_raw = df.index.min().date()
max_date_raw = df.index.max().date()

st.sidebar.subheader("Ver Dados Semanais Detalhados")
data_inicio_vis = st.sidebar.date_input("Data de Início", value=min_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="vis_start")
data_fim_vis = st.sidebar.date_input("Data de Fim", value=max_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="vis_end")

if data_inicio_vis > data_fim_vis:
    st.sidebar.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

df_visualizacao = df.loc[pd.to_datetime(data_inicio_vis):pd.to_datetime(data_fim_vis)].copy()

if df_visualizacao.empty:
    st.warning("Nenhum dado encontrado para o período selecionado para visualização.")
else:
    with st.expander("🔍 Ver Dados Semanais Filtrados"):
        st.dataframe(df_visualizacao.reset_index())
