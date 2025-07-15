import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- Carregar dados do arquivo CSV ---
@st.cache_data
def carregar_dados():
    # Caminho para o seu arquivo CSV
    csv_file_path = "dados_semanais.csv" # Certifique-se de que este arquivo existe na mesma pasta

    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{csv_file_path}' não foi encontrado. Por favor, certifique-se de que ele está na mesma pasta do script.")
        st.stop() # Para a execução do script se o arquivo não for encontrado

    # Converter a coluna 'Data' para o tipo datetime
    # Use 'dayfirst=True' se o formato for DD/MM/YYYY
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", dayfirst=True)

    # Definir a coluna 'Data' como índice para facilitar a seleção de períodos
    df = df.set_index("Data")
    
    # Ordenar o DataFrame pelo índice (data) para garantir que os períodos sejam selecionados corretamente
    df = df.sort_index()

    return df

df = carregar_dados()

st.title("📊 Comparativo de Períodos")

# --- Filtros de Período ---
st.sidebar.header("Seleção de Períodos")

# Obter as datas mínima e máxima do DataFrame carregado
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
# Convertendo as datas de input para datetime para correspondência com o índice do DataFrame
df_p1 = df.loc[pd.to_datetime(data_inicio_p1):pd.to_datetime(data_fim_p1)]
df_p2 = df.loc[pd.to_datetime(data_inicio_p2):pd.to_datetime(data_fim_p2)]

if df_p1.empty or df_p2.empty:
    st.warning("Um ou ambos os períodos selecionados não contêm dados. Por favor, ajuste as datas.")
else:
    # --- Calcular totais para cada período ---
    # As colunas numéricas são todas exceto o índice 'Data'
    colunas_numericas = df.columns
    
    totais_p1 = df_p1[colunas_numericas].sum()
    totais_p2 = df_p2[colunas_numericas].sum()

    # --- Calcular a diferença percentual ---
    diferenca_percentual = pd.Series(index=colunas_numericas, dtype=float)
    
    for col in colunas_numericas:
        val_p1 = totais_p1.get(col, 0) # Use .get para lidar com colunas que talvez não existam em um período específico (improvável neste caso)
        val_p2 = totais_p2.get(col, 0)
        
        if val_p1 == 0:
            if val_p2 > 0:
                diferenca_percentual[col] = float('inf') # Aumento infinito se P1 for 0 e P2 for > 0
            else:
                diferenca_percentual[col] = 0 # Se ambos são 0, a diferença é 0%
        else:
            diferenca_percentual[col] = ((val_p2 - val_p1) / val_p1) * 100

    # --- Criar DataFrame para exibição ---
    df_comparativo = pd.DataFrame({
        "Métrica": colunas_numericas,
        f"Total Período 1 ({data_inicio_p1.strftime('%d/%m/%Y')} a {data_fim_p1.strftime('%d/%m/%Y')})": totais_p1.values,
        f"Total Período 2 ({data_inicio_p2.strftime('%d/%m/%Y')} a {data_fim_p2.strftime('%d/%m/%Y')})": totais_p2.values,
        "Diferença Percentual (%)": diferenca_percentual.values
    })

    st.subheader("Comparativo de Totais entre Períodos")
    st.dataframe(df_comparativo.style.format({
        f"Total Período 1 ({data_inicio_p1.strftime('%d/%m/%Y')} a {data_fim_p1.strftime('%d/%m/%Y')})": "{:,.0f}",
        f"Total Período 2 ({data_inicio_p2.strftime('%d/%m/%Y')} a {data_fim_p2.strftime('%d/%m/%Y')})": "{:,.0f}",
        "Diferença Percentual (%)": "{:,.2f}%"
    }))


    # --- Visualização Gráfica ---
    st.subheader("Gráfico de Comparação Percentual")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_comparativo["Métrica"],
        y=df_comparativo["Diferença Percentual (%)"],
        name="Diferença Percentual",
        marker_color=['green' if x >= 0 else 'red' for x in df_comparativo["Diferença Percentual (%)"]],
        hovertemplate="<br>".join([
            "Métrica: %{x}",
            "Diferença: %{y:.2f}%",
        ])
    ))

    fig.update_layout(
        title="Diferença Percentual entre Período 1 e Período 2",
        xaxis_title="Métrica",
        yaxis_title="Diferença Percentual (%)",
        yaxis_tickformat=".0f",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 Ver dados do Período 1"):
        st.dataframe(df_p1.reset_index())
    with st.expander("🔍 Ver dados do Período 2"):
        st.dataframe(df_p2.reset_index())
