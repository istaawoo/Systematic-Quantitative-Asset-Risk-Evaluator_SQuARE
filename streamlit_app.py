# app.py  — Streamlit prototype (yfinance)
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timezone

st.set_page_config(layout="wide", page_title="Stock Risk Explorer (MVP)")
#Test
st.title("Stock Risk Explorer — Prototype")
st.caption("Prototype uses yfinance (good for demos). Not a trading feed. See data timestamp below.")

# --- Input
col1, col2 = st.columns([3,1])
with col1:
    ticker = st.text_input("Enter ticker (e.g. AAPL)", value="AAPL").upper()
with col2:
    fetch = st.button("Fetch")

# caching wrapper to avoid repeated API calls
@st.cache_data(ttl=60)
def fetch_ticker_data(t):
    try:
        tk = yf.Ticker(t)
        info = tk.info
        # historical 1y daily
        hist = tk.history(period="1y", interval="1d", actions=False)
        # intraday 30 days 1m (yfinance may not return 1m for all)
        intraday = None
        try:
            intraday = tk.history(period="7d", interval="1m")
        except Exception:
            intraday = None
        return info, hist, intraday
    except Exception as e:
        return None, None, None

if fetch and ticker:
    with st.spinner("Fetching data..."):
        info, hist, intraday = fetch_ticker_data(ticker)
    if info is None or hist is None or len(hist)==0:
        st.error("No data found (ticker might be invalid or yfinance blocked).")
        st.stop()

    # Data snapshot
    last_price = hist['Close'].iloc[-1]
    updated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    st.write(f"**{ticker}** — Price: ${last_price:.2f}  •  Data snapshot: {updated}")

    # Basic metrics
    returns = hist['Close'].pct_change().dropna()
    annual_vol = returns.std() * np.sqrt(252)  # approx
    one_year_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100
    max_dd = (hist['Close'].cummax() - hist['Close']).max() / hist['Close'].cummax().max() * 100

    # Subscore mapping (simple percentile-ish buckets — tweak later)
    def map_vol_to_score(vol):
        # rough buckets, convert to 0-100 risk (higher = riskier)
        if vol < 0.15: return 20
        if vol < 0.25: return 40
        if vol < 0.40: return 65
        return 90

    def map_dd_to_score(dd):
        if dd < 10: return 20
        if dd < 25: return 45
        if dd < 45: return 70
        return 95

    vol_score = map_vol_to_score(annual_vol)
    dd_score = map_dd_to_score(max_dd)
    growth_score = 100 - min(max(one_year_return, -50), 200) / 2  # crude: big gains can be risky

    # rule-based ASI (0-100) where higher = riskier
    weights = {"vol":0.4, "drawdown":0.25, "growth":0.2, "liquidity":0.15}
    # liquidity proxy: use average daily volume
    avg_vol = hist['Volume'].mean()
    if avg_vol > 5_000_000: liquidity_score = 20
    elif avg_vol > 1_000_000: liquidity_score = 40
    elif avg_vol > 200_000: liquidity_score = 65
    else: liquidity_score = 90

    rule_asi = (vol_score*weights['vol'] +
                dd_score*weights['drawdown'] +
                growth_score*weights['growth'] +
                liquidity_score*weights['liquidity'])

    # UI: show subscores + sliders for "what-if"
    st.subheader("Score breakdown (higher = riskier)")
    cols = st.columns(4)
    cols[0].metric("Volatility (annual)", f"{annual_vol:.2%}", delta=None)
    cols[1].metric("1y Return", f"{one_year_return:.2f}%", delta=None)
    cols[2].metric("Max Drawdown", f"{max_dd:.2f}%", delta=None)
    cols[3].metric("Avg Daily Volume", f"{avg_vol:,.0f}", delta=None)

    st.write("---")
    st.write("**Interactive 'what-if' sliders** — change sub-scores (0-100) to see hypothetical ASI.")
    sv1 = st.slider("Volatility subscore (riskier=larger)", 0, 100, int(vol_score))
    sv2 = st.slider("Drawdown subscore", 0, 100, int(dd_score))
    sv3 = st.slider("Growth subscore (riskier=larger)", 0, 100, int(growth_score))
    sv4 = st.slider("Liquidity subscore (riskier=larger)", 0, 100, int(liquidity_score))

    user_blend = st.slider("Blend ML sentiment (0=rule-only,100=ML-only) — prototype uses 0", 0, 100, 0)
    # Sentiment placeholder: 0 for no ML in MVP
    sentiment_score = 0

    hypothetical_asi = (sv1*weights['vol'] + sv2*weights['drawdown'] +
                       sv3*weights['growth'] + sv4*weights['liquidity'])

    final_actual = rule_asi*(1-user_blend/100) + sentiment_score*(user_blend/100)
    final_hypothetical = hypothetical_asi*(1-user_blend/100) + sentiment_score*(user_blend/100)

    st.write("")
    st.metric("Actual ASI (rule-based)", f"{final_actual:.1f} / 100")
    st.metric("Hypothetical ASI (your sliders)", f"{final_hypothetical:.1f} / 100")

    # Chart
    st.subheader("Price chart (1y)")
    hist_reset = hist.reset_index()
    chart = alt.Chart(hist_reset).mark_line().encode(
        x='Date:T',
        y='Close:Q'
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    st.write("---")
    st.info("Notes: This prototype uses yfinance for convenience. yfinance data may be delayed and is not guaranteed real-time. For per-minute real-time updates, use a paid API with streaming.")