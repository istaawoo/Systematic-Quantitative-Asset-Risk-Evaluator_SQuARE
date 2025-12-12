"""
stock_classifier.py - Classifies stock style and market cap tier using yfinance data.
"""
import yfinance as yf


def classify_stock(ticker):
    """
    Fetch stock fundamentals and classify style + market cap tier.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        dict: {
            'ticker': str,
            'short_name': str,
            'style': str (Growth, Value, Dividend, Blend),
            'sector': str,
            'market_cap_tier': str (Mega-cap, Large-cap, Mid-cap, Small-cap, Micro-cap),
            'pe_ratio': float or None,
            'dividend_yield': float or None,
            'revenue_growth': float or None,
            'earnings_growth': float or None,
            'market_cap': float or None,
            'error': str or None
        }
    """
    try:
        # Fetch ticker info - let yfinance handle the session internally
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        short_name = info.get("shortName", ticker)
        sector = info.get("sector", "Unknown")
        market_cap = info.get("marketCap")
        pe_ratio = info.get("trailingPE")
        dividend_yield = info.get("dividendYield")  # May be decimal or percentage
        revenue_growth = info.get("revenueGrowth")  # Already a decimal
        earnings_growth = info.get("earningsGrowth")  # Already a decimal
        
        # Normalize dividend_yield: if > 1, assume it's a percentage (e.g., 37 not 0.37)
        if dividend_yield and dividend_yield > 1:
            dividend_yield = dividend_yield / 100
        
        # Normalize growth rates: if > 10, assume it's a percentage
        if revenue_growth and revenue_growth > 10:
            revenue_growth = revenue_growth / 100
        if earnings_growth and earnings_growth > 10:
            earnings_growth = earnings_growth / 100
        
        # Classify market cap tier
        market_cap_tier = "Unknown"
        if market_cap:
            if market_cap >= 2_000_000_000_000:  # $2T+
                market_cap_tier = "Mega-cap"
            elif market_cap >= 300_000_000_000:  # $300B+
                market_cap_tier = "Large-cap"
            elif market_cap >= 50_000_000_000:  # $50B+
                market_cap_tier = "Mid-cap"
            elif market_cap >= 5_000_000_000:  # $5B+
                market_cap_tier = "Small-cap"
            else:
                market_cap_tier = "Micro-cap"
        
        # Classify stock style (Growth, Value, Dividend, Blend)
        # Heuristics: P/E ratio, dividend yield, earnings growth
        style = "Blend"
        if pe_ratio and dividend_yield is not None and earnings_growth:
            if dividend_yield > 0.03 and pe_ratio < 20:
                style = "Dividend"
            elif dividend_yield > 0.025:
                style = "Dividend"
            elif earnings_growth > 0.15 and pe_ratio and pe_ratio > 20:
                style = "Growth"
            elif pe_ratio < 15 and dividend_yield is not None and dividend_yield < 0.02:
                style = "Value"
        
        return {
            "ticker": ticker.upper(),
            "short_name": short_name,
            "style": style,
            "sector": sector,
            "market_cap_tier": market_cap_tier,
            "pe_ratio": pe_ratio,
            "dividend_yield": dividend_yield,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "market_cap": market_cap,
            "error": None
        }
    
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "short_name": None,
            "style": None,
            "sector": None,
            "market_cap_tier": None,
            "pe_ratio": None,
            "dividend_yield": None,
            "revenue_growth": None,
            "earnings_growth": None,
            "market_cap": None,
            "error": str(e)
        }
