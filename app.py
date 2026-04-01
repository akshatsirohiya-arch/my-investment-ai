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
    """Fetches industry metadata with rate-limiting safety."""
    try:
        time.sleep(0.2)
        tk = yf.Ticker(ticker)
        return tk.info.get('industry', 'Unknown 🔍')
    except: return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    """Uses 2026 Stable IDs with a fallback if Search Tool is restricted."""
    if not client: return "API Client not initialized."
    
    # Token Optimization
    summary_list = [f"{r['Ticker']}(${r['Price']:.1f},{r['Annualized_Return']:.0f}%vel)" for _, r in top_stocks_df.iterrows()]
    data_string = ",".join(summary_list)
    
    prompt = f"""
    Act as a Senior Equity Analyst. Analyze these {len(top_stocks_df)} stocks: {data_string}.
    For EVERY ticker, provide:
    1. Verdict (Buy/Hold/Avoid)
    2. 1-sentence logic for April 2026
    3. Risk Level (Low/Med/High)
    
    Return a Markdown table. DO NOT skip any tickers.
    """

    model_id = "gemini-2.0-flash"
    
    try:
        # Attempt 1: Analysis WITH Live Google Search
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return response.text
    except Exception as e:
        # Attempt 2: Fallback WITHOUT Search tool
        try:
            st.info("🔄 Optimizing connection: using internal 2026 intelligence...")
            response = client.models.generate_content(model=model_id, contents=prompt)
            return f"*(Live-Search Tool currently limited - using internal data)*\n\n{response.text}"
        except Exception as e2:
            if "429" in str(e2):
                return "🚨 Quota Exhausted: Please wait 60 seconds."
            return f"AI Analysis Error: {str(e2)}"

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # 2. SIDEBAR CONTROLS
        st.sidebar.header("🎚️ Filters")
        # FIX: The 'value' must match one of the 'options'
        analysis_count = st.sidebar.select_slider("Stocks to Analyze", options=[10, 20, 30], value=20)
        min_rvol = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.0)
        
        df_display = df[df['RVOL'] >= min_rvol].head(analysis_count).copy()

        # 3. Industry Data Toggle
        st.sidebar.markdown("---")
        if st.sidebar.checkbox("🔍 Load Industry Data"):
            with st.spinner("Classifying Sectors..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click to load"

        # 4. AI Trigger
        st.sidebar.markdown("---")
        if st.sidebar.button(f"🤖 Run AI Verdicts ({len(df_display)})"):
            with st.status("AI scanning market context...", expanded=True):
                report = run_ai_analysis(df_display)
            st.markdown(report)
            st.markdown("---")

        # 5. The Main Table
        st.subheader(f"📊 Live 180-Day Breakout Watchlist")
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
        st.warning("No breakout stocks found.")
else:
    st.error("Missing daily_watchlist.csv.")
