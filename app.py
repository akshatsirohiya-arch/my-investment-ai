import streamlit as st
import pandas as pd
import yfinance as yf
import os
from google import genai
from google.genai import types
import time

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Setup Client
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
    """Token-optimized analysis with built-in retry logic for 429 errors."""
    if not client: return "API Client not initialized."
    
    # COMPRESS DATA: Send only what is strictly necessary to save tokens
    summary_list = [f"{r['Ticker']}(${r['Price']:.1f},{r['Annualized_Return']:.0f}%vel)" for _, r in top_stocks_df.iterrows()]
    data_string = ",".join(summary_list)
    
    prompt = f"""
    Act as an Equity Analyst. Analyze these {len(top_stocks_df)} stocks: {data_string}.
    For EVERY ticker, provide:
    1. Verdict (Buy/Hold/Avoid)
    2. 1-sentence 2026 logic
    3. Risk Level
    Use a Markdown table. Do not skip any stocks.
    """

    # Retry Loop for 429 Errors
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash", # Best limits for free tier
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return response.text
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Quota hit. Retrying in {attempt + 5}s...")
                time.sleep(attempt + 5) # Wait progressively longer
            else:
                return f"AI Analysis Error: {str(e)}"
    
    return "Error: Quota exhausted after 3 attempts. Please wait 1 minute and try again."

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # Sidebar
        st.sidebar.header("🎚️ Filters")
        analysis_count = st.sidebar.select_slider("Stocks to Analyze", options=[10, 20, 30], value=20)
        min_rvol = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.0)
        
        df_display = df[df['RVOL'] >= min_rvol].head(analysis_count).copy()

        # Industry Toggle
        st.sidebar.markdown("---")
        if st.sidebar.checkbox("🔍 Load Industries"):
            with st.spinner("Fetching..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click to load"

        # AI Report
        st.sidebar.markdown("---")
        if st.sidebar.button(f"🤖 Run AI Verdicts ({len(df_display)})"):
            with st.status("Analyzing...", expanded=True):
                report = run_ai_analysis(df_display)
            st.markdown(report)
            st.markdown("---")

        # Watchlist Table
        st.subheader(f"📊 Top {len(df_display)} Momentum Breakouts")
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
