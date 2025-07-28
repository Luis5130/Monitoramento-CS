import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- Carregar dados do arquivo CSV ---
@st.cache_data
def carregar_dados():
    csv_file_path = "dados_semanais.csv"

    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{csv_file_path}' não foi encontrado.")
        st.stop()

    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", dayfirst=True)
    df = df.set_index("Data")
    df = df.sort_index()

    return df

df_original = carregar_dados()

st.title("📊 Análise de Performance: Comparativo Semana do Mês (Histórico)")

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
    max_value=max_date_available,
    key="graph_end_date"
)

if data_inicio_grafico > data_fim_grafico:
    st.sidebar.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

# --- Aplicar filtro de data ---
df_filtrado = df_original.loc[pd.to_datetime(data_inicio_grafico):pd.to_datetime(data_fim_grafico)].copy()
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o período selecionado.")
    st.stop()

# --- Preparar dados para comparação de "Semana do Mês" ---
df_comparacao_semana_mes = df_filtrado.copy()

df_comparacao_semana_mes['Ano'] = df_comparacao_semana_mes.index.year
df_comparacao_semana_mes['Mes'] = df_comparacao_semana_mes.index.month

# ✅ NOVO CÁLCULO: Semana do mês real
def semana_do_mes(data):
    primeiro_dia_mes = data.replace(day=1)
    ajuste_dia_semana = primeiro_dia_mes.weekday()  # Segunda = 0
    return ((data.day + ajuste_dia_semana - 1) // 7) + 1

df_comparacao_semana_mes['Semana_do_Mes_Num'] = df_comparacao_semana_mes.index.to_series().apply(semana_do_mes)
df_comparacao_semana_mes['Label_Mes'] = df_comparacao_semana_mes.index.strftime('%b')
df_comparacao_semana_mes['Mes_Ano'] = df_comparacao_semana_mes['Label_Mes'] + ' ' + df_comparacao_semana_mes['Ano'].astype(str)

# Agrupar por Ano, Mês, Semana do Mês
df_grouped_by_week_in_month = df_comparacao_semana_mes.groupby(
    ['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano']
).agg({col: 'sum' for col in df_original.columns if col not in ['Data']}).reset_index()

df_grouped_by_week_in_month = df_grouped_by_week_in_month.sort_values(by=['Ano', 'Mes', 'Semana_do_Mes_Num'])

# --- Seleção das Métricas ---
metricas_disponiveis = [col for col in df_grouped_by_week_in_month.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano']]
metricas_selecionadas = st.sidebar.multiselect("Status CS - DogHero", metricas_disponiveis, default=[metricas_disponiveis[0]])

# --- Construção do gráfico ---
st.header(f"Evolução das Métricas por Semana do Mês")
df_chart_data = df_grouped_by_week_in_month.copy()
df_chart_data['Full_Label_X_Hover'] = df_chart_data['Mes_Ano'] + ' S' + df_chart_data['Semana_do_Mes_Num'].astype(str)

if df_chart_data.empty or not metricas_selecionadas:
    st.warning("Nenhum dado ou métrica selecionada.")
else:
    fig_main = go.Figure()
    meses_para_plotar = sorted(df_chart_data['Mes_Ano'].unique(),
                               key=lambda x: (int(x.split(' ')[1]), pd.to_datetime(x.split(' ')[0], format='%b').month))

    cores = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'grey', 'cyan', 'magenta']
    cor_index = 0
    all_annotations = []

    for metrica in metricas_selecionadas:
        for mes_ano in meses_para_plotar:
            df_mes_metrica = df_chart_data[df_chart_data['Mes_Ano'] == mes_ano]
            if not df_mes_metrica.empty and metrica in df_mes_metrica.columns:
                current_color = cores[cor_index % len(cores)]
                cor_index += 1

                fig_main.add_trace(go.Scatter(
                    x=df_mes_metrica['Semana_do_Mes_Num'],
                    y=df_mes_metrica[metrica],
                    mode='lines+markers',
                    name=f'{mes_ano} ({metrica})',
                    line=dict(color=current_color, width=2),
                    hovertemplate="<b>%{customdata}" + f" ({metrica})" + "</b><br>Valor: %{y:,.0f}<extra></extra>",
                    customdata=df_mes_metrica['Full_Label_X_Hover']
                ))

                for _, row in df_mes_metrica.iterrows():
                    valor = row.get(metrica)
                    if pd.notna(valor):
                        all_annotations.append(dict(
                            x=row['Semana_do_Mes_Num'],
                            y=valor,
                            text=f"{valor:,.0f}",
                            showarrow=False,
                            yshift=10,
                            font=dict(color=current_color, size=10)
                        ))

    fig_main.update_layout(
        title="Evolução das Métricas por Semana do Mês",
        xaxis=dict(
            title="Semana do Mês",
            tickmode='array',
            tickvals=list(range(1, df_chart_data['Semana_do_Mes_Num'].max() + 1)),
            ticktext=[f'Semana {s}' for s in range(1, df_chart_data['Semana_do_Mes_Num'].max() + 1)],
            showgrid=True,
            gridcolor='lightgrey'
        ),
        yaxis=dict(title="Contagem", tickformat=",.0f", showgrid=True, gridcolor='lightgrey'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        height=550,
        annotations=all_annotations
    )
    st.plotly_chart(fig_main, use_container_width=True)
