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
df_comparacao_semana_mes['Label_Mes'] = df_comparacao_semana_mes.index.strftime('%b')

# Adicionar a coluna de Mês/Ano para agrupar e calcular MoM
df_comparacao_semana_mes['Mes_Ano'] = df_comparacao_semana_mes['Label_Mes'] + ' ' + df_comparacao_semana_mes['Ano'].astype(str)


# Agrupar por Ano, Mês, Semana do Mês para obter os totais
df_grouped_by_week_in_month = df_comparacao_semana_mes.groupby(['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano']).agg(
    {col: 'sum' for col in df_original.columns if col not in ['Data']}
).reset_index()

# Ordenar para garantir a consistência
df_grouped_by_week_in_month = df_grouped_by_week_in_month.sort_values(by=['Ano', 'Mes', 'Semana_do_Mes_Num'])

# --- Seleção da Métrica Principal ---
metricas_disponiveis = [col for col in df_grouped_by_week_in_month.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano']]
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=0
)

# --- Criar o DataFrame para o Gráfico Principal ---
df_chart_data = df_grouped_by_week_in_month.copy()

# Criar um rótulo completo para o hover (Mês e Ano S Semana X)
df_chart_data['Full_Label_X_Hover'] = df_chart_data['Mes_Ano'] + ' S' + df_chart_data['Semana_do_Mes_Num'].astype(str)


# --- Gráfico de Linhas (com uma linha para cada mês) ---
st.header(f"Evolução de {metrica_principal} (Contagem) por Semana do Mês")

if df_chart_data.empty:
    st.warning("Nenhum dado encontrado para o período selecionado para exibir o gráfico.")
else: # <-- Este é o 'else' que estava faltando
    fig_main = go.Figure()

    # Obter os meses únicos no período filtrado
    meses_para_plotar = sorted(df_chart_data['Mes_Ano'].unique(), 
                                key=lambda x: (int(x.split(' ')[1]), pd.to_datetime(x.split(' ')[0], format='%b').month))

    # Definir algumas cores para as linhas (você pode expandir esta lista)
    cores = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'grey']
    
    # Lista para armazenar todas as anotações (valores nos pontos)
    all_annotations = []

    # Iterar por cada mês para criar uma linha separada
    for i, mes_ano in enumerate(meses_para_plotar):
        df_mes = df_chart_data[df_chart_data['Mes_Ano'] == mes_ano].copy()
        
        if not df_mes.empty:
            current_color = cores[i % len(cores)] # Cicla pelas cores

            fig_main.add_trace(go.Scatter(
                x=df_mes['Semana_do_Mes_Num'], # Eixo X é a Semana do Mês
                y=df_mes[metrica_principal],
                mode='lines+markers',
                name=f'{mes_ano} ({metrica_principal})',
                line=dict(color=current_color, width=2),
                hovertemplate="<b>%{customdata[0]}</b><br>Valor: %{y:,.0f}<extra></extra>",
                customdata=df_mes[['Full_Label_X_Hover']]
            ))

            # Adicionar anotações de valor nos pontos da linha
            for _, row in df_mes.iterrows():
                if pd.notna(row[metrica_principal]):
                    all_annotations.append(dict(
                        x=row['Semana_do_Mes_Num'],
                        y=row[metrica_principal],
                        text=f"{row[metrica_principal]:,.0f}",
                        showarrow=False,
                        yshift=10,
                        font=dict(color=current_color, size=10)
                    ))
    
    # Configuração do Layout do Gráfico
    # Este bloco deve estar na mesma indentação do `fig_main = go.Figure()`
    fig_main.update_layout(
        title=f"Evolução de {metrica_principal} por Semana do Mês (Comparativo Mensal)",
        xaxis=dict(
            title="Semana do Mês",
            tickmode='array',
            # Queremos ticks de 1 a 5 (ou o máximo de semanas que você tem)
            tickvals=list(range(1, df_chart_data['Semana_do_Mes_Num'].max() + 1)),
            ticktext=[f'Semana {s}' for s in range(1, df_chart_data['Semana_do_Mes_Num'].max() + 1)],
            showgrid=True,
            gridcolor='lightgrey',
            automargin=True,
            tickangle=0 # Não rotacionar os rótulos de semana
        ),
        yaxis=dict(
            title=f"{metrica_principal} (Contagem)",
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
        annotations=all_annotations # Adiciona todas as anotações de valor nos pontos
    )
    st.plotly_chart(fig_main, use_container_width=True)

st.markdown("---")

# --- Seção de Tabela de Comparação (mantida como estava) ---
# --- Tabela de Comparação Dinâmica "Semana 1 Julho vs Semana 1 Junho vs Semana 1 Maio" ---
st.header(f"Comparativo Histórico da Mesma Semana do Mês para {metrica_principal}")

# Obter todas as semanas do mês únicas no período filtrado
semanas_do_mes_unicas = sorted(df_grouped_by_week_in_month['Semana_do_Mes_Num'].unique())

if not semanas_do_mes_unicas:
    st.info("Não há semanas do mês para comparar no período selecionado.")
else:
    tabela_dados = []

    for semana_num in semanas_do_mes_unicas:
        df_semana_especifica = df_grouped_by_week_in_month[
            df_grouped_by_week_in_month['Semana_do_Mes_Num'] == semana_num
        ].copy()

        if df_semana_especifica.empty:
            continue

        df_semana_especifica = df_semana_especifica.sort_values(by=['Ano', 'Mes'])

        # Adicionar a linha de separação
        sep_row = {'Mês e Ano': f'--- Semana {semana_num} ---'}
        
        meses_e_anos_presentes = df_semana_especifica['Mes_Ano'].unique()

        expected_cols_for_week = set()
        expected_cols_for_week.add(f'Valor ({metrica_principal})')

        for i in range(len(meses_e_anos_presentes)):
            current_month_label = meses_e_anos_presentes[i]
            for j in range(i):
                prev_month_label = meses_e_anos_presentes[j]
                expected_cols_for_week.add(f'vs. {prev_month_label} (Val Abs)')
                expected_cols_for_week.add(f'vs. {prev_month_label} (%)')
        
        for col_name in expected_cols_for_week:
            sep_row[col_name] = ''
        
        tabela_dados.append(sep_row)
        
        referencias_valores = {} 

        for idx, row in df_semana_especifica.iterrows():
            mes_ano_label = f"{row['Label_Mes']} {row['Ano']}"
            referencias_valores[mes_ano_label] = row[metrica_principal]

            linha_tabela_item = {'Mês e Ano': mes_ano_label, f'Valor ({metrica_principal})': row[metrica_principal]}
            
            meses_anteriores_para_comparar = []
            for prev_label, prev_val in referencias_valores.items():
                if prev_label != mes_ano_label:
                    meses_anteriores_para_comparar.append((prev_label, prev_val))
            
            meses_anteriores_para_comparar.sort(key=lambda x: (int(x[0].split(' ')[1]), pd.to_datetime(x[0].split(' ')[0], format='%b').month))

            for prev_label, prev_val in meses_anteriores_para_comparar:
                col_name_percent = f'vs. {prev_label} (%)'
                col_name_abs = f'vs. {prev_label} (Val Abs)'

                if pd.notna(prev_val) and prev_val != 0:
                    percent_diff = ((row[metrica_principal] - prev_val) / prev_val) * 100
                    linha_tabela_item[col_name_abs] = row[metrica_principal] - prev_val
                    linha_tabela_item[col_name_percent] = f"{percent_diff:,.2f}%"
                else:
                    linha_tabela_item[col_name_abs] = np.nan
                    linha_tabela_item[col_name_percent] = "N/A"
                
            tabela_dados.append(linha_tabela_item)
        
    if tabela_dados:
        all_cols_in_tables = set()
        for row_dict in tabela_dados:
            all_cols_in_tables.update(row_dict.keys())
        
        colunas_ordenadas = ['Mês e Ano', f'Valor ({metrica_principal})']
        comp_cols = [col for col in list(all_cols_in_tables) if 'vs.' in col]
        
        def sort_comp_cols(col_name):
            parts = col_name.split(' ')
            if len(parts) >= 3 and parts[0] == 'vs.':
                try:
                    month_str = parts[1]
                    year_str = parts[2]
                    month_num = pd.to_datetime(month_str, format='%b').month
                    year_num = int(year_str)
                    return (year_num, month_num, 'Val Abs' if 'Val Abs' in col_name else '%')
                except ValueError:
                    return (9999, 99, col_name)
            return (9999, 99, col_name)

        comp_cols.sort(key=sort_comp_cols)

        colunas_ordenadas.extend(comp_cols)
        
        df_final_tabela = pd.DataFrame(tabela_dados, columns=colunas_ordenadas)

        format_dict_values = {col: "{:,.0f}" for col in df_final_tabela.columns if 'Valor' in col and '%' not in col and 'Abs' not in col}
        format_dict_abs = {col: "{:,.0f}" for col in df_final_tabela.columns if 'Val Abs' in col}
        format_dict_percent = {col: "{}" for col in df_final_tabela.columns if '%' in col}

        format_dict_combined = {**format_dict_values, **format_dict_abs, **format_dict_percent}

        rows_to_format_mask = ~df_final_tabela['Mês e Ano'].astype(str).str.startswith('---')
        
        cols_to_format = [col for col in df_final_tabela.columns if col != 'Mês e Ano' and col in format_dict_combined]

        st.dataframe(df_final_tabela.style.format(format_dict_combined,
            subset=pd.IndexSlice[rows_to_format_mask, cols_to_format]
        ))
    else:
        st.info("Não há dados suficientes para gerar a tabela de comparativos para a Semana do Mês no período selecionado.")


st.markdown("---")

# --- SEÇÃO DE VISUALIZAÇÃO DE DADOS BRUTOS (OPCIONAL) ---
st.header("Visualização de Dados Semanais Brutos por Período Selecionado")

min_date_raw_vis = df_original.index.min().date()
max_date_raw_vis = df_original.index.max().date()

st.sidebar.subheader("Ver Dados Semanais Detalhados")
data_inicio_vis = st.sidebar.date_input("Data de Início", value=min_date_raw_vis, min_value=min_date_raw_vis, max_value=max_date_raw_vis, key="vis_start")
data_fim_vis = st.sidebar.date_input("Data de Fim", value=max_date_raw_vis, min_value=min_date_raw_vis, max_value=max_date_raw_vis, key="vis_end")

if data_inicio_vis > data_fim_vis:
    st.sidebar.error("Erro: A data de início não pode ser posterior à data de fim.")
    st.stop()

df_visualizacao = df_original.loc[pd.to_datetime(data_inicio_vis):pd.to_datetime(data_fim_vis)].copy()

if df_visualizacao.empty:
    st.warning("Nenhum dado encontrado para o período selecionado para visualização.")
else:
    with st.expander("🔍 Ver Dados Semanais Filtrados"):
        st.dataframe(df_visualizacao.reset_index())
