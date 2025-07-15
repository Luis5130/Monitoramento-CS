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

st.title("📊 Análise de Performance e Comparativo Mensal (MoM)")

# --- Agrupar por mês e calcular o total ---
df['Mes_Ano'] = df.index.to_period('M')
df_mensal = df.groupby('Mes_Ano')[df.columns[:-1]].sum()
df_mensal.index = df_mensal.index.to_timestamp()

# --- Calcular Mês Anterior e MoM (Month-over-Month) ---
metricas_disponiveis = df_mensal.columns.tolist()
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=0 # Padrão para a primeira métrica disponível
)

df_mensal['Mês Anterior'] = df_mensal[metrica_principal].shift(1)
df_mensal['MoM (%)'] = ((df_mensal[metrica_principal] - df_mensal['Mês Anterior']) / df_mensal['Mês Anterior']) * 100
df_mensal['MoM (%)'] = df_mensal['MoM (%)'].replace([np.inf, -np.inf], np.nan).fillna(0) # Tratar infinitos e NaN

# --- Gráfico de Linhas (Similar ao GMV Captado da Foto 2) ---
st.header(f"Evolução de {metrica_principal} (Contagem) - MoM")

fig_gmv = go.Figure()

# Linha 'Realizado' (Mês Atual)
fig_gmv.add_trace(go.Scatter(
    x=df_mensal.index,
    y=df_mensal[metrica_principal],
    mode='lines+markers',
    name='Realizado (Mês Atual)', # Renomeado para clareza
    line=dict(color='blue', width=2),
    hovertemplate="<b>%{x|%b %Y}</b><br>Realizado: %{y:,.0f}<extra></extra>"
))

# Linha 'Mês Anterior'
fig_gmv.add_trace(go.Scatter(
    x=df_mensal.index,
    y=df_mensal['Mês Anterior'],
    mode='lines+markers',
    name='Mês Anterior',
    line=dict(color='purple', width=2),
    hovertemplate="<b>%{x|%b %Y}</b><br>Mês Anterior: %{y:,.0f}<extra></extra>"
))

# Linha 'MoM' (Diferença Percentual)
fig_gmv.add_trace(go.Scatter(
    x=df_mensal.index,
    y=df_mensal['MoM (%)'],
    mode='lines+markers',
    name='MoM (%)',
    line=dict(color='orange', width=2, dash='dash'),
    yaxis='y2', # Usa um segundo eixo Y
    hovertemplate="<b>%{x|%b %Y}</b><br>MoM: %{y:.2f}%<extra></extra>"
))

# Adicionar rótulos de porcentagem na linha MoM
for i, row in df_mensal.iterrows():
    if pd.notna(row['MoM (%)']) and row['MoM (%)'] != 0: # Adiciona anotações apenas onde MoM não é NaN e não é 0
        fig_gmv.add_annotation(
            x=i,
            y=row['MoM (%)'],
            text=f"{row['MoM (%)']:.2f}%",
            showarrow=False,
            xshift=0,
            yshift=10 if row['MoM (%)'] >= 0 else -10, # Ajusta a posição do texto
            font=dict(color='orange', size=10),
            yref='y2' # Assegura que a anotação se refere ao y2
        )
    # Adicionar rótulos de valor para Realizado e Mês Anterior
    if pd.notna(row[metrica_principal]):
        fig_gmv.add_annotation(
            x=i,
            y=row[metrica_principal],
            text=f"{row[metrica_principal]:,.0f}", # Sem R$
            showarrow=False,
            yshift=10,
            font=dict(color='blue', size=10),
            yref='y'
        )
    if pd.notna(row['Mês Anterior']):
        fig_gmv.add_annotation(
            x=i,
            y=row['Mês Anterior'],
            text=f"{row['Mês Anterior']:.0f}", # Sem R$
            showarrow=False,
            yshift=-10, # Abaixo da linha
            font=dict(color='purple', size=10),
            yref='y'
        )


fig_gmv.update_layout(
    title=f"Evolução Mensal de {metrica_principal} com Comparativo Mês-a-Mês",
    xaxis_title="Data",
    yaxis=dict(
        title=f"{metrica_principal} (Contagem)", # Título do eixo Y sem R$
        tickformat=",.0f" # Formata o eixo Y como número inteiro
    ),
    yaxis2=dict(
        title="MoM (%)",
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
st.plotly_chart(fig_gmv, use_container_width=True)

st.markdown("---") # Separador visual

# --- SELEÇÃO DE PERÍODOS PARA EXIBIR DADOS BRUTOS (SE NECESSÁRIO) ---
st.header("Visualização de Dados Brutos por Período Selecionado")

min_date_raw = df.index.min().date()
max_date_raw = df.index.max().date()

st.sidebar.subheader("Ver Dados Semanais por Período")
data_inicio_vis = st.sidebar.date_input("Data de Início", value=min_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="vis_start")
data_fim_vis = st.sidebar.date_input("Data de Fim", value=max_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="vis_end")

if data_inicio_vis > data_fim_vis:
    st.sidebar.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

df_visualizacao = df.loc[pd.to_datetime(data_inicio_vis):pd.to_datetime(data_fim_vis)].copy()
df_visualizacao.drop(columns=['Mes_Ano'], errors='ignore', inplace=True) # Remove a coluna Mes_Ano se existir

if df_visualizacao.empty:
    st.warning("Nenhum dado encontrado para o período selecionado para visualização.")
else:
    with st.expander("🔍 Ver Dados Semanais Filtrados"):
        st.dataframe(df_visualizacao.reset_index())
