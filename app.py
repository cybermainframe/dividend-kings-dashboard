from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# Se publicares no Streamlit Cloud e quiseres que ele leia o CSV mais
# recente do GitHub, cola aqui o link "raw" do ficheiro CSV.
# Exemplo:
# CSV_URL = "https://raw.githubusercontent.com/TEU_UTILIZADOR/TEU_REPO/main/data/dividend_kings_latest.csv"
# Se deixares vazio, o dashboard lê o ficheiro local.
CSV_URL = ""

ROOT = Path(__file__).resolve().parent
LOCAL_CSV = ROOT / "data" / "dividend_kings_latest.csv"


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    """Carrega os dados mais recentes."""
    try:
        if CSV_URL:
            return pd.read_csv(CSV_URL, parse_dates=["date"])

        if LOCAL_CSV.exists():
            return pd.read_csv(LOCAL_CSV, parse_dates=["date"])

        return pd.DataFrame()

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()


def format_market_cap(value):
    """Formata o market cap de forma legível."""
    if pd.isna(value):
        return "N/D"

    try:
        value = float(value)
    except Exception:
        return "N/D"

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    return f"${value:,.0f}"


st.set_page_config(
    page_title="Dividend Kings Dashboard",
    page_icon="👑",
    layout="wide",
)

st.title("👑 Dashboard Dividend Kings")
st.caption("Ações com longo histórico de aumento de dividendos, ordenadas pela distância face à mínima de 52 semanas.")

df = load_data()

if df.empty:
    st.warning("Ainda não existem dados.")
    st.info("Corre primeiro o script de atualização:")
    st.code("python update_data.py", language="bash")
    st.stop()


latest_date = df["date"].max()
data = df[df["date"] == latest_date].copy()

st.caption(f"Última atualização dos dados: {latest_date:%Y-%m-%d}")


with st.sidebar:
    st.header("Filtros")

    max_distance = st.slider(
        label="Mostrar ações até esta distância da mínima (%)",
        min_value=0,
        max_value=100,
        value=20,
        step=1,
    )

    highlight_threshold = st.slider(
        label="Considerar 'muito perto da mínima' até (%)",
        min_value=0,
        max_value=30,
        value=10,
        step=1,
    )

    min_yield = st.number_input(
        label="Dividend yield mínimo (%)",
        min_value=0.0,
        max_value=15.0,
        value=0.0,
        step=0.1,
    )

    search = st.text_input(
        label="Pesquisar ticker ou nome",
        placeholder="Ex.: PEP, Walmart",
    )

    if "sector" in data.columns:
        sectors = sorted(
            data["sector"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_sectors = st.multiselect(
            label="Setores",
            options=sectors,
            default=sectors,
        )

        if selected_sectors:
            data = data[data["sector"].isin(selected_sectors)]


data = data[data["pct_from_low"].fillna(999) <= max_distance]

if "dividend_yield_pct" in data.columns:
    data = data[data["dividend_yield_pct"].fillna(0) >= min_yield]

if search:
    search_upper = search.upper()

    mask_ticker = data["ticker"].str.upper().str.contains(search_upper, na=False)
    mask_name = data["name"].str.upper().str.contains(search_upper, na=False)

    data = data[mask_ticker | mask_name]


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Empresas monitorizadas",
        value=len(data),
    )

with col2:
    near_low = data[data["pct_from_low"].fillna(999) <= highlight_threshold]

    st.metric(
        label=f"Muito perto da mínima ≤ {highlight_threshold}%",
        value=len(near_low),
    )

with col3:
    if "dividend_yield_pct" in data.columns and data["dividend_yield_pct"].notna().any():
        avg_yield = data["dividend_yield_pct"].mean()

        st.metric(
            label="Yield médio",
            value=f"{avg_yield:.2f}%",
        )
    else:
        st.metric(
            label="Yield médio",
            value="N/D",
        )

with col4:
    if not data.empty and data["pct_from_low"].notna().any():
        closest = data.loc[data["pct_from_low"].idxmin()]

        st.metric(
            label="Mais perto da mínima",
            value=f"{closest['ticker']}",
            delta=f"{closest['pct_from_low']:.2f}% acima",
            delta_color="inverse",
        )
    else:
        st.metric(
            label="Mais perto da mínima",
            value="N/D",
        )


st.markdown("---")


st.subheader("Distância face à mínima de 52 semanas")

chart_df = data.sort_values("pct_from_low").head(30)

if chart_df.empty:
    st.info("Nenhuma ação corresponde aos filtros atuais.")
else:
    chart_df["label"] = chart_df["ticker"] + " | " + chart_df["name"].astype(str)

    fig = px.bar(
        chart_df,
        x="pct_from_low",
        y="label",
        orientation="h",
        color="pct_from_low",
        color_continuous_scale="RdYlGn_r",
        labels={
            "pct_from_low": "% acima da mínima",
            "label": "",
        },
        hover_data={
            "ticker": True,
            "name": True,
            "price": True,
            "low_52w": True,
            "high_52w": True,
            "dividend_yield_pct": True,
            "sector": True,
            "label": False,
        },
    )

    fig.update_layout(
        height=650,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


st.markdown("---")


st.subheader("Tabela detalhada")

if data.empty:
    st.info("Nenhuma ação corresponde aos filtros atuais.")
else:
    table = data.copy()

    if "market_cap" in table.columns:
        table["market_cap_formatted"] = table["market_cap"].apply(format_market_cap)
    else:
        table["market_cap_formatted"] = "N/D"

    show_columns = [
        "ticker",
        "name",
        "sector",
        "price",
        "low_52w",
        "high_52w",
        "pct_from_low",
        "pct_from_high",
        "dividend_yield_pct",
        "trailing_pe",
        "market_cap_formatted",
    ]

    available_columns = [col for col in show_columns if col in table.columns]

    table = table[available_columns].sort_values("pct_from_low")

    table = table.rename(
        columns={
            "ticker": "Ticker",
            "name": "Empresa",
            "sector": "Setor",
            "price": "Preço",
            "low_52w": "Mínima 52S",
            "high_52w": "Máxima 52S",
            "pct_from_low": "% acima da mínima",
            "pct_from_high": "% face à máxima",
            "dividend_yield_pct": "Yield %",
            "trailing_pe": "P/E",
            "market_cap_formatted": "Market Cap",
        }
    )

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
    )

    csv = table.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descarregar CSV",
        data=csv,
        file_name="dividend_kings_dashboard.csv",
        mime="text/csv",
    )


st.markdown("---")

st.caption(
    "Este dashboard é apenas informativo e não constitui recomendação de investimento."
)