# Behavioral Profile Integration: Connor Barwin Fit Analysis

## Overview

The Stock Risk Explorer now integrates **behavioral profile matching** to provide qualitative assessment alongside the quantitative ASI (Asset Stability Index) score. This allows users to see not just how risky a stock is, but also how well it aligns with Connor Barwin's investment psychology and strategy.

## New Modules

### 1. `stock_classifier.py`
Fetches stock fundamentals from yfinance and classifies them into meaningful categories.

**Function: `classify_stock(ticker: str) -> dict`**

Returns:
```python
{
    'ticker': str,                      # e.g., "AAPL"
    'short_name': str,                  # e.g., "Apple Inc."
    'style': str,                       # "Growth", "Value", "Dividend", or "Blend"
    'sector': str,                      # e.g., "Technology"
    'market_cap_tier': str,             # "Mega-cap", "Large-cap", "Mid-cap", "Small-cap", "Micro-cap"
    'pe_ratio': float or None,          # P/E ratio
    'dividend_yield': float or None,    # Dividend yield as decimal (e.g., 0.03 for 3%)
    'revenue_growth': float or None,    # Revenue growth as decimal
    'earnings_growth': float or None,   # Earnings growth as decimal
    'market_cap': float or None,        # Market cap in USD
    'error': str or None                # Error message if fetch failed
}
```

**Stock Style Classification:**
- **Growth**: High earnings growth (>15%), higher P/E ratio (>20)
- **Value**: Lower P/E ratio (<15), low dividend yield
- **Dividend**: High dividend yield (>2.5-3%), reasonable P/E
- **Blend**: Mixed characteristics

**Market Cap Tiers:**
- **Mega-cap**: $2T+
- **Large-cap**: $300B–$2T
- **Mid-cap**: $50B–$300B
- **Small-cap**: $5B–$50B
- **Micro-cap**: <$5B

### 2. `stock_profile_matcher.py`
Loads Connor's behavioral profile and computes alignment scores.

**Function: `load_connor_profile(json_path: str) -> dict`**
Loads `behavioral_profile.json` containing Connor's investment philosophy.

**Function: `match_stock_to_connor(classified_stock: dict, connor_profile: dict = None) -> dict`**

Computes three alignment scores (0–1 scale):

1. **STYLE_ALIGNMENT (50% weight)**
   - Growth stocks score ~0.95 (excellent fit for Aggressive profile)
   - Value stocks score ~0.40 (poor fit)
   - Dividend stocks score ~0.35 (misaligned with growth focus)
   - Blend stocks score ~0.70 (moderate fit)
   - Formula incorporates Connor's growth focus score (0.67)

2. **SECTOR_ALIGNMENT (30% weight)**
   - Perfect match for Connor's preferred sectors (Sports & Entertainment, Real Estate, Impact Bonds): 0.95
   - Partial keyword match: 0.75
   - Neutral sectors (Tech, Healthcare, Financials): 0.50
   - Non-preferred sectors: 0.30

3. **TRAIT_ALIGNMENT (20% weight)**
   - Long-term oriented: Prefer Mega/Large-cap stable companies (+0.15)
   - Diligent/analytical: Prefer strong fundamentals and reasonable P/E (+0.10)
   - Mid-cap: +0.10; Small/Micro-cap: -0.10
   - Earnings growth >10%: +0.10; Negative growth: -0.10

**Overall Fit Score:**
```
OVERALL_FIT = (0.5 × STYLE) + (0.3 × SECTOR) + (0.2 × TRAIT)
```

**Fit Labels:**
- **0.80+**: "Excellent Fit" 🎯
- **0.65–0.79**: "Good Fit" ✅
- **0.50–0.64**: "Decent Fit" ⚠️
- **<0.50**: "Poor Fit" ❌

Returns:
```python
{
    'ticker': str,
    'fit_score': float (0-1),
    'fit_label': str,
    'fit_emoji': str,
    'style_alignment': float,
    'sector_alignment': float,
    'trait_alignment': float,
    'stock_style': str,
    'stock_sector': str,
    'connor_risk_tolerance': str,
    'reasoning': str,                   # Human-readable explanation
    'error': str or None
}
```

## Integration in Main App

After the user fetches a stock and the ASI is computed, the app now displays a new section:

### "✨ Fit with Connor Barwin's Profile"

**Components:**
1. **Overall Fit Score** with emoji indicator and label
2. **Alignment Breakdown** showing three subscores (Style, Sector, Trait)
3. **Reasoning Paragraph** explaining why the stock does/doesn't fit
4. **Recommendation** connecting quantitative risk (ASI) + qualitative fit:
   - High ASI + Poor fit = "risky AND misaligned—proceed with caution"
   - High ASI + Good fit = "high risk but good alignment—consider fit"
   - Low ASI + Good fit = "strong match—reasonable risk + good alignment"
   - Low ASI + Poor fit = "moderate risk but limited fit—diversify accordingly"

## Connor Barwin's Profile

**File:** `behavioral_profile.json`

```json
{
  "investor_name": "Connor Barwin",
  "risk_tolerance": "Aggressive",
  "traits": [
    "Long-Term Oriented",
    "Hands-On/Operational",
    "Socially Conscious",
    "Diligent/Analytical"
  ],
  "sector_preferences": [
    "Sports & Entertainment",
    "Urban Real Estate/Development",
    "Social Impact Bonds"
  ],
  "growth_focus_score": 0.67,
  "momentum_bias": 0.60,
  "investment_horizon_years": 10,
  "market_cap_preference": "Mid to Large Cap",
  "liquidity_preference": "Lower (prefers illiquid, long-term holds)"
}
```

## Example Output

### AAPL (Apple Inc.)

```
Stock Classification:
- Style: Growth
- Sector: Technology
- Market Cap Tier: Mega-cap
- P/E Ratio: 30.5
- Earnings Growth: 12%

Alignment Scores:
- Style Alignment: 0.95 (Growth fits Connor's aggressive profile)
- Sector Alignment: 0.50 (Technology is neutral, not in preferred sectors)
- Trait Alignment: 0.78 (Mega-cap, strong fundamentals)
- OVERALL FIT: 0.78 ✅ Good Fit

Reasoning:
AAPL is a Growth stock in Technology. Its Growth style aligns excellently with Connor's Aggressive 
risk tolerance and high growth focus (67%). However, Technology is outside Connor's stated sector 
preferences (Sports & Entertainment, Real Estate, Impact Bonds), which slightly reduces fit. The 
company's mega-cap scale and strong fundamentals fit Connor's long-term, analytical approach. 
Overall: solid growth investment, but consider whether technology concentration aligns with your 
illiquid private market focus.

Recommendation:
Based on AAPL's quantitative risk (ASI: 45/100) and qualitative fit (Good Fit), this stock offers 
a strong match—reasonable risk profile with excellent profile alignment.
```

### KO (Coca-Cola)

```
Stock Classification:
- Style: Dividend
- Sector: Consumer Defensive
- Market Cap Tier: Mega-cap
- P/E Ratio: 25.0
- Dividend Yield: 3.1%

Alignment Scores:
- Style Alignment: 0.35 (Dividend misaligned with growth focus)
- Sector Alignment: 0.30 (Consumer Defensive not in preferred sectors)
- Trait Alignment: 0.72 (Mega-cap, stable)
- OVERALL FIT: 0.38 ❌ Poor Fit

Reasoning:
KO is a Dividend stock in Consumer Defensive. Its Dividend character suggests income focus, which 
is secondary to Connor's growth orientation (67%). Consumer Defensive is outside Connor's stated 
sector preferences. While the mega-cap scale offers stability, the dividend focus and sector 
misalignment significantly reduce fit. This is more suited to income-focused investors.

Recommendation:
Based on KO's quantitative risk (ASI: 35/100) and qualitative fit (Poor Fit), this stock presents 
low quantitative risk but limited profile fit. Diversify accordingly.
```

## Error Handling

All functions handle missing or invalid data gracefully:
- Missing yfinance data defaults to neutral scores (0.50)
- API errors are caught and logged, with user-friendly error messages
- Stock fetch failures result in appropriate "Error" fit label

## Testing Recommendations

Test with diverse ticker symbols:

1. **AAPL** (Growth, Tech)
   - Expected: Good fit (~0.75–0.80), good style alignment but poor sector

2. **KO** (Dividend, Consumer Defensive)
   - Expected: Poor fit (~0.35–0.45), poor style and sector alignment

3. **GOOGL** (Growth, Tech)
   - Expected: Good fit (~0.75–0.80), similar to AAPL

4. **LEG** (Blend, Furniture/Home)
   - Expected: Decent fit (~0.55–0.65), mixed alignment

5. **Sports/Entertainment ticker** (if available)
   - Expected: Excellent fit (~0.80+), strong sector alignment

## Design Principles

1. **Non-Prescriptive**: Language says "is a good fit because..." not "you should buy this"
2. **Transparent**: Show which yfinance data fed into each decision
3. **Connected Signals**: Combine ASI (quantitative) + fit (qualitative) for holistic view
4. **Graceful Degradation**: Missing data doesn't break the analysis; defaults are conservative
5. **Human-Readable**: Reasoning explains the "why" in plain language

## Future Enhancements

- Portfolio-level fit analysis (sector concentration, style diversification)
- Historical fit tracking (how stock alignment changes over time)
- Custom profile creation UI
- Peer comparison (how stock ranks vs. similar stocks in its sector)
- Integration with backtesting to validate fit predictions
