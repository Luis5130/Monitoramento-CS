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

# --- Seleção da(s) Métrica(s) Principal(is) ---
metricas_disponiveis = [col for col in df_grouped_by_week_in_month.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano']]

# Alterado de selectbox para multiselect e o nome do label
metricas_selecionadas = st.sidebar.multiselect(
    "Status CS - DogHero", # Novo nome do label
    metricas_disponiveis,
    default=[metricas_disponiveis[0]] if metricas_disponiveis else [] # Exibe a primeira métrica por padrão se houver alguma
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
    cor_index = 0 # Reiniciar o índice de cor para cada nova execução

    # Lista para armazenar todas as anotações (valores nos pontos)
    all_annotations = []

    # Iterar por cada métrica selecionada
    for metrica in metricas_selecionadas:
        # Iterar por cada mês para criar uma linha separada para cada métrica
        for mes_ano in meses_para_plotar:
            df_mes_metrica = df_chart_data[
                (df_chart_data['Mes_Ano'] == mes_ano)
            ].copy()

            if not df_mes_metrica.empty and metrica in df_mes_metrica.columns:
                current_color = cores[(cor_index) % len(cores)]
                cor_index += 1 # Incrementar o índice de cor após cada linha plotada

                fig_main.add_trace(go.Scatter(
                    x=df_mes_metrica['Semana_do_Mes_Num'], # Eixo X é a Semana do Mês
                    y=df_mes_metrica.get(metrica), # Usar .get() para evitar KeyError se a coluna não existir (improvável aqui, mas boa prática)
                    mode='lines+markers',
                    name=f'{mes_ano} ({metrica})', # Nome da linha na legenda
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
            title="Contagem", # Generalizando o título do eixo Y já que múltiplas métricas podem ter unidades diferentes
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

# --- Seção de Tabela de Comparação (Consolidada) ---
st.header(f"Comparativo Histórico da Mesma Semana do Mês")

# Obter todas as semanas do mês únicas no período filtrado
semanas_do_mes_unicas = sorted(df_grouped_by_week_in_month['Semana_do_Mes_Num'].unique())

if not semanas_do_mes_unicas or not metricas_selecionadas:
    st.info("Não há semanas do mês ou métricas selecionadas para comparar na tabela.")
else:
    tabela_dados_consolidada = []

    for semana_num in semanas_do_mes_unicas:
        # Adicionar a linha de separação para cada semana
        sep_row = {'Período / Semana': f'--- Semana {semana_num} ---'}
        tabela_dados_consolidada.append(sep_row)

        df_semana_especifica = df_grouped_by_week_in_month[
            df_grouped_by_week_in_month['Semana_do_Mes_Num'] == semana_num
        ].copy()

        df_semana_especifica = df_semana_especifica.sort_values(by=['Ano', 'Mes'])

        meses_e_anos_presentes = df_semana_especifica['Mes_Ano'].unique()
        
        # Dicionário para armazenar os valores das métricas para os meses anteriores na mesma semana
        valores_por_metrica_e_mes = {metrica: {} for metrica in metricas_selecionadas}

        for idx, row in df_semana_especifica.iterrows():
            mes_ano_label = f"{row['Label_Mes']} {row['Ano']}"
            linha_tabela_item = {'Período / Semana': mes_ano_label}

            for metrica_col in metricas_selecionadas:
                current_value = row.get(metrica_col)
                linha_tabela_item[f'{metrica_col} (Valor)'] = current_value
                valores_por_metrica_e_mes[metrica_col][mes_ano_label] = current_value

                # Calcular comparações para esta métrica
                meses_anteriores_para_comparar = []
                for prev_label, prev_val in valores_por_metrica_e_mes[metrica_col].items():
                    if prev_label != mes_ano_label:
                        meses_anteriores_para_comparar.append((prev_label, prev_val))
                
                # Ordenar para garantir que as comparações sigam a ordem cronológica
                meses_anteriores_para_comparar.sort(key=lambda x: (int(x[0].split(' ')[1]), pd.to_datetime(x[0].split(' ')[0], format='%b').month))

                for prev_label, prev_val in meses_anteriores_para_comparar:
                    col_name_percent = f'{metrica_col} vs. {prev_label} (%)'
                    col_name_abs = f'{metrica_col} vs. {prev_label} (Val Abs)'

                    if pd.notna(current_value) and pd.notna(prev_val) and prev_val != 0:
                        percent_diff = ((current_value - prev_val) / prev_val) * 100
                        linha_tabela_item[col_name_abs] = current_value - prev_val
                        linha_tabela_item[col_name_percent] = f"{percent_diff:,.2f}%"
                    else:
                        linha_tabela_item[col_name_abs] = np.nan
                        linha_tabela_item[col_name_percent] = "N/A"
            
            tabela_dados_consolidada.append(linha_tabela_item)
        
    if tabela_dados_consolidada:
        # Determinar todas as colunas que aparecerão na tabela final
        all_cols = set()
        for row_dict in tabela_dados_consolidada:
            all_cols.update(row_dict.keys())
        
        # Definir a ordem das colunas
        colunas_ordenadas = ['Período / Semana']
        
        # Adicionar as colunas de métricas e suas comparações em ordem lógica
        for metrica in metricas_selecionadas:
            colunas_ordenadas.append(f'{metrica} (Valor)')
            
            # Coletar e ordenar as colunas de comparação para esta métrica
            comp_cols_for_metric = [col for col in all_cols if col.startswith(f'{metrica} vs.')]
            
            # Função de ordenação para as colunas de comparação: primeiro por ano, depois por mês, e então por tipo (Val Abs vs %)
            def sort_comp_cols(col_name_full):
                # Extrair o nome da métrica para remover
                parts = col_name_full.split(' vs. ')
                if len(parts) > 1:
                    comparison_part = parts[1] # Ex: 'May 2025 (%)' ou 'Jun 2025 (Val Abs)'
                    
                    # Tentar extrair o mês e o ano da parte da comparação
                    date_parts = comparison_part.split(' ')
                    if len(date_parts) >= 2:
                        try:
                            month_str = date_parts[0]
                            year_str = date_parts[1].split('(')[0] # Remover o parêntese para o ano
                            month_num = pd.to_datetime(month_str, format='%b').month
                            year_num = int(year_str)
                            type_indicator = 0 if 'Val Abs' in col_name_full else 1 # 0 para Val Abs, 1 para %
                            return (year_num, month_num, type_indicator)
                        except (ValueError, IndexError):
                            pass # Fallback para o caso de parsing falhar
                return (9999, 99, 99) # Valores altos para ir para o final
            
            comp_cols_for_metric.sort(key=sort_comp_cols)
            colunas_ordenadas.extend(comp_cols_for_metric)

        df_final_tabela = pd.DataFrame(tabela_dados_consolidada, columns=[col for col in colunas_ordenadas if col in all_cols])


        # Dicionário de formatação
        format_dict_combined = {}
        for col in df_final_tabela.columns:
            if 'Valor)' in col and 'Val Abs' not in col:
                format_dict_combined[col] = "{:,.0f}"
            elif 'Val Abs' in col:
                format_dict_combined[col] = "{:,.0f}"
            elif '%' in col:
                format_dict_combined[col] = "{}" # Formato já vem como string com %
        
        # Máscara para aplicar a formatação apenas nas linhas de dados, não nas linhas de separação
        rows_to_format_mask = ~df_final_tabela['Período / Semana'].astype(str).str.startswith('---')
        
        # Colunas que realmente existem no DataFrame e precisam ser formatadas
        cols_to_format = [col for col in df_final_tabela.columns if col != 'Período / Semana' and col in format_dict_combined]

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
