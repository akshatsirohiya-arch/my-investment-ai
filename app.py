import streamlit as st
import pandas as pd
import yfinance as yf
import os
from google import genai
from google.genai import types
import time
import datetime

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Setup Client
if "GEMINI_API_KEY" in st.secrets:
    try:
        # Initializing the client with the standard API version
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Secrets.")
    client = None

# --- CACHING LOGIC ---
CACHE_FILE = "ai_analysis_cache.txt"

def save_ai_report(text):
    with open(CACHE_FILE, "w") as f:
        f.write(f"{datetime.date.today()}\n{text}")

def load_ai_report():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            lines = f.readlines()
            if lines and lines[0].strip() == str(datetime.date.today()):
                return "".join(lines[1:])
    return None

# --- FUNCTIONS ---

@st.cache_data(ttl=86400)
def get_industry_safe(ticker):
    try:
        time.sleep(0.2)
        tk = yf.Ticker(ticker)
        return tk.info.get('industry', 'Unknown 🔍')
    except: return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    """Refined to be extremely stable to avoid ClientError."""
    if not client: return "API Client not initialized."
    
    # Token-efficient data string
    summary_list = [f"{r['Ticker']}(${r['Price']:.1f},{r['Annualized_Return']:.0f}%vel)" for _, r in top_stocks_df.iterrows()]
    data_string = ",".join(summary_list)
    
    prompt = f"""
    Act as a Senior Equity Analyst. Analyze these {len(top_stocks_df)} stocks: {data_string}.
    For EVERY ticker, provide:
    1. Verdict (Buy/Hold/Avoid)
    2. 1-sentence logic for April 2026
    3. Risk Level (Low/Med/High)
    Return a Markdown table.
    """

    # We use 'gemini-1.5-flash' here as it is the most compatible across all API tiers
    model_id = "gemini-1.5-flash"
    
    try:
        # STRIPPED-DOWN CALL: No Search tool, no complex config. 
        # This is the 'safest' way to avoid ClientError 404/400.
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        if response and response.text:
            return response.text
        else:
            return "AI returned an empty response. Please try again."
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

# --- MAIN APP ---
st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum & AI Strategic Equity Analysis")

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    if not df.empty:
        # Calculations
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # Sidebar
        st.sidebar.header("🎚️ Filters")
        analysis_count = st.sidebar.select_slider("Stocks to Analyze", options=[10, 20, 30], value=20)
        min_rvol = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.0)
        df_display = df[df['RVOL'] >= min_rvol].head(analysis_count).copy()

        # PERSISTENT AI REPORT SECTION
        st.sidebar.markdown("---")
        existing_report = load_ai_report()

        if existing_report:
            st.success("✅ Showing saved AI analysis for today.")
            st.markdown(existing_report)
            st.download_button("📥 Download Report", existing_report, f"Analysis_{datetime.date.today()}.txt")
        else:
            if st.sidebar.button(f"🤖 Generate AI Verdicts ({len(df_display)})"):
                with st.status("AI scanning market context...", expanded=True):
                    report = run_ai_analysis(df_display)
                    if "Error" not in report:
                        save_ai_report(report)
                st.markdown(report)

        # Main Table
        st.subheader("📊 Live 180-Day Breakout Watchlist")
        st.dataframe(df_display, use_container_width=True, column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Chart": st.column_config.LinkColumn("Chart 📈", display_text="View"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Annualized_Return": st.column_config.NumberColumn("Velocity %", format="%.1f%%"),
            "RVOL": st.column_config.NumberColumn("Rel Volume", format="%.2fx"),
            "Industry": st.column_config.TextColumn("Industry"),
            "High_180d": None, "Slope": None
        })
    else:
        st.warning("No breakout stocks found.")
else:
    st.error("Missing daily_watchlist.csv. Please ensure your 6AM scanner has run.")
