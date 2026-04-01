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
    """Uses the latest stable 2026 models for full equity analysis."""
    if not client: return "API Client not initialized."
    
    # Prepare data for up to 100 stocks
    summary_list = [
        f"{r['Ticker']} (${r['Price']:.2f}, Vol: {r['RVOL']:.1f}x, Velocity: {r['Annualized_Return']:.1f}%)" 
        for _, r in top_stocks_df.iterrows()
    ]
    data_string = "\n".join(summary_list)
    
    prompt = f"""
    Perform a professional Equity Research analysis on the following Top {len(top_stocks_df)} stocks 
    currently breaking out of 180-day price ranges.
    
    STOCK DATA:
    {data_string}

    REQUIRED OUTPUT FOR EACH STOCK:
    1. **Verdict**: [Strong Buy | Buy | Hold | Avoid]
    2. **Strategic Logic**: 1-sentence reasoning (consider sector trends, volume surge, and 2026 macro outlook).
    3. **Risk Profile**: Identify if it's a 'Momentum Leader', 'Safe Haven', or 'Volatility Trap'.
    4. **Geopolitical Context**: Briefly mention impact from current April 2026 global conflicts only if relevant to that specific ticker.

    Format the final report as a clean Markdown table.
    """

    # 2026 Stable Model List
    for model_alias in ["gemini-2.5-flash", "gemini-3-flash-preview", "gemini-2.5-pro"]:
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
            if model_alias == "gemini-2.5-pro": # Last attempt
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
        analysis_count = st.sidebar.select_slider("Analyze Top X Stocks", options=[25, 50, 100], value=50)
        min_rvol = st.sidebar.slider("Min RVOL (Volume Multiplier)", 0.0, 10.0, 1.0)
        
        df_display = df[df['RVOL'] >= min_rvol].head(analysis_count).copy()

        # Industry Data
        st.sidebar.markdown("---")
        if st.sidebar.checkbox("🔍 Load Industry Data"):
            with st.spinner("Classifying..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click to load"

        # AI Recommendations Button
        st.sidebar.markdown("---")
        if st.sidebar.button(f"🤖 Generate AI Verdicts (Top {analysis_count})"):
            with st.status(f"AI scanning {analysis_count} tickers...", expanded=True):
                st.write("Fetching latest 2026 market context...")
                ai_report = run_ai_analysis(df_display)
            st.markdown(ai_report)

        # Main Table Display
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
        st.warning("No breakouts found in the CSV.")
else:
    st.error("Missing daily_watchlist.csv. Run your scanner first.")
