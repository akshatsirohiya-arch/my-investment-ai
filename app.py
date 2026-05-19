"""
INSTITUTIONAL MOMENTUM COMMAND — v2
====================================
Rewrites by Claude. Key upgrades:
  1. HH/HL trend structure confirmation (not just velocity)
  2. Composite scoring: Trend + Momentum + Volume + Fundamental proxy
  3. Rich structured AI prompt with sector, macro context, risk profile
  4. Fundamental layer via yfinance (batched + cached)
  5. Stale data detection with timestamp warnings
  6. Graceful fallback if CSV missing (manual ticker entry)
  7. Report timestamp so you always know when it was generated
  8. Market pulse section (macro stance)
"""

import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
import json
from datetime import datetime, timedelta
from google import genai

# ─────────────────────────────────────────────
# 1. CONFIG
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Momentum Command v2", page_icon="🏹")

RISK_PROFILE = "Aggressive growth — position trades of 2–8 weeks, targeting 15–40% moves."
STRATEGY     = "Higher highs + higher lows trend structure required. Fundamental quality matters. AI/tech tailwinds preferred."
TODAY        = datetime.today().strftime("%B %d, %Y")

# ─────────────────────────────────────────────
# 2. GEMINI CLIENT
# ─────────────────────────────────────────────
@st.cache_resource
def get_client():
    if "GEMINI_API_KEY" not in st.secrets:
        return None
    try:
        return genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={"api_version": "v1beta"}
        )
    except Exception as e:
        st.sidebar.error(f"Gemini init error: {e}")
        return None

client = get_client()

def call_ai(prompt: str, model: str = "gemini-2.5-flash-lite") -> str:
    if not client:
        return "⚠️ AI Client not initialized. Check GEMINI_API_KEY in secrets."
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ Rate limit hit. Wait or upgrade to Gemini Tier 1."
        return f"AI Error: {str(e)}"

# ─────────────────────────────────────────────
# 3. HIGHER HIGHS / HIGHER LOWS ENGINE
#    Core of the trend filter — not just slope
# ─────────────────────────────────────────────
def compute_hh_hl(ticker: str, period: str = "6mo", window: int = 20) -> dict:
    """
    Returns whether a stock is making HH+HL vs 6-month baseline.
    Uses rolling window highs/lows to detect structure.
    """
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty or len(hist) < window * 2:
            return {"hh": False, "hl": False, "trend_structure": "INSUFFICIENT DATA", "score": 0}

        closes = hist["Close"]
        highs  = hist["High"]
        lows   = hist["Low"]

        # Rolling highs and lows with the given window
        roll_high = highs.rolling(window).max()
        roll_low  = lows.rolling(window).min()

        # Compare last 3 rolling windows to detect HH and HL
        # Slice into thirds: early, mid, recent
        n = len(roll_high.dropna())
        third = max(n // 3, 1)

        early_high = roll_high.dropna().iloc[:third].mean()
        mid_high   = roll_high.dropna().iloc[third:2*third].mean()
        late_high  = roll_high.dropna().iloc[2*third:].mean()

        early_low  = roll_low.dropna().iloc[:third].mean()
        mid_low    = roll_low.dropna().iloc[third:2*third].mean()
        late_low   = roll_low.dropna().iloc[2*third:].mean()

        hh = (late_high > mid_high) and (mid_high > early_high)
        hl = (late_low  > mid_low)  and (mid_low  > early_low)

        # Current price vs 6m high (proximity to breakout)
        current    = closes.iloc[-1]
        high_6m    = highs.max()
        pct_from_high = ((current - high_6m) / high_6m) * 100  # negative = below high

        if hh and hl:
            structure = "STRONG UPTREND"
            score = 10 if pct_from_high > -5 else 8
        elif hh and not hl:
            structure = "UPTREND (weak lows)"
            score = 6
        elif not hh and hl:
            structure = "BASING"
            score = 4
        else:
            structure = "DOWNTREND"
            score = 1

        return {
            "hh": hh,
            "hl": hl,
            "trend_structure": structure,
            "trend_score": score,
            "pct_from_6m_high": round(pct_from_high, 1),
            "current_price": round(current, 2),
            "high_6m": round(high_6m, 2),
        }
    except Exception as e:
        return {"hh": False, "hl": False, "trend_structure": "ERROR", "trend_score": 0, "error": str(e)}


# ─────────────────────────────────────────────
# 4. FUNDAMENTAL FETCHER (cached 24h)
# ─────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fundamentals(ticker: str) -> dict:
    """
    Pulls key fundamental signals from yfinance.
    Cached for 24 hours to avoid hammering the API.
    """
    try:
        info = yf.Ticker(ticker).info
        rev_growth    = info.get("revenueGrowth", None)      # TTM YoY
        earnings_gr   = info.get("earningsGrowth", None)
        profit_margin = info.get("profitMargins", None)
        pe            = info.get("trailingPE", None)
        fwd_pe        = info.get("forwardPE", None)
        mkt_cap       = info.get("marketCap", None)
        sector        = info.get("sector", "N/A")
        industry      = info.get("industry", "N/A")
        rec           = info.get("recommendationMean", None)  # 1=Strong Buy, 5=Sell
        short_ratio   = info.get("shortRatio", None)

        # Fundamental score (1–10)
        fund_score = 5  # baseline
        if rev_growth is not None:
            if rev_growth > 0.30: fund_score += 2
            elif rev_growth > 0.15: fund_score += 1
            elif rev_growth < 0: fund_score -= 2

        if earnings_gr is not None:
            if earnings_gr > 0.25: fund_score += 1
            elif earnings_gr < 0: fund_score -= 1

        if profit_margin is not None:
            if profit_margin > 0.20: fund_score += 1
            elif profit_margin < 0: fund_score -= 1

        if rec is not None:
            if rec < 2.0: fund_score += 1
            elif rec > 3.5: fund_score -= 1

        fund_score = max(1, min(10, fund_score))

        return {
            "sector":        sector,
            "industry":      industry,
            "market_cap":    mkt_cap,
            "rev_growth_pct": round(rev_growth * 100, 1) if rev_growth else None,
            "earnings_growth_pct": round(earnings_gr * 100, 1) if earnings_gr else None,
            "profit_margin_pct": round(profit_margin * 100, 1) if profit_margin else None,
            "trailing_pe":   round(pe, 1) if pe else None,
            "forward_pe":    round(fwd_pe, 1) if fwd_pe else None,
            "analyst_rec":   round(rec, 2) if rec else None,
            "short_ratio":   round(short_ratio, 1) if short_ratio else None,
            "fund_score":    fund_score,
        }
    except Exception as e:
        return {"sector": "N/A", "industry": "N/A", "market_cap": None, "fund_score": 5, "error": str(e)}


# ─────────────────────────────────────────────
# 5. COMPOSITE SCORER
# ─────────────────────────────────────────────
def compute_composite(row: pd.Series, trend_data: dict, fund_data: dict) -> dict:
    """
    Weighted composite score:
      Trend structure (HH/HL)  → 35%
      Momentum (Velocity %)    → 25%
      Volume (RVOL)            → 20%
      Fundamentals             → 20%
    """
    trend_score = trend_data.get("trend_score", 5)
    fund_score  = fund_data.get("fund_score", 5)

    # Normalize Velocity % → 1-10
    vel = row.get("Velocity %", 0)
    vel_score = min(10, max(1, vel / 50))  # 500% vel = 10, 50% = 1

    # Normalize RVOL → 1-10
    rvol = row.get("RVOL", 1.0)
    rvol_score = min(10, max(1, rvol * 2.5))  # RVOL 4x = 10

    composite = (
        trend_score * 0.35 +
        vel_score   * 0.25 +
        rvol_score  * 0.20 +
        fund_score  * 0.20
    )

    return {
        "trend_score":  round(trend_score, 1),
        "vel_score":    round(vel_score, 1),
        "rvol_score":   round(rvol_score, 1),
        "fund_score":   round(fund_score, 1),
        "composite":    round(composite, 1),
    }


# ─────────────────────────────────────────────
# 6. AI PROMPT — Rich & Structured
# ─────────────────────────────────────────────
def build_analysis_prompt(df_top: pd.DataFrame, macro_context: str = "") -> str:
    """
    Builds a rich, context-aware prompt.
    Sends sector, fundamentals, trend structure — not just velocity.
    """
    stocks_json = df_top[[
        "Ticker", "sector", "industry", "Velocity %", "RVOL",
        "trend_structure", "trend_score", "fund_score", "composite",
        "rev_growth_pct", "profit_margin_pct", "trailing_pe",
        "pct_from_6m_high"
    ]].head(10).to_json(orient="records", indent=2)

    prompt = f"""
You are an elite institutional equity analyst. Today is {TODAY}.

TRADER PROFILE:
- Risk: {RISK_PROFILE}
- Strategy: {STRATEGY}

MACRO CONTEXT (use to filter sector exposure):
{macro_context if macro_context else "US markets in AI-driven bull phase. Rate environment stable. Monitor tariff risks."}

STOCK DATA (pre-filtered for HH/HL trend structure + momentum):
{stocks_json}

FIELD GUIDE:
- trend_structure: STRONG UPTREND / UPTREND / BASING / DOWNTREND (based on higher highs + higher lows analysis)
- trend_score: 1-10 (10 = cleanest uptrend structure)  
- fund_score: 1-10 (10 = strong revenue growth, margins, analyst consensus)
- composite: 1-10 (weighted blend of all factors)
- pct_from_6m_high: how far below the 6-month high (0% = AT the high = breakout zone)
- RVOL: relative volume vs average (>2x = institutional interest)
- Velocity %: annualized price momentum

YOUR TASK:
1. Pick the TOP 3 stocks for a position trade (2-8 weeks).
2. For each, provide:
   - WHY NOW: Specific catalyst or setup reason (not generic)
   - ENTRY: Precise entry zone or condition
   - TARGET: Price target with % upside and timeframe  
   - STOP: Stop-loss level (invalidation point)
   - RISK: The single biggest risk to this trade
   - CONVICTION: High / Medium / Low with one-line justification

3. Give a 2-sentence PORTFOLIO NOTE on sector concentration or macro risk across the 3 picks.

4. Flag any stocks on the list to AVOID and why (1 line each).

Format your response in clean markdown with clear headers. Be specific and actionable — not generic.
"""
    return prompt


def build_pulse_prompt() -> str:
    return f"""
You are a macro strategist advising an aggressive US equity position trader. Today is {TODAY}.

Provide a DAILY MARKET PULSE covering:

## MARKET STANCE
State clearly: FULLY INVESTED | CAUTIOUS (reduce exposure) | CASH (risk-off)
Give 2-3 sentences justifying your stance based on current conditions.

## KEY MACRO FACTORS
- Fed & Rates: Current posture and what it means for growth stocks
- Dollar: Strength/weakness impact on multinationals vs domestic plays
- Volatility (VIX): Risk-on or risk-off signal
- Earnings cycle: Where we are and what sectors are in focus

## SECTOR ROTATION
- OWN NOW: Top 2 sectors and why
- REDUCE: 1-2 sectors losing momentum
- WATCH: 1 emerging theme or rotation to monitor

## AI TRADE HEALTH
Is the AI/semiconductor trade still the dominant theme? Rate it: 🔥 HOT / ⚡ ACTIVE / ❄️ COOLING

## THIS WEEK
2-3 specific events, data releases, or earnings that could move the market.

Be direct, specific, and opinionated. No hedging. This is for a trader who needs clear signals.
"""


# ─────────────────────────────────────────────
# 7. DATA LOADER WITH STALENESS CHECK
# ─────────────────────────────────────────────
def load_watchlist(path: str = "daily_watchlist.csv") -> tuple[pd.DataFrame | None, str]:
    """Returns (dataframe, warning_message)"""
    if not os.path.exists(path):
        return None, "missing"

    df = pd.read_csv(path)
    mod_time = datetime.fromtimestamp(os.path.getmtime(path))
    age_hours = (datetime.now() - mod_time).total_seconds() / 3600

    warning = ""
    if age_hours > 24:
        warning = f"⚠️ Data is {int(age_hours)}h old (last updated {mod_time.strftime('%b %d %H:%M')}). Consider refreshing your scanner."

    # Derived columns
    if "Slope" in df.columns and "Price" in df.columns:
        df["Velocity %"] = (df["Slope"] / df["Price"]) * 252 * 100
    if "Ticker" in df.columns:
        df["Chart"] = df["Ticker"].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")

    return df, warning


# ─────────────────────────────────────────────
# 8. MAIN APP
# ─────────────────────────────────────────────

st.markdown("""
<style>
    .metric-card { background: #0d1117; border: 1px solid #1e2d3d; border-radius: 8px; padding: 12px 16px; }
    .stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("🏹 Institutional Momentum Command v2")
st.caption(f"Today: {TODAY} | Strategy: Aggressive Position Trading | Filter: HH+HL Trend Structure")

# ── Sidebar ──────────────────────────────────
st.sidebar.header("⚙️ Filters")
min_rvol      = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.2, 0.1)
min_vel       = st.sidebar.slider("Min Velocity %", 0, 500, 30, 10)
min_composite = st.sidebar.slider("Min Composite Score", 1.0, 10.0, 5.0, 0.5)
min_mktcap_m  = st.sidebar.number_input("Min Market Cap ($M)", value=500, step=100)
require_hh_hl = st.sidebar.checkbox("Require HH+HL Structure", value=True)
macro_override = st.sidebar.text_area(
    "Macro Context Override (optional)",
    placeholder="e.g. Fed paused, tariff risks elevated, AI capex still growing..."
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Scoring Weights**")
st.sidebar.markdown("Trend Structure: **35%**")
st.sidebar.markdown("Velocity:        **25%**")
st.sidebar.markdown("RVOL:            **20%**")
st.sidebar.markdown("Fundamentals:    **20%**")

# ── Tabs ─────────────────────────────────────
tab_screen, tab_pulse, tab_manual = st.tabs(["📊 Screener", "🌐 Market Pulse", "✏️ Manual Entry"])

# ════════════════════════════════════════════
# TAB 1: SCREENER
# ════════════════════════════════════════════
with tab_screen:

    df_raw, stale_warning = load_watchlist()

    if stale_warning == "missing":
        st.error("❌ `daily_watchlist.csv` not found. Use the **Manual Entry** tab to enter tickers directly.")
        st.stop()

    if stale_warning:
        st.warning(stale_warning)

    df = df_raw.copy()

    # Basic filters
    if "RVOL" in df.columns:
        df = df[df["RVOL"] >= min_rvol]
    if "Velocity %" in df.columns:
        df = df[df["Velocity %"] >= min_vel]

    if df.empty:
        st.warning("No stocks pass the current filters. Try relaxing RVOL or Velocity thresholds.")
        st.stop()

    # ── Step 1: Enrich with HH/HL + Fundamentals ──
    st.info(f"🔍 Enriching {len(df)} stocks with trend structure + fundamentals... (first run takes ~30s)")

    enrich_btn = st.button("🚀 Enrich & Score All Stocks", type="primary")

    if enrich_btn or "enriched_df" not in st.session_state:
        progress = st.progress(0, text="Starting enrichment...")
        enriched_rows = []

        tickers = df["Ticker"].tolist()
        for i, (_, row) in enumerate(df.iterrows()):
            ticker = row["Ticker"]
            progress.progress((i + 1) / len(tickers), text=f"Analyzing {ticker}...")

            trend  = compute_hh_hl(ticker)
            fund   = fetch_fundamentals(ticker)
            scores = compute_composite(row, trend, fund)

            # Market cap filter
            mkt_cap = fund.get("market_cap", 0) or 0
            if mkt_cap < min_mktcap_m * 1_000_000:
                continue

            # HH+HL filter
            if require_hh_hl and not (trend.get("hh") and trend.get("hl")):
                continue

            combined = {**row.to_dict(), **trend, **fund, **scores}
            enriched_rows.append(combined)
            time.sleep(0.15)  # rate limit courtesy

        progress.empty()

        if not enriched_rows:
            st.warning("No stocks passed all filters after enrichment.")
            st.stop()

        df_enriched = pd.DataFrame(enriched_rows)
        df_enriched = df_enriched.sort_values("composite", ascending=False).reset_index(drop=True)
        df_enriched.index += 1  # rank starts at 1
        st.session_state["enriched_df"] = df_enriched
        st.session_state["enrich_time"] = datetime.now().strftime("%b %d %H:%M")

    df_enriched = st.session_state["enriched_df"]
    st.caption(f"Last enriched: {st.session_state.get('enrich_time', 'unknown')} | {len(df_enriched)} stocks passed all filters")

    # ── Apply composite filter ──
    df_display = df_enriched[df_enriched["composite"] >= min_composite].copy()

    # ── Score summary cards ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Stocks Passing", len(df_display))
    col2.metric("Avg Composite", f"{df_display['composite'].mean():.1f}/10" if not df_display.empty else "—")
    col3.metric("Strong Uptrends", int((df_display["trend_structure"] == "STRONG UPTREND").sum()) if not df_display.empty else 0)
    col4.metric("Avg Rev Growth", f"{df_display['rev_growth_pct'].mean():.0f}%" if "rev_growth_pct" in df_display and not df_display.empty else "—")

    # ── Main table ──
    st.subheader(f"📋 Ranked Watchlist ({len(df_display)} stocks)")

    display_cols = [
        "Ticker", "sector", "trend_structure", "composite",
        "trend_score", "vel_score", "rvol_score", "fund_score",
        "Velocity %", "RVOL", "current_price", "pct_from_6m_high",
        "rev_growth_pct", "profit_margin_pct", "trailing_pe", "Chart"
    ]
    display_cols = [c for c in display_cols if c in df_display.columns]

    st.dataframe(
        df_display[display_cols],
        use_container_width=True,
        column_config={
            "Chart":             st.column_config.LinkColumn("Chart", display_text="📈 View"),
            "composite":         st.column_config.ProgressColumn("Composite Score", min_value=0, max_value=10, format="%.1f"),
            "trend_score":       st.column_config.NumberColumn("Trend", format="%.1f"),
            "vel_score":         st.column_config.NumberColumn("Vel Score", format="%.1f"),
            "rvol_score":        st.column_config.NumberColumn("RVOL Score", format="%.1f"),
            "fund_score":        st.column_config.NumberColumn("Fund Score", format="%.1f"),
            "current_price":     st.column_config.NumberColumn("Price", format="$%.2f"),
            "Velocity %":        st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
            "pct_from_6m_high":  st.column_config.NumberColumn("% From 6m High", format="%.1f%%"),
            "rev_growth_pct":    st.column_config.NumberColumn("Rev Growth", format="%.0f%%"),
            "profit_margin_pct": st.column_config.NumberColumn("Net Margin", format="%.1f%%"),
            "trailing_pe":       st.column_config.NumberColumn("P/E", format="%.1f"),
            "RVOL":              st.column_config.NumberColumn("RVOL", format="%.2fx"),
        },
        hide_index=False,
    )

    # ── AI Analysis ──
    st.markdown("---")
    st.subheader("🤖 AI Deep Dive — Top Picks")

    if "ai_report" not in st.session_state:
        st.session_state["ai_report"] = None
        st.session_state["ai_report_time"] = None

    if st.button("🧠 Run AI Analysis on Top 10", type="primary"):
        with st.spinner("AI is analyzing trend structure, fundamentals, catalysts..."):
            prompt = build_analysis_prompt(df_display, macro_override)
            report = call_ai(prompt)
            st.session_state["ai_report"] = report
            st.session_state["ai_report_time"] = datetime.now().strftime("%b %d, %Y at %H:%M")

    if st.session_state["ai_report"]:
        st.caption(f"Generated: {st.session_state['ai_report_time']}")
        st.markdown(st.session_state["ai_report"])
        st.download_button(
            label="📥 Download Report (.txt)",
            data=f"Generated: {st.session_state['ai_report_time']}\n\n{st.session_state['ai_report']}",
            file_name=f"MomentumReport_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )


# ════════════════════════════════════════════
# TAB 2: MARKET PULSE
# ════════════════════════════════════════════
with tab_pulse:
    st.subheader("🌐 Daily Market Pulse")
    st.caption("Macro stance, sector rotation, and key events — refreshed on demand.")

    if "pulse_report" not in st.session_state:
        st.session_state["pulse_report"] = None
        st.session_state["pulse_time"] = None

    if st.button("🔄 Refresh Market Pulse", type="primary"):
        with st.spinner("Reading macro conditions..."):
            prompt = build_pulse_prompt()
            pulse  = call_ai(prompt)
            st.session_state["pulse_report"] = pulse
            st.session_state["pulse_time"] = datetime.now().strftime("%b %d, %Y at %H:%M")

    if st.session_state["pulse_report"]:
        st.caption(f"Last refreshed: {st.session_state['pulse_time']}")
        st.markdown(st.session_state["pulse_report"])
    else:
        st.info("Hit **Refresh Market Pulse** to get today's macro read.")


# ════════════════════════════════════════════
# TAB 3: MANUAL ENTRY (fallback if no CSV)
# ════════════════════════════════════════════
with tab_manual:
    st.subheader("✏️ Manually Enter Tickers")
    st.caption("Use this if you don't have a scanner CSV, or want to analyze specific stocks.")

    ticker_input = st.text_area(
        "Enter tickers (comma or newline separated)",
        placeholder="NVDA, MRVL, CRDO, AXON, PLTR",
        height=100
    )

    if st.button("🔍 Analyze These Tickers", type="primary"):
        raw_tickers = [t.strip().upper() for t in ticker_input.replace("\n", ",").split(",") if t.strip()]

        if not raw_tickers:
            st.warning("Enter at least one ticker.")
        else:
            progress = st.progress(0, text="Fetching data...")
            rows = []
            for i, ticker in enumerate(raw_tickers):
                progress.progress((i + 1) / len(raw_tickers), text=f"Fetching {ticker}...")
                trend  = compute_hh_hl(ticker)
                fund   = fetch_fundamentals(ticker)
                # For manual entry, create synthetic row with price as proxy
                row = pd.Series({
                    "Ticker":     ticker,
                    "RVOL":       1.5,   # unknown without scanner — mark neutral
                    "Velocity %": 50.0,  # unknown — mark neutral
                    "Price":      trend.get("current_price", 0),
                })
                scores = compute_composite(row, trend, fund)
                rows.append({**row.to_dict(), **trend, **fund, **scores})
                time.sleep(0.2)

            progress.empty()
            df_manual = pd.DataFrame(rows).sort_values("composite", ascending=False).reset_index(drop=True)
            df_manual.index += 1

            st.dataframe(
                df_manual[[c for c in [
                    "Ticker", "sector", "trend_structure", "composite",
                    "trend_score", "fund_score", "current_price",
                    "pct_from_6m_high", "rev_growth_pct", "trailing_pe"
                ] if c in df_manual.columns]],
                use_container_width=True,
                column_config={
                    "composite":        st.column_config.ProgressColumn("Composite", min_value=0, max_value=10, format="%.1f"),
                    "current_price":    st.column_config.NumberColumn("Price", format="$%.2f"),
                    "pct_from_6m_high": st.column_config.NumberColumn("% From 6m High", format="%.1f%%"),
                    "rev_growth_pct":   st.column_config.NumberColumn("Rev Growth", format="%.0f%%"),
                    "trailing_pe":      st.column_config.NumberColumn("P/E", format="%.1f"),
                }
            )

            if st.button("🧠 AI Analysis on These Tickers"):
                with st.spinner("Analyzing..."):
                    prompt = build_analysis_prompt(df_manual, macro_override)
                    report = call_ai(prompt)
                    st.session_state["ai_report"] = report
                    st.session_state["ai_report_time"] = datetime.now().strftime("%b %d, %Y at %H:%M")
                st.markdown(report)
