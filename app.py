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

# --- Calcular MoM (Month-over-Month) para o gráfico ---
# Mês Anterior é o mesmo índice de Semana_do_Mes_Num no mês anterior
df_grouped_by_week_in_month['Realizado_Mes_Anterior'] = df_grouped_by_week_in_month.groupby(['Semana_do_Mes_Num'])[metrica_principal].shift(1)
df_grouped_by_week_in_month['MoM (%)'] = ((df_grouped_by_week_in_month[metrica_principal] - df_grouped_by_week_in_month['Realizado_Mes_Anterior']) / df_grouped_by_week_in_month['Realizado_Mes_Anterior']) * 100
df_grouped_by_week_in_month['MoM (%)'] = df_grouped_by_week_in_month['MoM (%)'].replace([np.inf, -np.inf], np.nan)


# --- Seleção da Métrica Principal ---
metricas_disponiveis = [col for col in df_grouped_by_week_in_month.columns if col not in ['Ano', 'Mes', 'Semana_do_Mes_Num', 'Label_Mes', 'Mes_Ano', 'Realizado_Mes_Anterior', 'MoM (%)']]
metrica_principal = st.sidebar.selectbox(
    "Selecione a Métrica para o Gráfico de Tendência",
    metricas_disponiveis,
    index=0
)

# --- Criar o DataFrame para o Gráfico Principal (apenas "Realizado") ---
df_chart_data = df_grouped_by_week_in_month.copy()
# Simplificar Label_Eixo_X para "Semana X" e adicionar rótulo do mês no hover
df_chart_data['Label_Eixo_X_Simples'] = 'Semana ' + df_chart_data['Semana_do_Mes_Num'].astype(str)
# Criar um rótulo completo para o hover
df_chart_data['Full_Label_X'] = df_chart_data['Mes_Ano'] + ' S' + df_chart_data['Semana_do_Mes_Num'].astype(str)


# --- Gráfico de Linhas (apenas "Realizado" + "Mês Anterior" + "MoM") ---
st.header(f"Evolução de {metrica_principal} (Contagem) por Semana do Mês")

if df_chart_data.empty:
    st.warning("Não há dados suficientes para exibir o gráfico com os filtros selecionados.")
else:
    fig_main = go.Figure()

    # Linha "Realizado" (Semana Atual do Mês)
    fig_main.add_trace(go.Scatter(
        x=df_chart_data['Full_Label_X'], # Usar o rótulo completo para hover e para os valores de x
        y=df_chart_data[metrica_principal],
        mode='lines+markers',
        name='Realizado (Semana Atual do Mês)',
        line=dict(color='blue', width=2),
        hovertemplate="<b>%{x}</b><br>Realizado: %{y:,.0f}<extra></extra>"
    ))

    # Linha "Mês Anterior" (se a coluna existir e houver dados)
    if 'Realizado_Mes_Anterior' in df_chart_data.columns and not df_chart_data['Realizado_Mes_Anterior'].isnull().all():
        fig_main.add_trace(go.Scatter(
            x=df_chart_data['Full_Label_X'],
            y=df_chart_data['Realizado_Mes_Anterior'],
            mode='lines+markers',
            name='Semana Correspondente do Mês Anterior',
            line=dict(color='purple', dash='dash', width=2),
            hovertemplate="<b>%{x}</b><br>Mês Anterior: %{y:,.0f}<extra></extra>"
        ))

    # Linha "MoM (%)" - em um eixo Y secundário para melhor visualização
    if 'MoM (%)' in df_chart_data.columns and not df_chart_data['MoM (%)'].isnull().all():
        fig_main.add_trace(go.Scatter(
            x=df_chart_data['Full_Label_X'],
            y=df_chart_data['MoM (%)'],
            mode='lines+markers',
            name='MoM (%) (Semana do Mês)',
            yaxis='y2', # Atribui ao segundo eixo Y
            line=dict(color='orange', dash='dot', width=2),
            hovertemplate="<b>%{x}</b><br>MoM: %{y:,.2f}%<extra></extra>"
        ))

    # Adicionar rótulos de valor para Realizado e Mês Anterior
    for i, row in df_chart_data.iterrows():
        if pd.notna(row[metrica_principal]):
            fig_main.add_annotation(
                x=row['Full_Label_X'],
                y=row[metrica_principal],
                text=f"{row[metrica_principal]:,.0f}",
                showarrow=False,
                yshift=10,
                font=dict(color='blue', size=10)
            )
        if pd.notna(row['Realizado_Mes_Anterior']):
            fig_main.add_annotation(
                x=row['Full_Label_X'],
                y=row['Realizado_Mes_Anterior'],
                text=f"{row['Realizado_Mes_Anterior']:,.0f}",
                showarrow=False,
                yshift=10,
                font=dict(color='purple', size=10)
            )
        if pd.notna(row['MoM (%)']):
            fig_main.add_annotation(
                x=row['Full_Label_X'],
                y=row['MoM (%)'],
                text=f"{row['MoM (%)']:,.2f}%",
                showarrow=False,
                yshift=-15 if row['MoM (%)'] < 0 else 10, # Ajuste a posição do rótulo para valores negativos
                font=dict(color='orange', size=10)
            )

    # --- Adicionar linhas verticais para separar os meses ---
    # Encontrar as transições de mês no eixo X_Simples (semanas)
    meses_unicos = df_chart_data['Mes_Ano'].unique()
    for i, mes_ano in enumerate(meses_unicos):
        # Encontre o primeiro ponto de dados para cada mês no eixo X completo
        first_point_of_month = df_chart_data[df_chart_data['Mes_Ano'] == mes_ano]['Full_Label_X'].iloc[0]
        # Adiciona uma linha vertical no início de cada mês (ou um pouco antes para que a primeira semana fique dentro)
        if i > 0: # Para evitar uma linha antes do primeiro mês
            fig_main.add_vline(x=first_point_of_month, line_width=1, line_dash="dash", line_color="grey")
            # Adicionar rótulo do mês na linha vertical
            fig_main.add_annotation(
                x=first_point_of_month,
                yref="paper", y=1.05, # Posição Y no topo do gráfico
                text=mes_ano,
                showarrow=False,
                font=dict(size=10, color="grey"),
                xanchor="left", # Ancorar à esquerda da linha
                textangle=-45 # Rotacionar texto
            )


    fig_main.update_layout(
        title=f"Evolução de {metrica_principal} por Semana do Mês (MoM)",
        xaxis=dict(
            title="Período (Semana do Mês)",
            tickmode='array', # Usar tickmode 'array'
            tickvals=df_chart_data['Full_Label_X'].tolist(), # Usar os rótulos completos para as posições
            ticktext=df_chart_data['Label_Eixo_X_Simples'].tolist(), # Exibir apenas "Semana X"
            showgrid=True, # Mostrar grid vertical para as semanas
            gridcolor='lightgrey',
            # Isso é para evitar que os ticks se sobreponham, mas os labels dos meses estarão nas linhas
            automargin=True,
            tickangle=-45
        ),
        yaxis=dict(
            title=f"{metrica_principal} (Contagem)",
            tickformat=",.0f",
            showgrid=True,
            gridcolor='lightgrey'
        ),
        yaxis2=dict(
            title="MoM (%)",
            overlaying='y', # Sobrepõe ao primeiro eixo Y
            side='right', # Posiciona no lado direito
            tickformat=",.2f", # Formata como porcentagem
            showgrid=False # Não mostrar grade para o segundo eixo
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        height=550 # Aumentar a altura para acomodar os rótulos dos meses
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
        # Preencher colunas que estarão presentes no DataFrame final com NaN ou strings vazias
        for col_prefix in ['Valor', 'vs.']: # Prefixo das colunas que podem ser dinâmicas
            for col_suffix in [' (Contagem)', ' (Val Abs)', ' (%)']: # Sufixos comuns
                col_name_guess = f"{col_prefix} ({metrica_principal}){col_suffix}"
                if col_name_guess in df_semana_especifica.columns or any(c.startswith(col_prefix) and c.endswith(col_suffix) for c in df_semana_especifica.columns):
                    sep_row[col_name_guess] = '' # Preencher com string vazia
        # Adicionar colunas de comparação específicas
        meses_e_anos_para_cols = df_semana_especifica['Mes_Ano'].tolist()
        for i in range(len(meses_e_anos_para_cols)):
            for j in range(i + 1, len(meses_e_anos_para_cols)):
                m1_label = meses_e_anos_para_cols[i]
                m2_label = meses_e_anos_para_cols[j]
                sep_row[f'vs. {m1_label} (Val Abs)'] = ''
                sep_row[f'vs. {m1_label} (%)'] = ''
        
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
        comp_cols.sort(key=lambda x: (int(x.split(' ')[2]), pd.to_datetime(x.split(' ')[1], format='%b').month, 'Val Abs' if 'Val Abs' in x else '%'))
        colunas_ordenadas.extend(comp_cols)
        
        df_final_tabela = pd.DataFrame(tabela_dados, columns=colunas_ordenadas)

        # Formatação
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
