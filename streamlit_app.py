# app.py - Stock Risk Explorer (final-feel prototype)
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timezone
from stock_classifier import classify_stock
from stock_profile_matcher import match_stock_to_connor, load_connor_profile

st.set_page_config(layout="wide", page_title="Stock Risk Explorer")
st.title("Stock Risk Explorer")
st.caption("(Data via yfinance)")
st.markdown("**Square Stock Analyzer**: Systematic Quantitative Asset Risk Evaluator (SQuARE)")

# Define weights at module level so they're accessible throughout
weights = {"vol": 0.4, "drawdown": 0.25, "growth": 0.2, "liquidity": 0.15}

# Metric definitions for tooltips
metric_definitions = {
    "Current Price": "The most recent closing price of the stock.",
    "Market Cap": "Total market value of company's outstanding shares. Calculated as share price multiplied by number of shares.",
    "P/E Ratio": "Price-to-Earnings ratio. Stock price divided by earnings per share. Lower ratios may indicate undervaluation, higher ratios may indicate growth expectations.",
    "Dividend Yield": "Annual dividend payment as a percentage of stock price. Represents income return to shareholders.",
    "Earnings Growth": "Year-over-year percentage change in earnings per share. Indicates company profitability trend.",
    "Revenue Growth": "Year-over-year percentage change in total revenue. Indicates company sales growth.",
    "1-Year Return": "Stock price change over the past year expressed as a percentage.",
    "Annualized Volatility": "Standard deviation of daily returns annualized. Higher values indicate more price fluctuation and risk."
}

# CSS: tooltip delay and company card styling
st.markdown(
    """
    <style>
    .tooltip{position:relative; display:inline-block}
    .tooltip .tooltiptext{
        visibility:hidden;
        width:280px;
        background:#fff;
        color:#111;
        text-align:left;
        border:1px solid #e0e0e0;
        padding:8px;
        border-radius:8px;
        position:absolute;
        z-index:100;
        bottom:125%;
        left:50%;
        transform:translateX(-50%);
        opacity:0;
        transition:opacity 0.15s ease;
        transition-delay:0.55s; /* delay before showing tooltip */
        box-shadow:0 6px 18px rgba(0,0,0,0.08);
    }
    .tooltip:hover .tooltiptext{visibility:visible; opacity:1}
    /* company card: dark mode readable */
    .company-card{border:1px solid rgba(255,255,255,0.06);padding:12px;border-radius:10px;background:#0b1220;color:#f8fafc}
    .company-card h4{margin:0 0 6px 0;color:#ffffff}
    .company-card div{color:#e6eef8}
    .company-logo{width:64px;height:64px;border-radius:8px;margin-right:10px}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Helper: fetch data (cache)
@st.cache_data(ttl=60)
def fetch_ticker_data(t):
    try:
        tk = yf.Ticker(t)
        info = tk.info
        # fetch longer history so users can zoom out beyond one year
        hist = tk.history(period="5y", interval="1d", actions=False)
        intraday = None
        try:
            intraday = tk.history(period="7d", interval="1m")
        except Exception:
            intraday = None
        return info, hist, intraday
    except Exception:
        return None, None, None

# --- Input form: allows Enter to submit
with st.form(key="ticker_form", clear_on_submit=False):
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input("Enter ticker (e.g. AAPL)", value=st.session_state.get("ticker", "AAPL")).upper()
    with col2:
        submitted = st.form_submit_button("Fetch")

# If user submitted, fetch and store results (only on submit)
if submitted and ticker_input:
    info, hist, intraday = fetch_ticker_data(ticker_input)
    if info is None or hist is None or len(hist) == 0:
        st.error("No data found (ticker may be invalid or yfinance is blocked).")
    else:
        # store in session state so subsequent slider changes don't re-fetch
        st.session_state["ticker"] = ticker_input
        st.session_state["info"] = info
        st.session_state["hist"] = hist
        st.session_state["intraday"] = intraday
        # compute base metrics and subscores and store
        # compute metrics over the last 1 year slice but keep full history for chart/zoom
        end = hist.index[-1]
        one_year_ago = end - pd.Timedelta(days=365)
        hist_1y = hist.loc[hist.index >= one_year_ago]
        if len(hist_1y) < 50:
            hist_1y = hist.tail(252)
        returns = hist_1y["Close"].pct_change().dropna()
        annual_vol = float(returns.std() * np.sqrt(252))
        # find nearest price ~1 year ago on the full history
        idx = hist.index.get_indexer([one_year_ago], method="nearest")[0]
        one_year_price = hist["Close"].iloc[idx]
        one_year_return = float((hist["Close"].iloc[-1] / one_year_price - 1) * 100)
        max_dd = float((hist_1y["Close"].cummax() - hist_1y["Close"]).max() / hist_1y["Close"].cummax().max() * 100)
        avg_vol = float(hist["Volume"].mean())

        # mapping functions (can be refined later)
        def map_vol_to_score(vol):
            if vol < 0.15:
                return 20
            if vol < 0.25:
                return 40
            if vol < 0.40:
                return 65
            return 90

        def map_dd_to_score(dd):
            if dd < 10:
                return 20
            if dd < 25:
                return 45
            if dd < 45:
                return 70
            return 95

        vol_score = map_vol_to_score(annual_vol)
        dd_score = map_dd_to_score(max_dd)
        # growth: moderate growth lowers risk; extreme negative or positive can raise risk
        growth_score = 50 + (min(max(one_year_return, -50), 200) / 4)  # simple mapping
        # liquidity proxy
        if avg_vol > 5_000_000:
            liquidity_score = 20
        elif avg_vol > 1_000_000:
            liquidity_score = 40
        elif avg_vol > 200_000:
            liquidity_score = 65
        else:
            liquidity_score = 90

        rule_asi = (
            vol_score * weights["vol"]
            + dd_score * weights["drawdown"]
            + growth_score * weights["growth"]
            + liquidity_score * weights["liquidity"]
        )

        # store computed values
        st.session_state["annual_vol"] = annual_vol
        st.session_state["one_year_return"] = one_year_return
        st.session_state["max_dd"] = max_dd
        st.session_state["avg_vol"] = avg_vol
        st.session_state["vol_score"] = vol_score
        st.session_state["dd_score"] = dd_score
        st.session_state["growth_score"] = growth_score
        st.session_state["liquidity_score"] = liquidity_score
        st.session_state["rule_asi"] = rule_asi

# If session state has data, display the UI
if "hist" in st.session_state:
    ticker = st.session_state["ticker"]
    info = st.session_state["info"]
    hist = st.session_state["hist"]
    intraday = st.session_state.get("intraday", None)

    last_price = hist["Close"].iloc[-1]
    updated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    # Header
    colA, colB = st.columns([3, 1])
    with colA:
        st.markdown(f"## {ticker}: ${last_price:.2f}")
        st.caption(f"Data timestamp: {updated}")
        # short ASI definition
        st.caption("ASI = Asset Stability Index (0-100). Higher = more risky. Computed from volatility, drawdown, liquidity, and growth.")
    with colB:
        # optional company short info if available - render as a distinct card
        short_name = info.get("shortName", "")
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        country = info.get("country", "")
        market_cap = info.get("marketCap", None)

        def format_market_cap(mc):
            try:
                mc = float(mc)
            except Exception:
                return str(mc)
            if mc >= 1e12:
                return f"${mc/1e12:.2f}T"
            if mc >= 1e9:
                return f"${mc/1e9:.2f}B"
            if mc >= 1e6:
                return f"${mc/1e6:.2f}M"
            return f"${mc:,.0f}"

        # logo (if available) and info in a horizontal layout
        logo_url = info.get("logo_url") or info.get("logo")
        company_html = '<div class="company-card">'
        company_html += '<div style="display:flex;align-items:center">'
        if logo_url:
            company_html += f'<img src="{logo_url}" class="company-logo" alt="logo"/>'
        company_html += '<div>'
        if short_name:
            company_html += f"<h4>{short_name}</h4>"
        if sector:
            company_html += f"<div><strong>Sector:</strong> {sector}</div>"
        if industry and industry != sector:
            company_html += f"<div><strong>Industry:</strong> {industry}</div>"
        if country:
            company_html += f"<div><strong>Country:</strong> {country}</div>"
        if market_cap:
            company_html += f"<div><strong>Market Cap:</strong> {format_market_cap(market_cap)}</div>"
        company_html += '</div></div>'
        st.markdown(company_html, unsafe_allow_html=True)

    # Helper function to create tooltip with circle-i icon (CSS-based with delay)
    def tooltip_icon(explanation):
        esc = explanation.replace('"', '&quot;')
        return f'<span class="tooltip">ⓘ<span class="tooltiptext">{esc}</span></span>'
    
    # Basic metrics with inline tooltips
    st.subheader("Key metrics")
    cols = st.columns(4)
    
    

    with cols[0]:
        cols[0].markdown(
            f"**Volatility {tooltip_icon('Volatility is the typical size of daily price moves, annualized. Higher volatility = larger price swings and higher short-term risk. Lower volatility = more stable prices.')}**",
            unsafe_allow_html=True
        )
        cols[0].metric("", f"{st.session_state['annual_vol']:.2%}")
    
    with cols[1]:
        cols[1].markdown(
            f"**1-Year Return {tooltip_icon('Percentage change from the close 1 year ago to today. Positive returns may indicate growth, but extreme returns can signal heightened volatility or market concentration risk.')}**",
            unsafe_allow_html=True
        )
        cols[1].metric("", f"{st.session_state['one_year_return']:.2f}%")
    
    with cols[2]:
        cols[2].markdown(
            f"**Max Drawdown {tooltip_icon('The largest peak-to-trough decline during the past year. Measures tail risk - the worst historical loss if you bought at the peak. Higher drawdowns indicate greater downside exposure.')}**",
            unsafe_allow_html=True
        )
        cols[2].metric("", f"{st.session_state['max_dd']:.2f}%")
    
    with cols[3]:
        cols[3].markdown(
            f"**Avg Daily Volume {tooltip_icon('Average shares traded per day. Higher volume = better liquidity (easier to buy/sell). Low liquidity can make it difficult to exit positions during market stress.')}**",
            unsafe_allow_html=True
        )
        cols[3].metric("", f"{st.session_state['avg_vol']:,.0f}")

    st.write("---")
    st.subheader("Score breakdown (higher = more risky)")

    # sliders use session_state values as defaults so they won't reset
    sv1 = st.slider(
        "Volatility subscore (riskier = larger)",
        0,
        100,
        int(st.session_state["vol_score"]),
        key="sv1",
    )
    sv2 = st.slider(
        "Drawdown subscore (riskier = larger)",
        0,
        100,
        int(st.session_state["dd_score"]),
        key="sv2",
    )
    sv3 = st.slider(
        "Growth subscore (riskier = larger)",
        0,
        100,
        int(st.session_state["growth_score"]),
        key="sv3",
    )
    sv4 = st.slider(
        "Liquidity subscore (riskier = larger)",
        0,
        100,
        int(st.session_state["liquidity_score"]),
        key="sv4",
    )

    # Hypothetical and actual on same line
    col_actual, col_hyp = st.columns(2)
    hypothetical_asi = (sv1 * weights["vol"] + sv2 * weights["drawdown"] + sv3 * weights["growth"] + sv4 * weights["liquidity"])
    actual_asi = st.session_state["rule_asi"]

    with col_actual:
        st.metric("Actual ASI (rule-based)", f"{actual_asi:.1f} / 100")
    with col_hyp:
        st.metric("Hypothetical ASI (your sliders)", f"{hypothetical_asi:.1f} / 100")

    # --- Profile Matching Section ---
    st.write("---")
    st.subheader("✨ Fit with Connor Barwin's Profile")
    
    # Classify stock and compute fit
    classified = classify_stock(ticker)
    connor_profile = load_connor_profile()
    fit_result = match_stock_to_connor(classified, connor_profile)
    
    if fit_result.get("error"):
        st.warning(f"Unable to compute profile fit: {fit_result['error']}")
    else:
        # Display overall fit score and label
        col_fit1, col_fit2 = st.columns([2, 3])
        with col_fit1:
            fit_score = fit_result.get("fit_score", 0)
            fit_label = fit_result.get("fit_label", "Unknown")
            fit_emoji = fit_result.get("fit_emoji", "❓")
            st.markdown(f"### {fit_emoji} {fit_label}")
            st.metric("Overall Fit Score", f"{fit_score:.2f} / 1.00")
        
        with col_fit2:
            # Display three alignment subscores
            st.markdown("**Alignment Breakdown:**")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                style_align = fit_result.get("style_alignment", 0)
                st.metric("Style", f"{style_align:.2f}")
            with col_s2:
                sector_align = fit_result.get("sector_alignment", 0)
                st.metric("Sector", f"{sector_align:.2f}")
            with col_s3:
                trait_align = fit_result.get("trait_alignment", 0)
                st.metric("Traits", f"{trait_align:.2f}")
        
        # Display reasoning
        reasoning = fit_result.get("reasoning", "")
        st.markdown(f"**Reasoning:**\n\n{reasoning}")
        
        # Display recommendation connecting ASI + fit
        st.markdown("---")
        recommendation = f"Based on {ticker}'s quantitative risk (ASI: {actual_asi:.1f}/100) and qualitative fit ({fit_label}), "
        if actual_asi > 70 and fit_score < 0.50:
            recommendation += f"this stock presents **high quantitative risk AND poor alignment** with Connor's profile. Proceed with caution."
        elif actual_asi > 70 and fit_score >= 0.50:
            recommendation += f"this stock has **high quantitative risk** but **good profile fit**. Consider if the alignment justifies the volatility."
        elif actual_asi <= 70 and fit_score >= 0.65:
            recommendation += f"this stock offers a **strong match**—reasonable risk profile with excellent profile alignment."
        elif actual_asi <= 70 and fit_score < 0.50:
            recommendation += f"this stock has **moderate quantitative risk** but **limited profile fit**. Diversify accordingly."
        else:
            recommendation += f"this stock warrants further evaluation against your broader portfolio strategy."
        
        st.info(recommendation)

    # --- Financial Metrics Section ---
    st.write("---")
    st.subheader("📊 Financial Metrics")
    
    # Get additional fundamentals from classified stock data
    metrics_display = {}
    
    # Current price metrics
    current_price = hist.iloc[-1]["Close"]
    metrics_display["Current Price"] = f"${current_price:.2f}"
    
    # Market cap
    if classified.get("market_cap"):
        market_cap = classified["market_cap"]
        if market_cap >= 1_000_000_000_000:
            metrics_display["Market Cap"] = f"${market_cap/1_000_000_000_000:.2f}T"
        elif market_cap >= 1_000_000_000:
            metrics_display["Market Cap"] = f"${market_cap/1_000_000_000:.2f}B"
        else:
            metrics_display["Market Cap"] = f"${market_cap/1_000_000:.2f}M"
    
    # Valuation metrics
    if classified.get("pe_ratio"):
        pe = classified["pe_ratio"]
        metrics_display["P/E Ratio"] = f"{pe:.2f}x" if pe else "N/A"
    
    if classified.get("dividend_yield") is not None:
        div_yield = classified["dividend_yield"]
        metrics_display["Dividend Yield"] = f"{div_yield*100:.2f}%" if div_yield else "0.00%"
    
    # Growth metrics
    if classified.get("earnings_growth"):
        earnings_growth = classified["earnings_growth"]
        metrics_display["Earnings Growth"] = f"{earnings_growth*100:.2f}%" if earnings_growth else "N/A"
    
    if classified.get("revenue_growth"):
        revenue_growth = classified["revenue_growth"]
        metrics_display["Revenue Growth"] = f"{revenue_growth*100:.2f}%" if revenue_growth else "N/A"
    
    # Price performance
    one_year_ago_price = hist.iloc[0]["Close"] if len(hist) > 0 else current_price
    one_year_return = ((current_price - one_year_ago_price) / one_year_ago_price) * 100
    metrics_display["1-Year Return"] = f"{one_year_return:.2f}%"
    
    # Volatility (annualized)
    daily_returns = hist["Close"].pct_change().dropna()
    annualized_vol = daily_returns.std() * np.sqrt(252)
    metrics_display["Annualized Volatility"] = f"{annualized_vol*100:.2f}%"
    
    # Display metrics in a grid with tooltip icons
    cols = st.columns(3)
    for idx, (key, value) in enumerate(metrics_display.items()):
        with cols[idx % 3]:
            tooltip_text = metric_definitions.get(key, "")
            if tooltip_text:
                metric_label = f'{key} <span class="tooltip">ⓘ<span class="tooltiptext">{tooltip_text}</span></span>'
                st.markdown(f'<div>{metric_label}</div>', unsafe_allow_html=True)
                st.metric("", value)
            else:
                st.metric(key, value)

    st.write("---")
    
    # Legal Disclaimer
    st.info(
        "⚠️ **Disclaimer**: Data is provided by yfinance and may be delayed. Stock prices and financial metrics are not real-time "
        "and typically lag by 15-20 minutes. This tool is for informational purposes only and should not be considered financial advice. "
        "Always verify critical data through official sources before making investment decisions. Past performance does not guarantee future results. "
        "Consult a licensed financial advisor before making investment decisions."
    )
    
    with st.expander("Technical Methodology & Details"):
        st.markdown("""
        **Asset Stability Index (ASI) Calculation**
        - The ASI is a composite risk score (0-100, higher = more risky) based on four key metrics: Volatility, Max Drawdown, Growth, and Liquidity.
        - **Weights:**
            - Volatility: 40%
            - Max Drawdown: 25%
            - Growth: 20%
            - Liquidity: 15%
        - **Volatility** is annualized standard deviation of daily returns (1 year for 1y chart, 5 years for 5y chart).
        - **Max Drawdown** is the largest peak-to-trough loss over the same period.
        - **Growth** is the 1-year or 5-year return, mapped to a risk score (extreme positive/negative returns increase risk).
        - **Liquidity** is average daily volume (higher volume = lower risk).
        - Each metric is mapped to a subscore (0-100) using rule-based bins, then combined using the above weights.
        - The ASI is not a prediction, but a standardized risk summary for comparison.
        
        **Why These Weights?**
        - Volatility and drawdown are the most direct measures of risk for liquid assets, so they are weighted highest.
        - Growth is included to penalize assets with extreme returns (which may be unstable or speculative).
        - Liquidity is included to penalize assets that may be hard to exit in a crisis.
        - Weights are chosen to balance short-term risk (volatility), tail risk (drawdown), and market structure (growth/liquidity).
        
        **Methodology Notes**
        - All calculations use adjusted close prices.
        - Volatility is annualized using sqrt(252) for daily data, sqrt(52) for weekly data.
        - Drawdown is calculated as the largest percent drop from a prior peak.
        - Growth is mapped to risk using a simple linear binning: moderate growth lowers risk, extreme growth or loss increases risk.
        - Liquidity bins are chosen based on typical US equity volume distributions.
        - The methodology is documented for reproducibility and transparency.
        """)