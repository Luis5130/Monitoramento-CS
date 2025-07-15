import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots # Para múltiplos gráficos em uma figura

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

st.title("📊 Análise de Performance ao Longo do Tempo e Comparativo de Períodos")

# --- VISUALIZAÇÃO DE TENDÊNCIA AO LONGO DO TEMPO (SIMILAR À FOTO 1) ---
st.header("Tendência das Métricas ao Longo do Tempo")

# Obter todas as colunas numéricas (métricas)
metricas_para_grafico_linha = df.columns.tolist()

if not metricas_para_grafico_linha:
    st.warning("Nenhuma métrica numérica encontrada para exibir no gráfico de tendência.")
else:
    fig_linha = go.Figure()

    for col in metricas_para_grafico_linha:
        fig_linha.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines+markers', name=col))

    fig_linha.update_layout(
        title="Evolução das Métricas Semanais",
        xaxis_title="Data",
        yaxis_title="Contagem",
        hovermode="x unified" # Exibe hover para todas as linhas na mesma data
    )
    st.plotly_chart(fig_linha, use_container_width=True)


# --- SELEÇÃO DE PERÍODOS PARA COMPARATIVO ---
st.sidebar.header("Seleção de Períodos para Comparativo")

min_date = df.index.min().date()
max_date = df.index.max().date()

st.sidebar.subheader("Período 1")
data_inicio_p1 = st.sidebar.date_input("Data de Início P1", value=min_date, min_value=min_date, max_value=max_date, key="p1_start")
data_fim_p1 = st.sidebar.date_input("Data de Fim P1", value=max_date, min_value=min_date, max_value=max_date, key="p1_end")

st.sidebar.subheader("Período 2")
data_inicio_p2 = st.sidebar.date_input("Data de Início P2", value=min_date, min_value=min_date, max_value=max_date, key="p2_start")
data_fim_p2 = st.sidebar.date_input("Data de Fim P2", value=max_date, min_value=min_date, max_value=max_date, key="p2_end")


# --- Garantir que as datas de fim sejam maiores ou iguais às datas de início ---
if data_inicio_p1 > data_fim_p1:
    st.sidebar.error("Erro: A data de início do Período 1 não pode ser posterior à data de fim.")
    st.stop()

if data_inicio_p2 > data_fim_p2:
    st.sidebar.error("Erro: A data de início do Período 2 não pode ser posterior à data de fim.")
    st.stop()


# --- Filtrar dados por período ---
df_p1 = df.loc[pd.to_datetime(data_inicio_p1):pd.to_datetime(data_fim_p1)]
df_p2 = df.loc[pd.to_datetime(data_inicio_p2):pd.to_datetime(data_fim_p2)]

if df_p1.empty or df_p2.empty:
    st.warning("Um ou ambos os períodos selecionados não contêm dados. Por favor, ajuste as datas.")
else:
    # --- Calcular totais para cada período ---
    colunas_numericas = df.columns # As métricas são todas as colunas exceto o índice 'Data'
    
    totais_p1 = df_p1[colunas_numericas].sum()
    totais_p2 = df_p2[colunas_numericas].sum()

    # --- Calcular a diferença percentual ---
    diferenca_percentual = pd.Series(index=colunas_numericas, dtype=float)
    
    for col in colunas_numericas:
        val_p1 = totais_p1.get(col, 0)
        val_p2 = totais_p2.get(col, 0)
        
        if val_p1 == 0:
            if val_p2 > 0:
                diferenca_percentual[col] = float('inf') # Aumento infinito
            else:
                diferenca_percentual[col] = 0 # Ambos zero, diferença zero
        else:
            diferenca_percentual[col] = ((val_p2 - val_p1) / val_p1) * 100

    # --- Criar DataFrame para exibição ---
    st.header("Comparativo de Períodos Selecionados")
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


    # --- Gráfico de Barras da Diferença Percentual (Similar à Foto 2) ---
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
