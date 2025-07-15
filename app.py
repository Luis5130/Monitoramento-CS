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
# Primeiro, criar uma coluna 'Mes_Ano' para agrupar
df['Mes_Ano'] = df.index.to_period('M')

# Agrupar por 'Mes_Ano' e somar as métricas
df_mensal = df.groupby('Mes_Ano')[df.columns[:-1]].sum() # Exclui a coluna 'Mes_Ano' temporária

# Converter o índice de Period para Datetime para Plotly
df_mensal.index = df_mensal.index.to_timestamp()

# --- Calcular Mês Anterior e MoM (Month-over-Month) ---
# Vamos focar na métrica 'Excelente' para o gráfico principal como exemplo
# Você pode generalizar isso para outras métricas ou usar um seletor

metricas_disponiveis = df_mensal.columns.tolist()
# Seletor para escolher a métrica principal para o gráfico de tendência
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=metricas_disponiveis.index('Excelente') if 'Excelente' in metricas_disponiveis else 0
)

df_mensal['Mês Anterior'] = df_mensal[metrica_principal].shift(1)
df_mensal['MoM (%)'] = ((df_mensal[metrica_principal] - df_mensal['Mês Anterior']) / df_mensal['Mês Anterior']) * 100
df_mensal['MoM (%)'] = df_mensal['MoM (%)'].replace([np.inf, -np.inf], np.nan).fillna(0) # Tratar infinitos e NaN

# --- Gráfico de Linhas (Similar ao GMV Captado da Foto 2) ---
st.header(f"Evolução de {metrica_principal} Captado (R$) - MoM")

fig_gmv = go.Figure()

# Linha 'Realizado' (Mês Atual)
fig_gmv.add_trace(go.Scatter(
    x=df_mensal.index,
    y=df_mensal[metrica_principal],
    mode='lines+markers',
    name='Realizado',
    line=dict(color='blue', width=2),
    hovertemplate="<b>%{x|%b %Y}</b><br>Realizado: R$ %{y:,.0f}<extra></extra>"
))

# Linha 'Mês Anterior'
fig_gmv.add_trace(go.Scatter(
    x=df_mensal.index,
    y=df_mensal['Mês Anterior'],
    mode='lines+markers',
    name='Mês Anterior',
    line=dict(color='purple', width=2),
    hovertemplate="<b>%{x|%b %Y}</b><br>Mês Anterior: R$ %{y:,.0f}<extra></extra>"
))

# Linha 'MoM' (Diferença Percentual)
fig_gmv.add_trace(go.Scatter(
    x=df_mensal.index,
    y=df_mensal['MoM (%)'],
    mode='lines+markers',
    name='MoM',
    line=dict(color='orange', width=2, dash='dash'),
    yaxis='y2', # Usa um segundo eixo Y
    hovertemplate="<b>%{x|%b %Y}</b><br>MoM: %{y:.2f}%<extra></extra>"
))

# Adicionar rótulos de porcentagem na linha MoM
for i, row in df_mensal.iterrows():
    if pd.notna(row['MoM (%)']): # Adiciona anotações apenas onde MoM não é NaN
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
            text=f"R$ {row[metrica_principal]/1000:,.0f} Mi" if row[metrica_principal] >= 1000 else f"R$ {row[metrica_principal]:,.0f}",
            showarrow=False,
            yshift=10,
            font=dict(color='blue', size=10),
            yref='y'
        )
    if pd.notna(row['Mês Anterior']):
        fig_gmv.add_annotation(
            x=i,
            y=row['Mês Anterior'],
            text=f"R$ {row['Mês Anterior']/1000:,.0f} Mi" if row['Mês Anterior'] >= 1000 else f"R$ {row['Mês Anterior']:,.0f}",
            showarrow=False,
            yshift=-10, # Abaixo da linha
            font=dict(color='purple', size=10),
            yref='y'
        )


fig_gmv.update_layout(
    title=f"Evolução Mensal de {metrica_principal} com Comparativo MoM",
    xaxis_title="Data",
    yaxis=dict(
        title=f"{metrica_principal} (R$)",
        tickformat=",.0f" # Formata o eixo Y como moeda/número grande
    ),
    yaxis2=dict(
        title="MoM (%)",
        overlaying='y', # Sobrepõe ao primeiro eixo Y
        side='right', # Coloca no lado direito
        tickformat=".2f", # Formato de porcentagem para o segundo eixo Y
        showgrid=False # Não mostra a grade para o segundo eixo
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode="x unified",
    height=500 # Altura do gráfico
)
st.plotly_chart(fig_gmv, use_container_width=True)

st.markdown("---") # Separador visual

# --- SELEÇÃO DE PERÍODOS PARA COMPARATIVO DETALHADO (Mantido do código anterior) ---
st.header("Comparativo Detalhado de Períodos Selecionados")

min_date_raw = df.index.min().date()
max_date_raw = df.index.max().date()

st.sidebar.subheader("Período 1")
data_inicio_p1 = st.sidebar.date_input("Data de Início P1", value=min_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="p1_start_raw")
data_fim_p1 = st.sidebar.date_input("Data de Fim P1", value=max_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="p1_end_raw")

st.sidebar.subheader("Período 2")
data_inicio_p2 = st.sidebar.date_input("Data de Início P2", value=min_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="p2_start_raw")
data_fim_p2 = st.sidebar.date_input("Data de Fim P2", value=max_date_raw, min_value=min_date_raw, max_value=max_date_raw, key="p2_end_raw")

if data_inicio_p1 > data_fim_p1:
    st.sidebar.error("Erro: A data de início do Período 1 não pode ser posterior à data de fim.")
    st.stop()

if data_inicio_p2 > data_fim_p2:
    st.sidebar.error("Erro: A data de início do Período 2 não pode ser posterior à data de fim.")
    st.stop()

df_p1 = df.loc[pd.to_datetime(data_inicio_p1):pd.to_datetime(data_fim_p1)]
df_p2 = df.loc[pd.to_datetime(data_inicio_p2):pd.to_datetime(data_fim_p2)]

if df_p1.empty or df_p2.empty:
    st.warning("Um ou ambos os períodos selecionados não contêm dados. Por favor, ajuste as datas.")
else:
    colunas_numericas = df.columns[:-1] # Exclui a coluna 'Mes_Ano' temporária, se ela existir ainda no df original

    totais_p1 = df_p1[colunas_numericas].sum()
    totais_p2 = df_p2[colunas_numericas].sum()

    diferenca_percentual = pd.Series(index=colunas_numericas, dtype=float)
    
    for col in colunas_numericas:
        val_p1 = totais_p1.get(col, 0)
        val_p2 = totais_p2.get(col, 0)
        
        if val_p1 == 0:
            if val_p2 > 0:
                diferenca_percentual[col] = float('inf')
            else:
                diferenca_percentual[col] = 0
        else:
            diferenca_percentual[col] = ((val_p2 - val_p1) / val_p1) * 100

    df_comparativo = pd.DataFrame({
        "Métrica": colunas_numericas,
        f"Total Período 1 ({data_inicio_p1.strftime('%d/%m/%Y')} a {data_fim_p1.strftime('%d/%m/%Y')})": totais_p1.values,
        f"Total Período 2 ({data_inicio_p2.strftime('%d/%m/%Y')} a {data_fim_p2.strftime('%d/%m/%Y')})": totais_p2.values,
        "Diferença Percentual (%)": diferenca_percentual.values
    })

    st.dataframe(df_comparativo.style.format({
        f"Total Período 1 ({data_inicio_p1.strftime('%d/%m/%Y')} a {data_fim_p1.strftime('%d/%m/%Y')})": "{:,.0f}",
        f"Total Período 2 ({data_inicio_p2.strftime('%d/%m/%Y')} a {data_fim_p2.strftime('%d/%m/%Y')})": "{:,.0f}",
        "Diferença Percentual (%)": "{:,.2f}%"
    }))

    st.subheader("Gráfico de Diferença Percentual entre Período 1 e Período 2")

    fig_bar = go.Figure()

    fig_bar.add_trace(go.Bar(
        x=df_comparativo["Métrica"],
        y=df_comparativo["Diferença Percentual (%)"],
        name="Diferença Percentual",
        marker_color=['green' if x >= 0 else 'red' for x in df_comparativo["Diferença Percentual (%)"]],
        hovertemplate="<br>".join([
            "Métrica: %{x}",
            "Diferença: %{y:.2f}%",
        ])
    ))

    fig_bar.update_layout(
        title="Diferença Percentual por Métrica",
        xaxis_title="Métrica",
        yaxis_title="Diferença Percentual (%)",
        yaxis_tickformat=".0f",
        showlegend=False
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("🔍 Ver dados brutos do Período 1"):
        st.dataframe(df_p1.reset_index())
    with st.expander("🔍 Ver dados brutos do Período 2"):
        st.dataframe(df_p2.reset_index())
