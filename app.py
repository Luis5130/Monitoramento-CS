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

df_original = carregar_dados()

st.title("📊 Análise de Performance: Comparativo Semana do Mês (MoM)")

# --- Filtros de Período na barra lateral para o gráfico principal ---
st.sidebar.header("Filtros para o Gráfico Principal")

min_date_available = df_original.index.min().date()
max_date_available = df_original.index.max().date()

data_inicio_grafico = st.sidebar.date_input(
    "Data de Início do Gráfico",
    value=min_date_available,
    min_value=min_date_available,
    max_value=max_date_available,
    key="graph_start_date"
)
data_fim_grafico = st.sidebar.date_input(
    "Data de Fim do Gráfico",
    value=max_date_available,
    min_value=min_date_available,
    max_value=max_date_available, # CORRIGIDO: Adicionado max_value= aqui
    key="graph_end_date"
)

# Validação dos filtros de data
if data_inicio_grafico > data_fim_grafico:
    st.sidebar.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

# --- Aplicar o filtro de data antes de qualquer processamento ---
df_filtrado = df_original.loc[pd.to_datetime(data_inicio_grafico):pd.to_datetime(data_fim_grafico)].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o período selecionado no gráfico principal. Por favor, ajuste as datas.")
    st.stop()


# --- Preparar dados para comparação de "Semana do Mês" ---
df_comparacao_semana_mes = df_filtrado.copy()

# Adicionar colunas para Mês, Ano e Semana do Mês
df_comparacao_semana_mes['Ano'] = df_comparacao_semana_mes.index.year
df_comparacao_semana_mes['Mes'] = df_comparacao_semana_mes.index.month
df_comparacao_semana_mes['Semana_do_Mes_Num'] = ((df_comparacao_semana_mes.index.day - 1) // 7) + 1

# --- Agrupar por Semana do Mês e Mês/Ano para os totais ---
df_grouped = df_comparacao_semana_mes.groupby(['Ano', 'Mes', 'Semana_do_Mes_Num']).agg(
    {col: 'sum' for col in df_original.columns}
).reset_index()

# Ordenar para garantir que o cálculo do mês anterior funcione corretamente
df_grouped = df_grouped.sort_values(by=['Ano', 'Mes', 'Semana_do_Mes_Num'])

# --- Seleção da Métrica Principal ---
metricas_disponiveis = [col for col in df_grouped.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num']]
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=0
)

# --- Calcular a Semana Correspondente do Mês Anterior ---
df_plot = df_grouped.copy()

df_plot['Mes_Anterior_Valor'] = np.nan
df_plot['MoM_Semana_Pct'] = np.nan

for idx, row in df_plot.iterrows():
    mes_anterior = row['Mes'] - 1
    ano_anterior_mo = row['Ano']
    if mes_anterior == 0:
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
df_plot['MoM_Semana_Pct'] = ((df_plot[metrica_principal] - df_plot['Mes_Anterior_Valor']) / df_plot['Mes_Anterior_Valor']) * 100
df_plot['MoM_Semana_Pct'] = df_plot['MoM_Semana_Pct'].replace([np.inf, -np.inf], np.nan).fillna(0)

# Remover linhas onde não há comparação (primeiros meses/semanas)
df_plot_final = df_plot[
    (df_plot[metrica_principal].notna()) |
    (df_plot['Mes_Anterior_Valor'].notna()) |
    (df_plot['MoM_Semana_Pct'].notna())
].copy()


# --- Criar rótulos para o eixo X do gráfico ---
df_plot_final['Label_Eixo_X'] = df_plot_final['Mes'].apply(lambda x: pd.to_datetime(str(x), format='%m').strftime('%b')) + ' S' + df_plot_final['Semana_do_Mes_Num'].astype(str)

# --- Gráfico de Linhas para Comparação Semanal do Mês (MoM) ---
st.header(f"Evolução de {metrica_principal} (Contagem) - Comparativo Semana do Mês (MoM)")

if df_plot_final.empty:
    st.warning("Não há dados suficientes para exibir o gráfico com os filtros e comparações selecionados.")
else:
    fig_semana_mes = go.Figure()

    # Linha 'Realizado' (Semana Atual do Mês)
    fig_semana_mes.add_trace(go.Scatter(
        x=df_plot_final['Label_Eixo_X'],
        y=df_plot_final[metrica_principal],
        mode='lines+markers',
        name='Realizado (Semana Atual do Mês)',
        line=dict(color='blue', width=2),
        hovertemplate="<b>%{x}</b><br>Realizado: %{y:,.0f}<extra></extra>"
    ))

    # Linha 'Semana Correspondente do Mês Anterior'
    fig_semana_mes.add_trace(go.Scatter(
        x=df_plot_final['Label_Eixo_X'],
        y=df_plot_final['Mes_Anterior_Valor'],
        mode='lines+markers',
        name='Semana Correspondente do Mês Anterior',
        line=dict(color='purple', width=2),
        hovertemplate="<b>%{x}</b><br>Mês Anterior: %{y:,.0f}<extra></extra>"
    ))

    # Linha 'MoM_Semana_Pct' (Diferença Percentual)
    fig_semana_mes.add_trace(go.Scatter(
        x=df_plot_final['Label_Eixo_X'],
        y=df_plot_final['MoM_Semana_Pct'],
        mode='lines+markers',
        name='MoM (%) (Semana do Mês)',
        line=dict(color='orange', width=2, dash='dash'),
        yaxis='y2',
        hovertemplate="<b>%{x}</b><br>MoM: %{y:.2f}%<extra></extra>"
    ))

    # Adicionar rótulos de porcentagem e valores
    for i, row in df_plot_final.iterrows():
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

st.markdown("---")

# --- SEÇÃO DE VISUALIZAÇÃO DE DADOS BRUTOS (OPCIONAL) ---
st.header("Visualização de Dados Semanais Brutos por Período Selecionado")

min_date_raw_vis = df_original.index.min().date()
max_date_raw_vis = df_original.index.max().date()

st.sidebar.subheader("Ver Dados Semanais Detalhados")
data_inicio_vis = st.sidebar.date_input("Data de Início", value=min_date_raw_vis, min_value=min_date_raw_vis, max_value=max_date_raw_vis, key="vis_start")
data_fim_vis = st.sidebar.date_input("Data de Fim", value=max_date_raw_vis, min_value=min_date_raw_vis, max_value=max_date_raw_vis, key="vis_end") # CORRIGIDO AQUI TAMBÉM

if data_inicio_vis > data_fim_vis:
    st.sidebar.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

df_visualizacao = df_original.loc[pd.to_datetime(data_inicio_vis):pd.to_datetime(data_fim_vis)].copy()

if df_visualizacao.empty:
    st.warning("Nenhum dado encontrado para o período selecionado para visualização.")
else:
    with st.expander("🔍 Ver Dados Semanais Filtrados"):
        st.dataframe(df_visualizacao.reset_index())
