import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date, timedelta

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

# Agrupa os dados por semana do mês para o GRÁFICO E TABELA
# Isso garante um único ponto por semana do mês
df_grouped = df.groupby(
    ['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano']) \
    .agg({col: 'sum' for col in df_original.columns if col != 'Data'}).reset_index() \
    .sort_values(['Ano','Mes','Semana_do_Mes_Num'])

# Preenche o df_grouped para garantir que todas as semanas de 1 a 5 apareçam,
# mesmo se não houver dados para elas em um mês/ano específico.
full_index_data = []
for ano in df['Ano'].unique():
    for mes_num, label_mes in df[['Mes', 'Label_Mes']].drop_duplicates().values:
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
metricas = [c for c in df_original.columns if c not in ['Data']]
selecionadas = st.sidebar.multiselect("Selecione a(s) Métrica(s)", metricas, default=[metricas[0]] if metricas else [])

# — Seção do Gráfico —
st.header("Evolução das Métricas por Semana do Mês")

if not df_grouped.empty and selecionadas: # Usar df_grouped para o gráfico
    fig = go.Figure()
    meses = sorted(df_grouped['Mes_Ano'].unique(), # Usar df_grouped para meses únicos
                   key=lambda x: (int(x.split(' ')[1]), pd.to_datetime(x.split(' ')[0], format='%b').month))
    cores = ['blue','red','green','purple','orange','brown','pink','grey','cyan','magenta']
    ci = 0
    ann = []

    for met in selecionadas:
        for ma in meses:
            # Filtra os dados AGREGADOS para o mês/ano atual
            tmp = df_grouped[df_grouped['Mes_Ano']==ma].sort_values('Semana_do_Mes_Num')

            # Opcional: Se você quer que as linhas não conectem pontos onde o valor é 0,
            # filtre apenas onde o valor da métrica é maior que 0.
            # Se você quer ver as linhas passando pelo 0, remova esta linha.
            # tmp = tmp[tmp[met] > 0] 

            if not tmp.empty:
                cor = cores[ci % len(cores)]
                ci += 1
                fig.add_trace(go.Scatter(
                    x=tmp['Semana_do_Mes_Num'], # Eixo X: número da semana do mês (já agrupado)
                    y=tmp[met], # Eixo Y: valor da métrica (já somado/agregado)
                    mode='lines+markers',
                    name=f"{ma} ({met})",
                    line=dict(color=cor, width=2),
                    customdata=tmp[['Full_Label', met]].values,
                    hovertemplate="<b>%{customdata[0]} (" + met + ")</b><br>Valor: %{customdata[1]:,.0f}<extra></extra>"
                ))
                # Adiciona anotações apenas para pontos com valor > 0, para não poluir
                for _, row in tmp.iterrows():
                    if row[met] > 0: # Adiciona anotação apenas se o valor não for zero
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
            tickvals=list(range(1, 6)),
            ticktext=[f"Semana {i}" for i in range(1, 6)],
            showgrid=True,
            gridcolor='lightgrey',
            type='category' # Trata o eixo X como categorias
        ),
        yaxis=dict(title="Contagem", tickformat=",.0f", showgrid=True, gridcolor='lightgrey'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        height=550,
        annotations=ann
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 Por favor, selecione ao menos uma métrica para visualizar o gráfico.")

st.markdown("---")

# — Seção da Tabela Comparativa —
st.header("Comparativo Histórico da Mesma Semana do Mês")

if selecionadas:
    records = []
    semanas = sorted(df_grouped['Semana_do_Mes_Num'].unique())
    for sem in semanas:
        records.append({'Período / Semana': f"--- Semana {sem} ---"})
        df_sem = df_grouped[df_grouped['Semana_do_Mes_Num']==sem].sort_values(['Ano','Mes'])
        vals = {met: {} for met in selecionadas}

        for _, r in df_sem.iterrows():
            lab = f"{r['Label_Mes']} {r['Ano']}"
            rec = {'Período / Semana': lab}

            for met in selecionadas:
                rec[f"{met} (Valor)"] = r[met]
                vals[met][lab] = r[met]

                for prev_lab, prev_val in vals[met].items():
                    if prev_lab != lab and prev_val is not None and pd.notna(prev_val):
                        change = r[met]-prev_val
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
            st.dataframe(df_vis.reset_index().assign(Semana_do_Mes_Calculada=df_vis.index.to_series().apply(semana_do_mes)))
