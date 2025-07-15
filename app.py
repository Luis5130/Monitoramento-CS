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

st.title("📊 Análise de Performance: Comparativo Semana do Mês (MoM)")

# --- Preparar dados para comparação de "Semana do Mês" ---
df_comparacao_semana_mes = df.copy()

# Adicionar colunas para Mês, Ano e Semana do Mês
df_comparacao_semana_mes['Ano'] = df_comparacao_semana_mes.index.year
df_comparacao_semana_mes['Mes'] = df_comparacao_semana_mes.index.month
# Calcula a semana do mês como (dia do mês - 1) // 7 + 1
# Ex: Dia 1-7 -> Semana 1, Dia 8-14 -> Semana 2, etc.
df_comparacao_semana_mes['Semana_do_Mes_Num'] = ((df_comparacao_semana_mes.index.day - 1) // 7) + 1

# Criar um identificador único para "Ano-Semana do Mês" para gráficos
df_comparacao_semana_mes['Periodo_Semana_Mes'] = df_comparacao_semana_mes['Ano'].astype(str) + '-S' + df_comparacao_semana_mes['Semana_do_Mes_Num'].astype(str)

# --- Agrupar por Semana do Mês e Mês/Ano para os totais ---
# Isso é para o caso de termos múltiplas entradas para a mesma "semana do mês" num dado mês,
# o que é menos provável com seus dados semanais, mas garante a consistência.
# Usamos a média para cada 'Semana_do_Mes_Num' dentro de cada 'Mes_Ano'
df_grouped = df_comparacao_semana_mes.groupby(['Ano', 'Mes', 'Semana_do_Mes_Num']).agg(
    {col: 'sum' for col in df.columns} # Soma as métricas para a semana específica
).reset_index()

# Ordenar para garantir que o shift funcione corretamente
df_grouped = df_grouped.sort_values(by=['Ano', 'Mes', 'Semana_do_Mes_Num'])

# --- Seleção da Métrica Principal ---
metricas_disponiveis = [col for col in df_grouped.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num']]
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=0 # Padrão para a primeira métrica disponível
)

# --- Calcular a Semana Correspondente do Mês Anterior ---
# Criar uma cópia para não interferir com o df_grouped original
df_plot = df_grouped.copy()

df_plot['Mes_Anterior_Valor'] = np.nan
df_plot['MoM_Semana_Pct'] = np.nan

for idx, row in df_plot.iterrows():
    # Encontrar o valor da mesma Semana_do_Mes_Num no mês anterior
    mes_anterior = row['Mes'] - 1
    ano_anterior_mo = row['Ano']
    if mes_anterior == 0: # Se for janeiro (mês 1), o mês anterior é dezembro do ano anterior
        mes_anterior = 12
        ano_anterior_mo = row['Ano'] - 1

    valor_mes_anterior = df_plot[
        (df_plot['Ano'] == ano_anterior_mo) &
        (df_plot['Mes'] == mes_anterior) &
        (df_plot['Semana_do_Mes_Num'] == row['Semana_do_Mes_Num'])
    ][metrica_principal]

    if not valor_mes_anterior.empty:
        df_plot.loc[idx, 'Mes_Anterior_Valor'] = valor_mes_anterior.iloc[0]

# Calcular a porcentagem de diferença
# Garantir que não haja divisão por zero
df_plot['MoM_Semana_Pct'] = ((df_plot[metrica_principal] - df_plot['Mes_Anterior_Valor']) / df_plot['Mes_Anterior_Valor']) * 100
df_plot['MoM_Semana_Pct'] = df_plot['MoM_Semana_Pct'].replace([np.inf, -np.inf], np.nan).fillna(0)


# --- Criar rótulos para o eixo X do gráfico ---
# Ex: 'Maio S1', 'Maio S2', 'Junho S1'
df_plot['Label_Eixo_X'] = df_plot['Mes'].apply(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b')) + ' S' + df_plot['Semana_do_Mes_Num'].astype(str)

# --- Gráfico de Linhas para Comparação Semanal do Mês (MoM) ---
st.header(f"Evolução de {metrica_principal} (Contagem) - Comparativo Semana do Mês (MoM)")

fig_semana_mes = go.Figure()

# Linha 'Realizado' (Semana Atual do Mês)
fig_semana_mes.add_trace(go.Scatter(
    x=df_plot['Label_Eixo_X'],
    y=df_plot[metrica_principal],
    mode='lines+markers',
    name='Realizado (Semana Atual do Mês)',
    line=dict(color='blue', width=2),
    hovertemplate="<b>%{x}</b><br>Realizado: %{y:,.0f}<extra></extra>"
))

# Linha 'Semana Correspondente do Mês Anterior'
fig_semana_mes.add_trace(go.Scatter(
    x=df_plot['Label_Eixo_X'],
    y=df_plot['Mes_Anterior_Valor'],
    mode='lines+markers',
    name='Semana Correspondente do Mês Anterior',
    line=dict(color='purple', width=2),
    hovertemplate="<b>%{x}</b><br>Mês Anterior: %{y:,.0f}<extra></extra>"
))

# Linha 'MoM_Semana_Pct' (Diferença Percentual)
fig_semana_mes.add_trace(go.Scatter(
    x=df_plot['Label_Eixo_X'],
    y=df_plot['MoM_Semana_Pct'],
    mode='lines+markers',
    name='MoM (%) (Semana do Mês)',
    line=dict(color='orange', width=2, dash='dash'),
    yaxis='y2', # Usa um segundo eixo Y
    hovertemplate="<b>%{x}</b><br>MoM: %{y:.2f}%<extra></extra>"
))

# Adicionar rótulos de porcentagem e valores
for i, row in df_plot.iterrows():
    # Apenas para pontos onde MoM não é 0 ou NaN
    if pd.notna(row['MoM_Semana_Pct']) and row['MoM_Semana_Pct'] != 0:
        fig_semana_mes.add_annotation(
            x=row['Label_Eixo_X'],
            y=row['MoM_Semana_Pct'],
            text=f"{row['MoM_Semana_Pct']:.2f}%",
            showarrow=False,
            xshift=0,
            yshift=10 if row['MoM_Semana_Pct'] >= 0 else -10,
            font=dict(color='orange', size=10),
            yref='y2'
        )
    # Adicionar rótulos de valor para Realizado e Mês Anterior
    if pd.notna(row[metrica_principal]):
        fig_semana_mes.add_annotation(
            x=row['Label_Eixo_X'],
            y=row[metrica_principal],
            text=f"{row[metrica_principal]:,.0f}",
            showarrow=False,
            yshift=10,
            font=dict(color='blue', size=10),
            yref='y'
        )
    if pd.notna(row['Mes_Anterior_Valor']):
        fig_semana_mes.add_annotation(
            x=row['Label_Eixo_X'],
            y=row['Mes_Anterior_Valor'],
            text=f"{row['Mes_Anterior_Valor']:.0f}",
            showarrow=False,
            yshift=-10,
            font=dict(color='purple', size=10),
            yref='y'
        )

fig_semana_mes.update_layout(
    title=f"Evolução de {metrica_principal} com Comparativo Semana do Mês (MoM)",
    xaxis_title="Período (Mês e Semana)",
    yaxis=dict(
        title=f"{metrica_principal} (Contagem)",
        tickformat=",.0f"
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
st.plotly_chart(fig_semana_mes, use_container_width=True)

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
