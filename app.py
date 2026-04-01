import streamlit as st
import pandas as pd
import yfinance as yf
import os
from google import genai
from google.genai import types
import time

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Setup 2026 Gemini Client
if "GEMINI_API_KEY" in st.secrets:
    try:
        # Initializing the modern client
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Secrets.")
    client = None

st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum & AI Geopolitical Intelligence")

# --- FUNCTIONS ---

@st.cache_data(ttl=86400)
def get_industry_safe(ticker):
    try:
        time.sleep(0.2)
        tk = yf.Ticker(ticker)
        return tk.info.get('industry', 'Unknown 🔍')
    except: return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    """Uses the 2026 Google GenAI SDK with Model Fallback."""
    if not client: return "API Client not initialized. Check API Key."
    
    summary_list = [f"{r['Ticker']} (${r['Price']:.2f}, {r['Annualized_Return']:.1f}% Velocity)" for _, r in top_stocks_df.iterrows()]
    data_string = "; ".join(summary_list)
    
    prompt = f"""
    Analyze these Top 50 stocks breaking 180-day highs regarding the April 2026 Iran/Israel conflict: 
    {data_string}. 
    
    1. Categorize by War Sensitivity (High/Medium/Low).
    2. Identify Top 5 Strategic Picks.
    3. Flag Volatility Traps.
    """

    # Try these model aliases in order
    for model_alias in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-pro-exp-02-05"]:
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
            if model_alias == "gemini-2.0-pro-exp-02-05": # If last one fails
                return f"AI Analysis Error: {str(e)}"
            continue # Try next model

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # Calculate Momentum Velocity
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # Sidebar Settings
        st.sidebar.header("🎚️ Filters")
        min_rvol = st.sidebar.slider("Min RVOL (Vol Surge)", 0.0, 10.0, 1.0)
        df_display = df[df['RVOL'] >= min_rvol].head(100).copy()

        # Industry Classification
        st.sidebar.markdown("---")
        if st.sidebar.checkbox("🔍 Load Industries (Yahoo API)"):
            with st.spinner("Fetching Sectors..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click sidebar to load"

        # AI Report Trigger
        st.sidebar.markdown("---")
        if st.sidebar.button("🤖 Run AI Deep-Dive (Top 50)"):
            with st.status("Gemini searching 2026 war news...", expanded=True):
                ai_report = run_ai_analysis(df_display.head(50))
            st.markdown("### 🛰️ Geopolitical Intelligence Report")
            st.markdown(ai_report)

        # Main Table
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Chart": st.column_config.LinkColumn("Chart 📈", display_text="View Setup"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Annualized_Return": st.column_config.NumberColumn("Ann. Velocity %", format="%.1f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Volume", format="%.2fx"),
                "Industry": st.column_config.TextColumn("Industry"),
                "High_180d": None, "Slope": None
            }
        )
    else:
        st.warning("No breakouts found in today's data.")
else:
    st.error("Missing daily_watchlist.csv. Ensure your GitHub Action scanner is working.")
