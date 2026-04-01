import streamlit as st
import pandas as pd
import yfinance as yf
import os
from google import genai
from google.genai import types
import time

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Setup New 2026 Gemini Client
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
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
    """Uses the 2026 Google GenAI SDK for Grounded Analysis."""
    if not client: return "API Key missing."
    
    summary_list = [f"{r['Ticker']} (${r['Price']:.2f}, {r['Annualized_Return']:.1f}% Velocity)" for _, r in top_stocks_df.iterrows()]
    data_string = "; ".join(summary_list)
    
    prompt = f"Analyze these Top 50 stocks breaking 180-day highs regarding the April 2026 Iran conflict: {data_string}. Categorize by War Sensitivity, Top 5 Picks, and Volatility Traps."

    try:
        # New 2026 'Gemini 3 Flash' model with Search Grounding
        response = client.models.generate_content(
            model="gemini-3-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return response.text
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # Annualized Return Calculation
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # Filters
        st.sidebar.header("🎚️ Filters")
        min_rvol = st.sidebar.slider("Min RVOL (Vol Surge)", 0.0, 10.0, 1.0)
        df_display = df[df['RVOL'] >= min_rvol].head(100).copy()

        # Industry Toggle
        st.sidebar.markdown("---")
        if st.sidebar.checkbox("🔍 Load Industries"):
            with st.spinner("Fetching Sectors..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click sidebar to load"

        # AI Trigger
        st.sidebar.markdown("---")
        if st.sidebar.button("🤖 Run AI Deep-Dive (Top 50)"):
            with st.status("Gemini 3 searching war news...", expanded=True):
                ai_report = run_ai_analysis(df_display.head(50))
            st.markdown(ai_report)

        # Table Display
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
        st.warning("No breakouts found.")
else:
    st.error("Data file missing. Run scanner.py first.")
