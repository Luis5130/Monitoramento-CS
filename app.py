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

# — Função ajustada: semana do mês usando isocalendar e mapeamento para 5 semanas —
def semana_do_mes(dt):
    # Dia da semana do primeiro dia do mês (Monday is 0 and Sunday is 6)
    primeiro_dia_mes = dt.replace(day=1)
    # A semana ISO começa na segunda-feira.
    # Obtenha a semana ISO do ano para a data e para o primeiro dia do mês
    semana_ano_dt = dt.isocalendar()[1]
    semana_ano_primeiro_dia_mes = primeiro_dia_mes.isocalendar()[1]

    # Calcula a semana do mês
    # Se a semana do ano do dia é a mesma ou posterior à do primeiro dia do mês
    if semana_ano_dt >= semana_ano_primeiro_dia_mes:
        semana_mes = semana_ano_dt - semana_ano_primeiro_dia_mes + 1
    else:
        # Se o primeiro dia do mês está em uma semana de ano "anterior" (ex: mês novo começa na semana 53 do ano anterior)
        # Calcula as semanas restantes do ano anterior e adiciona as semanas do ano atual
        # Isso é mais complexo e pode ser simplificado assumindo que isocalendar lida com a virada do ano para semanas.
        # Uma abordagem mais simples para essa situação específica é considerar a semana 1 do mês.
        semana_mes = semana_ano_dt + (dt.replace(month=12, day=31).isocalendar()[1] - semana_ano_primeiro_dia_mes) + 1


    # Garante que o máximo seja a Semana 5.
    # Se um mês tem, por exemplo, 6 datas de início de semana distintas e a 6ª tem dados,
    # esses dados serão somados à 5ª semana.
    return min(semana_mes, 5)


df = df_filtrado.copy()
df['Ano'] = df.index.year
df['Mes'] = df.index.month
df['Semana_do_Mes_Num'] = df.index.to_series().apply(semana_do_mes)
df['Label_Mes'] = df.index.strftime('%b')
df['Mes_Ano'] = df['Label_Mes'] + ' ' + df['Ano'].astype(str)

df_grouped = df.groupby(
    ['Ano','Mes','Semana_do_Mes_Num','Label_Mes','Mes_Ano']) \
    .agg({col: 'sum' for col in df_original.columns}).reset_index() \
    .sort_values(['Ano','Mes','Semana_do_Mes_Num'])

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
            tmp = df_chart[df_chart['Mes_Ano']==ma]
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
                    ann.append(dict(
                        x=row['Semana_do_Mes_Num'], y=row[met],
                        text=f"{row[met]:,.0f}", showarrow=False, yshift=10,
                        font=dict(color=cor, size=10)
                    ))

    fig.update_layout(
        title="Evolução das Métricas por Semana do Mês",
        xaxis=dict(title="Semana do Mês", tickmode='array',
                   tickvals=list(range(1, df_chart['Semana_do_Mes_Num'].max()+1)),
                   ticktext=[f"Semana {i}" for i in range(1, df_chart['Semana_do_Mes_Num'].max()+1)],
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
                        change = r[met]-prev_val
                        pct = (change/prev_val)*100
                        rec[f"{met} vs. {prev_lab} (Val Abs)"] = change
                        rec[f"{met} vs. {prev_lab} (%)"] = f"{pct:,.2f}%"
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
            st.dataframe(df_vis.reset_index())
