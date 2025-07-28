import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date, timedelta

@st.cache_data
def carregar_dados():
    df = pd.read_csv("dados_semanais.csv")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", dayfirst=True)
    df = df.set_index("Data").sort_index()
    return df

df_original = carregar_dados()

st.title("📊 Análise de Performance: Comparativo Semana do Mês (Histórico)")

# — Filtros de Período —
min_date = df_original.index.min().date()
max_date = df_original.index.max().date()

data_inicio = st.sidebar.date_input(
    "Data de Início do Gráfico", min_value=min_date, max_value=max_date, value=min_date)
data_fim = st.sidebar.date_input(
    "Data de Fim do Gráfico", min_value=min_date, max_value=max_date, value=max_date)

if data_inicio > data_fim:
    st.sidebar.error("Data de início > data de fim.")
    st.stop()

df_filtrado = df_original.loc[data_inicio:data_fim].copy()
if df_filtrado.empty:
    st.warning("Nenhum dado no período selecionado.")
    st.stop()

# — Função REVISADA: semana do mês por intervalos fixos de dias —
def semana_do_mes(dt):
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

df = df_filtrado.copy()
df['Ano'] = df.index.year
df['Mes'] = df.index.month
df['Semana_do_Mes_Num'] = df.index.to_series().apply(semana_do_mes)
df['Label_Mes'] = df.index.strftime('%b')
df['Mes_Ano'] = df['Label_Mes'] + ' ' + df['Ano'].astype(str)

# Certificar-se de que todas as semanas do mês de 1 a 5 apareçam no agrupamento
# mesmo que não haja dados para elas em um mês específico, para garantir a estrutura do gráfico.
# Para isso, vamos criar um DataFrame completo de semanas e mesclar com os dados agrupados.
todas_semanas_mes = pd.DataFrame({'Semana_do_Mes_Num': range(1, 6)})

# Gerar todas as combinações de Ano, Mês, Label_Mes, Mes_Ano e Semana_do_Mes_Num
# para preencher possíveis lacunas (como a Semana 1 que pode estar faltando)
full_index_data = []
for ano in df['Ano'].unique():
    for mes_num, label_mes in df[['Mes', 'Label_Mes']].drop_duplicates().values:
        mes_ano_label = f"{label_mes} {ano}"
        for sem in range(1, 6): # De 1 a 5 semanas fixas
            full_index_data.append({
                'Ano': ano,
                'Mes': mes_num,
                'Semana_do_Mes_Num': sem,
                'Label_Mes': label_mes,
                'Mes_Ano': mes_ano_label
            })
full_index_df = pd.DataFrame(full_index_data)


df_grouped = df.groupby(
    ['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano']) \
    .agg({col: 'sum' for col in df_original.columns}).reset_index() \
    .sort_values(['Ano','Mes','Semana_do_Mes_Num'])

# Mesclar com o full_index_df para garantir que todas as semanas 1-5 apareçam, mesmo sem dados
# Usamos 'left' merge para manter todas as combinações de full_index_df
df_grouped = pd.merge(full_index_df, df_grouped,
                      on=['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano'],
                      how='left').fillna(0) # Preenche os valores de métricas com 0 onde não há dados


metricas = [c for c in df_grouped.columns if c not in ['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano']]

selecionadas = st.sidebar.multiselect("Status CS – DogHero", metricas, default=[metricas[0]] if metricas else [])

# — Gráfico —
st.header("Evolução das Métricas por Semana do Mês")

df_chart = df_grouped.copy()
df_chart['Full_Label'] = df_chart['Mes_Ano'] + ' S' + df_chart['Semana_do_Mes_Num'].astype(str)

if not df_chart.empty and selecionadas:
    fig = go.Figure()
    meses = sorted(df_chart['Mes_Ano'].unique(),
                   key=lambda x: (int(x.split(' ')[1]), pd.to_datetime(x.split(' ')[0], format='%b').month))
    cores = ['blue','red','green','purple','orange','brown','pink','grey','cyan','magenta']
    ci = 0
    ann = []

    for met in selecionadas:
        for ma in meses:
            tmp = df_chart[(df_chart['Mes_Ano']==ma) & (df_chart[met] > 0)] # Filtra apenas linhas com valor > 0 para o trace
            # Se você quiser mostrar as semanas vazias com 0 no gráfico, remova o `& (df_chart[met] > 0)`
            if not tmp.empty:
                cor = cores[ci % len(cores)]
                ci += 1
                fig.add_trace(go.Scatter(
                    x=tmp['Semana_do_Mes_Num'], y=tmp[met],
                    mode='lines+markers',
                    name=f"{ma} ({met})",
                    line=dict(color=cor, width=2),
                    customdata=tmp['Full_Label'],
                    hovertemplate="<b>%{customdata} (" + met + ")</b><br>Valor: %{y:,.0f}<extra></extra>"
                ))
                for _, row in tmp.iterrows():
                    # Adiciona anotações apenas se o valor for maior que 0
                    if row[met] > 0:
                        ann.append(dict(
                            x=row['Semana_do_Mes_Num'], y=row[met],
                            text=f"{row[met]:,.0f}", showarrow=False, yshift=10,
                            font=dict(color=cor, size=10)
                        ))

    fig.update_layout(
        title="Evolução das Métricas por Semana do Mês",
        xaxis=dict(title="Semana do Mês", tickmode='array',
                   tickvals=list(range(1, 6)), # Garante ticks de 1 a 5
                   ticktext=[f"Semana {i}" for i in range(1, 6)],
                   showgrid=True, gridcolor='lightgrey'),
        yaxis=dict(title="Contagem", tickformat=",.0f", showgrid=True, gridcolor='lightgrey'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", height=550, annotations=ann
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Nenhum dado ou métrica selecionada para gráfico.")

st.markdown("---")

# — Tabela comparativa —
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
                    if prev_lab != lab and prev_val and pd.notna(prev_val):
                        # Evita divisão por zero se prev_val for 0
                        pct = ( (r[met]-prev_val)/prev_val ) * 100 if prev_val != 0 else np.nan
                        rec[f"{met} vs. {prev_lab} (Val Abs)"] = r[met]-prev_val
                        rec[f"{met} vs. {prev_lab} (%)"] = f"{pct:,.2f}%" if pd.notna(pct) else "N/A"
            records.append(rec)
    df_tab = pd.DataFrame(records)
    st.dataframe(df_tab)
else:
    st.info("Selecione métricas para tabela comparativa.")

st.markdown("---")

# — Dados brutos —
st.header("Visualização de Dados Semanais Brutos por Período Selecionado")
st.sidebar.header("Ver Dados Semanais Detalhados")

data_inicio_vis = st.sidebar.date_input("Data de Início", min_value=min_date, max_value=max_date, value=min_date, key="vis_start")
data_fim_vis = st.sidebar.date_input("Data de Fim", min_value=min_date, max_value=max_date, value=max_date, key="vis_end")

if data_inicio_vis > data_fim_vis:
    st.sidebar.error("Data início > fim")
else:
    df_vis = df_original.loc[data_inicio_vis:data_fim_vis]
    if df_vis.empty:
        st.warning("Nenhum dado nessa faixa.")
    else:
        with st.expander("🔍 Ver Dados Semanais Filtrados"):
            st.dataframe(df_vis.reset_index().assign(Semana_do_Mes_Calculada=df_vis.index.to_series().apply(semana_do_mes)))
