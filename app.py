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
df_filtrado = df_original.loc[pd.to_datetime(data_inicio_grafico):pd.to_datetime(data_fim_grafico)].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o período selecionado no gráfico principal. Por favor, ajuste as datas.")
    st.stop()


# --- Preparar dados para comparação de "Semana do Mês" ---
df_comparacao_semana_mes = df_filtrado.copy()

df_comparacao_semana_mes['Ano'] = df_comparacao_semana_mes.index.year
df_comparacao_semana_mes['Mes'] = df_comparacao_semana_mes.index.month
df_comparacao_semana_mes['Semana_do_Mes_Num'] = ((df_comparacao_semana_mes.index.day - 1) // 7) + 1
df_comparacao_semana_mes['Label_Mes'] = df_comparacao_semana_mes.index.strftime('%b') # Ex: Jun, Jul

# Agrupar por Ano, Mês, Semana do Mês para obter os totais
df_grouped_by_week_in_month = df_comparacao_semana_mes.groupby(['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes']).agg(
    {col: 'sum' for col in df_original.columns}
).reset_index()

# Ordenar para garantir a consistência
df_grouped_by_week_in_month = df_grouped_by_week_in_month.sort_values(by=['Ano', 'Mes', 'Semana_do_Mes_Num'])

# --- Seleção da Métrica Principal ---
metricas_disponiveis = [col for col in df_grouped_by_week_in_month.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes']]
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=0
)

# --- Criar o DataFrame para o Gráfico Principal (apenas "Realizado") ---
# Este DataFrame conterá apenas o valor 'Realizado' para cada ponto
df_chart_data = df_grouped_by_week_in_month.copy()
df_chart_data['Label_Eixo_X'] = df_chart_data['Label_Mes'] + ' S' + df_chart_data['Semana_do_Mes_Num'].astype(str) + ' ' + df_chart_data['Ano'].astype(str)

# --- Gráfico de Linhas (apenas "Realizado") ---
st.header(f"Evolução de {metrica_principal} (Contagem) por Semana do Mês")

if df_chart_data.empty:
    st.warning("Não há dados suficientes para exibir o gráfico com os filtros selecionados.")
else:
    fig_main = go.Figure()

    fig_main.add_trace(go.Scatter(
        x=df_chart_data['Label_Eixo_X'],
        y=df_chart_data[metrica_principal],
        mode='lines+markers',
        name='Realizado (Semana Atual do Mês)',
        line=dict(color='blue', width=2),
        hovertemplate="<b>%{x}</b><br>Realizado: %{y:,.0f}<extra></extra>"
    ))

    # Adicionar rótulos de valor para Realizado
    for i, row in df_chart_data.iterrows():
        if pd.notna(row[metrica_principal]):
            fig_main.add_annotation(
                x=row['Label_Eixo_X'],
                y=row[metrica_principal],
                text=f"{row[metrica_principal]:,.0f}",
                showarrow=False,
                yshift=10,
                font=dict(color='blue', size=10)
            )

    fig_main.update_layout(
        title=f"Evolução de {metrica_principal} por Semana do Mês",
        xaxis_title="Período (Mês e Semana)",
        yaxis=dict(
            title=f"{metrica_principal} (Contagem)",
            tickformat=",.0f"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        height=450 # Um pouco menor para dar espaço à tabela
    )
    st.plotly_chart(fig_main, use_container_width=True)

st.markdown("---")

# --- Tabela de Comparação Dinâmica "Semana 1 Julho vs Semana 1 Junho vs Semana 1 Maio" ---
st.header(f"Comparativo Histórico da Mesma Semana do Mês para {metrica_principal}")

# Obter todas as semanas do mês únicas no período filtrado
semanas_do_mes_unicas = sorted(df_grouped_by_week_in_month['Semana_do_Mes_Num'].unique())

if not semanas_do_mes_unicas:
    st.info("Não há semanas do mês para comparar no período selecionado.")
else:
    # Criar uma lista para armazenar os dados da tabela
    tabela_dados = []

    # Iterar por cada Semana do Mês (S1, S2, etc.)
    for semana_num in semanas_do_mes_unicas:
        st.subheader(f"Comparativo para Semana {semana_num}")
        
        # Filtrar dados para a semana atual do mês
        df_semana_especifica = df_grouped_by_week_in_month[
            df_grouped_by_week_in_month['Semana_do_Mes_Num'] == semana_num
        ].copy()

        if df_semana_especifica.empty:
            st.info(f"Não há dados para a Semana {semana_num} no período selecionado.")
            continue

        # Ordenar pelo mês (e ano) para garantir a ordem cronológica da comparação
        df_semana_especifica = df_semana_especifica.sort_values(by=['Ano', 'Mes'])

        # Criar colunas para a tabela de comparação
        colunas_tabela = ['Mês e Ano']
        valores_semanais = []
        
        # Coluna para o valor atual
        colunas_tabela.append(f'Valor ({metrica_principal})')
        
        # Armazenar os valores de referência para cálculo percentual
        referencias_valores = {} 

        for idx, row in df_semana_especifica.iterrows():
            mes_ano_label = f"{row['Label_Mes']} {row['Ano']}"
            referencias_valores[mes_ano_label] = row[metrica_principal]

            linha_tabela = {'Mês e Ano': mes_ano_label, f'Valor ({metrica_principal})': row[metrica_principal]}
            
            # Adicionar comparações percentuais com meses anteriores
            meses_anteriores_para_comparar = []
            for prev_label, prev_val in referencias_valores.items():
                if prev_label != mes_ano_label: # Não comparar com ele mesmo
                    meses_anteriores_para_comparar.append((prev_label, prev_val))
            
            # Ordenar meses anteriores do mais antigo para o mais recente para a exibição
            meses_anteriores_para_comparar.sort(key=lambda x: (int(x[0].split(' ')[1]), list(pd.to_datetime(str(pd.to_datetime(x[0].split(' ')[0], format='%b').month), format='%m').strftime('%b%Y'))[0]))

            for prev_label, prev_val in meses_anteriores_para_comparar:
                col_name_percent = f'vs. {prev_label} (%)'
                col_name_abs = f'vs. {prev_label} (Val)'

                if prev_val is not None and prev_val != 0:
                    percent_diff = ((row[metrica_principal] - prev_val) / prev_val) * 100
                    linha_tabela[col_name_abs] = row[metrica_principal] - prev_val
                    linha_tabela[col_name_percent] = f"{percent_diff:,.2f}%"
                else:
                    linha_tabela[col_name_abs] = np.nan
                    linha_tabela[col_name_percent] = "N/A" if prev_val == 0 else "" # Trata divisão por zero ou dados ausentes
                
                # Adicionar colunas se ainda não existirem
                if col_name_abs not in colunas_tabela:
                    colunas_tabela.append(col_name_abs)
                if col_name_percent not in colunas_tabela:
                    colunas_tabela.append(col_name_percent)
            
            tabela_dados.append(linha_tabela)

    # Criar um DataFrame final para a tabela de cada semana
    if tabela_dados:
        # Criar um set de todas as colunas para garantir que todas as tabelas tenham as mesmas colunas
        all_cols_in_tables = set()
        for row_dict in tabela_dados:
            all_cols_in_tables.update(row_dict.keys())
        
        df_final_tabela = pd.DataFrame(tabela_dados, columns=sorted(list(all_cols_in_tables), key=lambda x: (x.split('(')[0], x))) # Ordena colunas
        st.dataframe(df_final_tabela.style.format(
            {col: "{:,.0f}" for col in df_final_tabela.columns if 'Valor' in col and '%'
