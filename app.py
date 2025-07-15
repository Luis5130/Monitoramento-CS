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

# Validação dos filtros de data
if data_inicio_grafico > data_fim_grafico:
    st.sidebar.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

# --- Aplicar o filtro de data antes de qualquer processamento ---
df_filtrado = df_original.loc[(pd.to_datetime(data_inicio_grafico)):(pd.to_datetime(data_fim_grafico))].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o período selecionado no gráfico principal. Por favor, ajuste as datas.")
    st.stop()


# --- Preparar dados para comparação de "Semana do Mês" ---
df_comparacao_semana_mes = df_filtrado.copy()

df_comparacao_semana_mes['Ano'] = df_comparacao_semana_mes.index.year
df_comparacao_semana_mes['Mes'] = df_comparacao_semana_mes.index.month
df_comparacao_semana_mes['Semana_do_Mes_Num'] = ((df_comparacao_semana_mes.index.day - 1) // 7) + 1
df_comparacao_semana_mes['Label_Mes'] = df_comparacao_semana_mes.index.strftime('%b')

# Adicionar a coluna de Mês/Ano para agrupar e calcular MoM
df_comparacao_semana_mes['Mes_Ano'] = df_comparacao_semana_mes['Label_Mes'] + ' ' + df_comparacao_semana_mes['Ano'].astype(str)


# Agrupar por Ano, Mês, Semana do Mês para obter os totais
df_grouped_by_week_in_month = df_comparacao_semana_mes.groupby(['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano']).agg(
    {col: 'sum' for col in df_original.columns if col not in ['Data']}
).reset_index()

# Ordenar para garantir a consistência
df_grouped_by_week_in_month = df_grouped_by_week_in_month.sort_values(by=['Ano', 'Mes', 'Semana_do_Mes_Num'])

# --- Seleção da(s) Métrica(s) Principal(is) ---
metricas_disponiveis = [col for col in df_grouped_by_week_in_month.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano']]
metricas_selecionadas = st.sidebar.multiselect(
    "Status CS - DogHero",
    metricas_disponiveis,
    default=[metricas_disponiveis[-1]] if metricas_disponiveis else [] # Exibe a última métrica por padrão se houver alguma
)


# --- Criar o DataFrame para o Gráfico Principal ---
df_chart_data = df_grouped_by_week_in_month.copy()

# Criar um rótulo completo para o hover (Mês e Ano S Semana X)
df_chart_data['Full_Label_X_Hover'] = df_chart_data['Mes_Ano'] + ' S' + df_chart_data['Semana_do_Mes_Num'].astype(str)


# --- Gráfico de Linhas (com uma linha para cada mês e métrica) ---
st.header(f"Evolução das Métricas por Semana do Mês")

if df_chart_data.empty or not metricas_selecionadas:
    st.warning("Nenhum dado ou métrica selecionada para exibir o gráfico.")
else:
    fig_main = go.Figure()

    # Obter os meses únicos no período filtrado
    meses_para_plotar = sorted(df_chart_data['Mes_Ano'].unique(),
                                key=lambda x: (int(x.split(' ')[1]), pd.to_datetime(x.split(' ')[0], format='%b').month))

    # Definir algumas cores para as linhas
    cores = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'grey', 'cyan', 'magenta']
    cor_index = 0

    # Lista para armazenar todas as anotações (valores nos pontos)
    all_annotations = []

    # Iterar por cada métrica selecionada
    for metrica in metricas_selecionadas:
        # Iterar por cada mês para criar uma linha separada para cada métrica
        for mes_ano in meses_para_plotar:
            df_mes_metrica = df_chart_data[(df_chart_data['Mes_Ano'] == mes_ano)].copy()

            if not df_mes_metrica.empty and metrica in df_mes_metrica.columns:
                current_color = cores[(cor_index) % len(cores)]
                cor_index += 1

                fig_main.add_trace(go.Scatter(
                    x=df_mes_metrica['Semana_do_Mes_Num'], # Eixo X é a Semana do Mês
                    y=df_mes_metrica.get(metrica), # Usar .get() para evitar KeyError
                    mode='lines+markers',
                    name=f'{mes_ano} ({metrica})',
                    line=dict(color=current_color, width=2),
                    hovertemplate="<b>%{customdata}" + f" ({metrica})" + "</b><br>Valor: %{y:,.0f}<extra></extra>",
                    customdata=df_mes_metrica['Full_Label_X_Hover']
                ))

                # Adicionar anotações de valor nos pontos da linha
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

    # Configuração do Layout do Gráfico
    fig_main.update_layout(
        title=f"Evolução das Métricas por Semana do Mês",
        xaxis=dict(
            title="Semana do Mês",
            tickmode='array',
            tickvals=list(range(1, df_chart_data['Semana_do_Mes_Num'].max() + 1)),
            ticktext=[f'Semana {s}' for s in range(1, df_chart_data['Semana_do_Mes_Num'].max() + 1)],
            showgrid=True,
            gridcolor='lightgrey',
            automargin=True,
            tickangle=0 # Não rotacionar os rótulos de semana
        ),
        yaxis=dict(
            title="Contagem", # Generalizando o título do eixo Y
            tickformat=",.0f",
            showgrid=True,
            gridcolor='lightgrey'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        height=550,
        annotations=all_annotations
    )
    st.plotly_chart(fig_main, use_container_width=True)

st.markdown("---")

# --- Seção de Tabela de Comparação (mantida como estava) ---
st.header(f"Comparativo Histórico da Mesma Semana do Mês para as Métricas")

# Obter todas as semanas do mês únicas no período filtrado
semanas_do_mes_unicas = sorted(df_grouped_by_week_in_month['Semana_do_Mes_Num'].unique())

if not semanas_do_mes_unicas or not metricas_selecionadas:
    st.info("Não há semanas do mês ou métricas selecionadas para comparar.")
else:
    for metrica_tabela in metricas_selecionadas:
        st.subheader(f"Métrica: {metrica_tabela}")
        tabela_dados = []

        for semana_num in semanas_do_mes_unicas:
            df_semana_especifica = df_grouped_by_week_in_month[(df_grouped_by_week_in_month['Semana_do_Mes_Num'] == semana_num)].copy()

            if df_semana_especifica.empty:
                continue

            df_semana_especifica = df_semana_especifica.sort_values(by=['Ano', 'Mes'])

            # Adicionar a linha de separação
            sep_row = {'Mês e Ano': f'--- Semana {semana_num} ---'}

            meses_e_anos_presentes = df_semana_especifica['Mes_Ano'].unique()

            expected_cols_for_week = set()
            expected_cols_for_week.add(f'Valor ({metrica_tabela})')

            for i in range(len(meses_e_anos_presentes)):
                current_month_label = meses_e_anos_presentes
