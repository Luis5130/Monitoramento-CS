import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date, timedelta # Importações necessárias

@st.cache_data
def carregar_dados():
    """
    Carrega os dados do arquivo CSV, formata a coluna 'Data' e define como índice.
    @st.cache_data: Armazena o DataFrame em cache para evitar recargas desnecessárias.
    """
    df = pd.read_csv("dados_semanais.csv")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", dayfirst=True)
    df = df.set_index("Data").sort_index()
    return df

# Carrega os dados uma vez
df_original = carregar_dados()

st.title("📊 Análise de Performance: Comparativo Semana do Mês (Histórico)")

# — Filtros de Período na Barra Lateral —
st.sidebar.header("Filtros de Período do Gráfico")
min_date = df_original.index.min().date()
max_date = df_original.index.max().date()

data_inicio = st.sidebar.date_input(
    "Data de Início do Gráfico", min_value=min_date, max_value=max_date, value=min_date)
data_fim = st.sidebar.date_input(
    "Data de Fim do Gráfico", min_value=min_date, max_value=max_date, value=max_date)

if data_inicio > data_fim:
    st.sidebar.error("⚠️ Data de início não pode ser maior que a data de fim.")
    st.stop()

# Filtra o DataFrame com base no período selecionado
df_filtrado = df_original.loc[data_inicio:data_fim].copy()
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o período selecionado. Por favor, ajuste os filtros.")
    st.stop()

# — Função para calcular a semana do mês baseada em intervalos fixos de dias —
def semana_do_mes(dt):
    """
    Calcula a semana do mês para uma dada data, dividindo o mês em 5 semanas fixas.
    Semana 1: Dias 1-7
    Semana 2: Dias 8-14
    Semana 3: Dias 15-21
    Semana 4: Dias 22-28
    Semana 5: Dias 29-31
    """
    dia = dt.day
    if dia <= 7:
        return 1
    elif dia <= 14:
        return 2
    elif dia <= 21:
        return 3
    elif dia <= 28:
        return 4
    else: # Dias 29, 30, 31
        return 5

# Aplica a função de semana do mês ao DataFrame filtrado
df = df_filtrado.copy()
df['Ano'] = df.index.year
df['Mes'] = df.index.month
df['Semana_do_Mes_Num'] = df.index.to_series().apply(semana_do_mes)
df['Label_Mes'] = df.index.strftime('%b') # Ex: Jan, Feb
df['Mes_Ano'] = df['Label_Mes'] + ' ' + df['Ano'].astype(str) # Ex: Jan 2025

# DataFrame para o gráfico: usa os dados individuais do df (não agrupados ainda para o plot)
df_chart_data = df.copy()
df_chart_data['Full_Label'] = df_chart_data['Mes_Ano'] + ' S' + df_chart_data['Semana_do_Mes_Num'].astype(str)

# Agrupa os dados para a TABELA COMPARATIVA (sumariza por semana do mês)
# Isso é importante para a tabela que compara totais por semana
df_grouped = df.groupby(
    ['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano']) \
    .agg({col: 'sum' for col in df_original.columns}).reset_index() \
    .sort_values(['Ano','Mes','Semana_do_Mes_Num'])

# Preenche o df_grouped para garantir que todas as semanas de 1 a 5 apareçam na tabela
# mesmo se não houver dados para elas em um mês/ano específico.
full_index_data = []
# Pega anos e meses únicos do DataFrame filtrado para construir o índice completo
for ano in df_filtrado['Ano'].unique():
    # Pega apenas as combinações únicas de Mes e Label_Mes do df_filtrado para evitar duplicações desnecessárias
    for mes_num, label_mes in df_filtrado[['Mes', 'Label_Mes']].drop_duplicates().values:
        mes_ano_label = f"{label_mes} {ano}"
        for sem in range(1, 6): # Itera de 1 a 5 semanas fixas
            full_index_data.append({
                'Ano': ano,
                'Mes': mes_num,
                'Semana_do_Mes_Num': sem,
                'Label_Mes': label_mes,
                'Mes_Ano': mes_ano_label
            })
full_index_df = pd.DataFrame(full_index_data)

# Realiza um left merge para manter todas as combinações de semanas 1-5 e preencher NaNs com 0
df_grouped = pd.merge(full_index_df, df_grouped,
                      on=['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano'],
                      how='left').fillna(0)


# Seleciona as métricas disponíveis para o usuário
# Exclui as colunas de identificação e tempo
metricas = [c for c in df_original.columns if c not in ['Data']]
selecionadas = st.sidebar.multiselect("Selecione a(s) Métrica(s)", metricas, default=[metricas[0]] if metricas else [])

# — Seção do Gráfico —
st.header("Evolução das Métricas por Semana do Mês")

if not df_chart_data.empty and selecionadas:
    fig = go.Figure()
    # Garante que os meses sejam ordenados cronologicamente na legenda
    meses = sorted(df_chart_data['Mes_Ano'].unique(),
                   key=lambda x: (int(x.split(' ')[1]), pd.to_datetime(x.split(' ')[0], format='%b').month))
    cores = ['blue','red','green','purple','orange','brown','pink','grey','cyan','magenta']
    ci = 0 # Contador para alternar cores
    ann = [] # Lista para armazenar as anotações (rótulos de valores)

    for met in selecionadas:
        for ma in meses:
            # Filtra os dados INDIVIDUAIS para o mês/ano atual para plotar cada ponto do CSV
            tmp = df_chart_data[df_chart_data['Mes_Ano']==ma].sort_values('Data') # Ordena por data para a linha ficar correta

            if not tmp.empty:
                cor = cores[ci % len(cores)]
                ci += 1
                fig.add_trace(go.Scatter(
                    x=tmp['Semana_do_Mes_Num'], # Eixo X: número da semana do mês (categórico)
                    y=tmp[met], # Eixo Y: valor da métrica para cada ponto individual
                    mode='lines+markers', # Linhas e marcadores nos pontos
                    name=f"{ma} ({met})", # Nome da série na legenda
                    line=dict(color=cor, width=2), # Estilo da linha
                    # customdata para o hovertemplate: inclui o rótulo completo e o valor
                    customdata=tmp[['Full_Label', met]].values,
                    hovertemplate="<b>%{customdata[0]} (" + met + ")</b><br>Valor: %{customdata[1]:,.0f}<extra></extra>"
                ))
                # Adiciona anotações para cada ponto de dado original
                for _, row in tmp.iterrows():
                    ann.append(dict(
                        x=row['Semana_do_Mes_Num'], y=row[met],
                        text=f"{row[met]:,.0f}", showarrow=False, yshift=10,
                        font=dict(color=cor, size=10)
                    ))

    fig.update_layout(
        title="Evolução das Métricas por Semana do Mês",
        xaxis=dict(
            title="Semana do Mês",
            tickmode='array',
            tickvals=list(range(1, 6)), # Garante que os ticks de 1 a 5 sempre apareçam
            ticktext=[f"Semana {i}" for i in range(1, 6)], # Rótulos dos ticks
            showgrid=True,
            gridcolor='lightgrey',
            type='category' # Trata o eixo X como categorias para alinhar os pontos no mesmo "Semana Num"
        ),
        yaxis=dict(title="Contagem", tickformat=",.0f", showgrid=True, gridcolor='lightgrey'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", # Hover que mostra informações de todos os traces na mesma coordenada X
        height=550,
        annotations=ann # Adiciona as anotações ao layout do gráfico
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 Por favor, selecione ao menos uma métrica para visualizar o gráfico.")

st.markdown("---")

# — Seção da Tabela Comparativa —
st.header("Comparativo Histórico da Mesma Semana do Mês")

if selecionadas:
    records = []
    # Itera pelas semanas únicas (1 a 5) no df_grouped
    semanas = sorted(df_grouped['Semana_do_Mes_Num'].unique())
    for sem in semanas:
        records.append({'Período / Semana': f"--- Semana {sem} ---"}) # Título para cada bloco de semana
        # Filtra e ordena o df_grouped para a semana atual
        df_sem = df_grouped[df_grouped['Semana_do_Mes_Num']==sem].sort_values(['Ano','Mes'])
        vals = {met: {} for met in selecionadas} # Dicionário para armazenar valores anteriores para comparação

        for _, r in df_sem.iterrows():
            lab = f"{r['Label_Mes']} {r['Ano']}"
            rec = {'Período / Semana': lab} # Rótulo da linha (ex: Mai 2025)

            for met in selecionadas:
                rec[f"{met} (Valor)"] = r[met]
                vals[met][lab] = r[met] # Armazena o valor atual para futuras comparações

                # Calcula a variação em relação aos períodos anteriores já processados na mesma semana
                for prev_lab, prev_val in vals[met].items():
                    if prev_lab != lab and prev_val is not None and pd.notna(prev_val):
                        change = r[met]-prev_val
                        # Evita divisão por zero: se prev_val for 0, o percentual é N/A
                        pct = ( (change/prev_val)*100 ) if prev_val != 0 else np.nan
                        rec[f"{met} vs. {prev_lab} (Val Abs)"] = change
                        rec[f"{met} vs. {prev_lab} (%)"] = f"{pct:,.2f}%" if pd.notna(pct) else "N/A"
            records.append(rec)
    df_tab = pd.DataFrame(records)
    st.dataframe(df_tab)
else:
    st.info("📈 Selecione métricas no menu lateral para visualizar a tabela comparativa.")

st.markdown("---")

# — Seção de Visualização de Dados Brutos —
st.header("Visualização de Dados Semanais Brutos por Período Selecionado")
st.sidebar.header("Ver Dados Semanais Detalhados")

# Filtros para a visualização dos dados brutos (separados dos filtros do gráfico)
data_inicio_vis = st.sidebar.date_input("Data de Início", min_value=min_date, max_value=max_date, value=min_date, key="vis_start")
data_fim_vis = st.sidebar.date_input("Data de Fim", min_value=min_date, max_value=max_date, value=max_date, key="vis_end")

if data_inicio_vis > data_fim_vis:
    st.sidebar.error("⚠️ Data de início não pode ser maior que a data de fim para a visualização.")
else:
    df_vis = df_original.loc[data_inicio_vis:data_fim_vis]
    if df_vis.empty:
        st.warning("Nenhum dado nessa faixa de visualização. Ajuste as datas.")
    else:
        with st.expander("🔍 Clique para Ver Dados Semanais Filtrados"):
            # Exibe o DataFrame bruto com a coluna de semana do mês calculada
            st.dataframe(df_vis.reset_index().assign(Semana_do_Mes_Calculada=df_vis.index.to_series().apply(semana_do_mes)))
