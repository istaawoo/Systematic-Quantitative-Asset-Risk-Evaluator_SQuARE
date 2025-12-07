"""
stock_profile_matcher.py - Matches stock characteristics against Connor Barwin's behavioral profile.
"""
import json
import os


def load_connor_profile(json_path="behavioral_profile.json"):
    """Load Connor's behavioral profile from JSON."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default profile if file not found
        return {
            "investor_name": "Connor Barwin",
            "risk_tolerance": "Aggressive",
            "traits": ["Long-Term Oriented", "Hands-On/Operational", "Socially Conscious", "Diligent/Analytical"],
            "biases": ["Affinity Bias", "Narrative Fallacy", "Survivorship Bias"],
            "sector_preferences": ["Sports & Entertainment", "Urban Real Estate/Development", "Social Impact Bonds"],
            "growth_focus_score": 0.67,
            "momentum_bias": 0.60,
            "investment_horizon_years": 10,
            "market_cap_preference": "Mid to Large Cap",
            "liquidity_preference": "Lower (prefers illiquid, long-term holds)"
        }


def compute_style_alignment(stock_style, connor_profile):
    """
    Compute alignment between stock style and Connor's Aggressive profile.
    Connor is growth-focused (0.67 growth score), so Growth stocks score high.
    """
    growth_focus = connor_profile.get("growth_focus_score", 0.67)
    
    if stock_style == "Growth":
        return 0.95 * growth_focus  # ~0.64-0.95
    elif stock_style == "Blend":
        return 0.70 * growth_focus  # ~0.47-0.70
    elif stock_style == "Value":
        return 0.40 * (1 - growth_focus)  # ~0.13-0.40
    elif stock_style == "Dividend":
        return 0.35 * (1 - growth_focus)  # ~0.12-0.35
    else:
        return 0.50  # Neutral for unknown


def compute_sector_alignment(stock_sector, connor_profile):
    """
    Compute alignment between stock sector and Connor's preferred sectors.
    """
    preferred_sectors = connor_profile.get("sector_preferences", [])
    
    # Check for direct match
    for pref in preferred_sectors:
        if pref.lower() in stock_sector.lower() or stock_sector.lower() in pref.lower():
            return 0.95
    
    # Check for partial match (e.g., "Real Estate" in "Consumer Real Estate")
    preferred_keywords = []
    for pref in preferred_sectors:
        preferred_keywords.extend(pref.lower().split())
    
    stock_keywords = stock_sector.lower().split()
    common_keywords = set(preferred_keywords) & set(stock_keywords)
    
    if common_keywords:
        return 0.75
    
    # Neutral sectors (neither good nor bad)
    neutral_sectors = ["Technology", "Healthcare", "Financials", "Industrials"]
    if any(neut.lower() in stock_sector.lower() for neut in neutral_sectors):
        return 0.50
    
    # Non-preferred
    return 0.30


def compute_trait_alignment(classified_stock, connor_profile):
    """
    Compute alignment based on stock characteristics (market cap, fundamentals) vs Connor's traits.
    Connor is: Long-Term Oriented, Hands-On/Operational, Diligent/Analytical
    """
    alignment = 0.50  # Start neutral
    
    market_cap_tier = classified_stock.get("market_cap_tier")
    pe_ratio = classified_stock.get("pe_ratio")
    earnings_growth = classified_stock.get("earnings_growth")
    
    # Long-Term Oriented: Prefer large/stable companies with good fundamentals
    if market_cap_tier in ["Mega-cap", "Large-cap"]:
        alignment += 0.15
    elif market_cap_tier == "Mid-cap":
        alignment += 0.10
    elif market_cap_tier in ["Small-cap", "Micro-cap"]:
        alignment -= 0.10
    
    # Diligent/Analytical: Prefer stocks with clear, strong fundamentals
    if earnings_growth and earnings_growth > 0.10:
        alignment += 0.10
    elif earnings_growth and earnings_growth < 0:
        alignment -= 0.10
    
    if pe_ratio:
        if 15 <= pe_ratio <= 30:  # Reasonable P/E
            alignment += 0.10
        elif pe_ratio > 50:  # Expensive
            alignment -= 0.05
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, alignment))


def compute_overall_fit(style_alignment, sector_alignment, trait_alignment):
    """
    Compute overall fit score using weighted average.
    Weights: Style 50%, Sector 30%, Trait 20%
    """
    overall = (0.5 * style_alignment) + (0.3 * sector_alignment) + (0.2 * trait_alignment)
    return max(0.0, min(1.0, overall))


def fit_label_from_score(fit_score):
    """Map fit score to label."""
    if fit_score >= 0.80:
        return "Excellent Fit"
    elif fit_score >= 0.65:
        return "Good Fit"
    elif fit_score >= 0.50:
        return "Decent Fit"
    else:
        return "Poor Fit"


def fit_emoji_from_score(fit_score):
    """Map fit score to emoji indicator."""
    if fit_score >= 0.80:
        return "🎯"
    elif fit_score >= 0.65:
        return "✅"
    elif fit_score >= 0.50:
        return "⚠️"
    else:
        return "❌"


def generate_reasoning(classified_stock, connor_profile, style_alignment, sector_alignment, trait_alignment, overall_fit):
    """
    Generate human-readable reasoning explaining the fit.
    """
    ticker = classified_stock["ticker"]
    style = classified_stock["style"]
    sector = classified_stock["sector"]
    market_cap_tier = classified_stock["market_cap_tier"]
    pe_ratio = classified_stock["pe_ratio"]
    dividend_yield = classified_stock["dividend_yield"]
    
    fit_label = fit_label_from_score(overall_fit)
    growth_focus = connor_profile.get("growth_focus_score", 0.67)
    
    # Build reasoning paragraphs
    reasoning = f"{ticker} is a {style} stock in {sector}. "
    
    # Style alignment reasoning
    if style == "Growth":
        reasoning += f"Its Growth style aligns excellently with Connor's Aggressive risk tolerance and high growth focus ({growth_focus:.0%}). "
    elif style == "Value":
        reasoning += f"As a Value stock, it aligns less well with Connor's Aggressive profile and growth focus ({growth_focus:.0%}). "
    elif style == "Dividend":
        reasoning += f"Its Dividend character suggests income focus, which is secondary to Connor's growth orientation ({growth_focus:.0%}). "
    else:
        reasoning += f"As a Blend stock, it has mixed alignment with Connor's growth-focused profile. "
    
    # Sector alignment reasoning
    preferred = connor_profile.get("sector_preferences", [])
    if any(pref.lower() in sector.lower() for pref in preferred):
        reasoning += f"{sector} is within Connor's stated sector preferences (Sports & Entertainment, Real Estate, Impact Bonds). "
    else:
        reasoning += f"{sector} is outside Connor's stated sector preferences (Sports & Entertainment, Real Estate, Impact Bonds). "
    
    # Trait alignment reasoning (market cap, fundamentals)
    if market_cap_tier in ["Mega-cap", "Large-cap"]:
        reasoning += f"The {market_cap_tier} scale and solid fundamentals fit Connor's long-term, analytical approach and preference for established companies. "
    elif market_cap_tier == "Mid-cap":
        reasoning += f"The {market_cap_tier} scale offers growth potential while maintaining reasonable stability for Connor's long-term approach. "
    else:
        reasoning += f"The {market_cap_tier} scale may lack the stability Connor typically seeks for long-term holdings. "
    
    # Overall recommendation
    if overall_fit >= 0.80:
        reasoning += f"Overall: Excellent match—strong alignment across style, sector, and fundamentals."
    elif overall_fit >= 0.65:
        reasoning += f"Overall: Good fit. Consider whether the sector or style aligns with your portfolio diversification goals."
    elif overall_fit >= 0.50:
        reasoning += f"Overall: Decent fit but with notable misalignments. Evaluate against other opportunities."
    else:
        reasoning += f"Overall: Poor fit. Consider whether your investment thesis overrides the profile misalignments."
    
    return reasoning


def match_stock_to_connor(classified_stock, connor_profile=None):
    """
    Compute alignment scores and generate fit assessment for a stock against Connor's profile.
    
    Args:
        classified_stock (dict): Output from stock_classifier.classify_stock()
        connor_profile (dict): Connor's behavioral profile (loaded from JSON if not provided)
        
    Returns:
        dict: {
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
            'reasoning': str,
            'error': str or None
        }
    """
    if connor_profile is None:
        connor_profile = load_connor_profile()
    
    if classified_stock.get("error"):
        return {
            "ticker": classified_stock.get("ticker", "UNKNOWN"),
            "fit_score": None,
            "fit_label": "Error",
            "fit_emoji": "❌",
            "style_alignment": None,
            "sector_alignment": None,
            "trait_alignment": None,
            "stock_style": None,
            "stock_sector": None,
            "connor_risk_tolerance": connor_profile.get("risk_tolerance", "Unknown"),
            "reasoning": "Unable to fetch stock data.",
            "error": classified_stock.get("error")
        }
    
    try:
        style_align = compute_style_alignment(classified_stock.get("style"), connor_profile)
        sector_align = compute_sector_alignment(classified_stock.get("sector", "Unknown"), connor_profile)
        trait_align = compute_trait_alignment(classified_stock, connor_profile)
        overall = compute_overall_fit(style_align, sector_align, trait_align)
        label = fit_label_from_score(overall)
        emoji = fit_emoji_from_score(overall)
        reasoning = generate_reasoning(classified_stock, connor_profile, style_align, sector_align, trait_align, overall)
        
        return {
            "ticker": classified_stock.get("ticker"),
            "fit_score": overall,
            "fit_label": label,
            "fit_emoji": emoji,
            "style_alignment": style_align,
            "sector_alignment": sector_align,
            "trait_alignment": trait_align,
            "stock_style": classified_stock.get("style"),
            "stock_sector": classified_stock.get("sector"),
            "connor_risk_tolerance": connor_profile.get("risk_tolerance", "Unknown"),
            "reasoning": reasoning,
            "error": None
        }
    
    except Exception as e:
        return {
            "ticker": classified_stock.get("ticker"),
            "fit_score": None,
            "fit_label": "Error",
            "fit_emoji": "❌",
            "style_alignment": None,
            "sector_alignment": None,
            "trait_alignment": None,
            "stock_style": classified_stock.get("style"),
            "stock_sector": classified_stock.get("sector"),
            "connor_risk_tolerance": connor_profile.get("risk_tolerance", "Unknown"),
            "reasoning": "Error computing fit assessment.",
            "error": str(e)
        }
