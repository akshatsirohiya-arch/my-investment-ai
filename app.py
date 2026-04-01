import streamlit as st
import pandas as pd
import yfinance as yf
import os
from google import genai
from google.genai import types
import time

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Setup Modern 2026 Gemini Client
if "GEMINI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Secrets.")
    client = None

st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum & AI Strategic Equity Analysis")

# --- FUNCTIONS ---

@st.cache_data(ttl=86400)
def get_industry_safe(ticker):
    try:
        time.sleep(0.2)
        tk = yf.Ticker(ticker)
        return tk.info.get('industry', 'Unknown 🔍')
    except: return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    """Uses the latest stable 2026 models with a 'No-Skip' directive."""
    if not client: return "API Client not initialized."
    
    count = len(top_stocks_df)
    summary_list = [
        f"{r['Ticker']} (Price: ${r['Price']:.2f}, Ann. Velocity: {r['Annualized_Return']:.1f}%)" 
        for _, r in top_stocks_df.iterrows()
    ]
    data_string = "\n".join(summary_list)
    
    # The 'STRICT' Prompt to prevent the AI from summarizing only the top 5
    prompt = f"""
    You are a professional Equity Research Assistant. 
    I am providing a list of {count} stocks. You MUST provide a specific analysis for EVERY SINGLE ONE of the {count} stocks listed below. Do not skip any. Do not summarize.

    INPUT DATA:
    {data_string}

    REQUIRED TABLE COLUMNS FOR ALL {count} TICKERS:
    1. **Ticker**: The stock symbol.
    2. **Verdict**: [Strong Buy | Buy | Hold | Avoid].
    3. **2026 Catalyst**: 1-sentence on why it's moving (Energy, Defense, Tech, or Macro).
    4. **Risk**: High/Med/Low.

    Return ONLY the Markdown table containing all {count} rows.
    """

    # 2026 Stable Model List - using the most robust version for large tables
    for model_alias in ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite"]:
        try:
            response = client.models.generate_content(
                model=model_alias,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return response.text
        except Exception as e:
            if model_alias == "gemini-2.0-flash-lite":
                return f"AI Analysis Error: {str(e)}"
            continue

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # Calculate Momentum Metrics
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # Sidebar Controls
        st.sidebar.header("🎚️ Filters")
        analysis_count = st.sidebar.select_slider("Stocks to Analyze", options=[10, 25, 50], value=25)
        min_rvol = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.0)
        
        # Filter primary data
        df_display = df[df['RVOL'] >= min_rvol].head(analysis_count).copy()

        # Industry Data Toggle
        st.sidebar.markdown("---")
        if st.sidebar.checkbox("🔍 Load Industry Metadata"):
            with st.spinner("Fetching..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click to load"

        # --- SECTION 1: AI REPORT ---
        st.sidebar.markdown("---")
        if st.sidebar.button(f"🤖 Generate AI Verdicts for Top {len(df_display)}"):
            with st.status(f"AI Analysing {len(df_display)} Tickers...", expanded=True):
                report = run_ai_analysis(df_display)
            st.markdown("### 🛰️ Geopolitical & Strategic Verdicts")
            st.markdown(report)
            st.markdown("---")

        # --- SECTION 2: INTERACTIVE WATCHLIST ---
        st.subheader(f"📊 Live 180-Day Watchlist (Top {len(df_display)})")
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Chart": st.column_config.LinkColumn("Chart 📈", display_text="View"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Annualized_Return": st.column_config.NumberColumn("Velocity %", format="%.1f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Volume", format="%.2fx"),
                "Industry": st.column_config.TextColumn("Industry"),
                "High_180d": None, "Slope": None
            }
        )
    else:
        st.warning("No breakouts found.")
else:
    st.error("Missing daily_watchlist.csv. Run your scanner first.")
