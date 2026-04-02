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

# Setup Modern 2026 Gemini Client
if "GEMINI_API_KEY" in st.secrets:
    try:
        # Initializing the client - ensure your secret is the 'AIza...' key
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Streamlit Secrets.")
    client = None

# --- CACHING LOGIC (Saves AI Quota) ---
CACHE_FILE = "ai_analysis_cache.txt"

def save_ai_report(text):
    """Saves the AI verdict to a local file with today's date stamp."""
    try:
        with open(CACHE_FILE, "w") as f:
            f.write(f"{datetime.date.today()}\n{text}")
    except:
        pass

def load_ai_report():
    """Loads the report only if it matches today's date."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                lines = f.readlines()
                if lines and lines[0].strip() == str(datetime.date.today()):
                    return "".join(lines[1:])
        except:
            return None
    return None

# --- FUNCTIONS ---

@st.cache_data(ttl=86400)
def get_industry_safe(ticker):
    """Fetches sector info with 24h caching."""
    try:
        time.sleep(0.2) # Rate limit protection
        tk = yf.Ticker(ticker)
        return tk.info.get('industry', 'Unknown 🔍')
    except: 
        return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    """Uses Production Stable IDs to bypass 404 Beta errors."""
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
    Return a Markdown table. DO NOT skip any tickers.
    """

    # 'gemini-2.0-flash' is the 2026 Production Stable ID. 
    # Do NOT use 'models/' prefix or 'v1beta' config to avoid 404 errors.
    model_id = "gemini-2.0-flash"
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        if response and response.text:
            return response.text
        else:
            return "AI returned an empty response. Try reducing stock count."
    except Exception as e:
        # Fallback to 1.5 if 2.0 is unavailable
        try:
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return response.text
        except Exception as e2:
            return f"AI Analysis Error: {str(e2)}"

# --- MAIN APP LOGIC ---
st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum & AI Strategic Equity Analysis")

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. Momentum Calculations
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # 2. Sidebar Controls
        st.sidebar.header("🎚️ Filters")
        # Kept at 20 default for Free Tier stability
        analysis_count = st.sidebar.select_slider("Stocks to Analyze", options=[10, 20, 30], value=20)
        min_rvol = st.sidebar.slider("Min RVOL (Vol Surge)", 0.0, 10.0, 1.0)
        
        df_display = df[df['RVOL'] >= min_rvol].head(analysis_count).copy()

        # 3. Industry Data Toggle
        st.sidebar.markdown("---")
        if st.sidebar.checkbox("🔍 Load Industry Data"):
            with st.spinner("Classifying..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click to load"

        # 4. PERSISTENT AI REPORT SECTION
        st.sidebar.markdown("---")
        existing_report = load_ai_report()

        if existing_report:
            st.success("✅ Showing saved AI analysis for today.")
            st.markdown(existing_report)
            st.download_button("📥 Download Report (TXT)", existing_report, f"Analysis_{datetime.date.today()}.txt")
        else:
            if st.sidebar.button(f"🤖 Generate AI Verdicts ({len(df_display)})"):
                with st.status("AI scanning 2026 market context...", expanded=True):
                    report = run_ai_analysis(df_display)
                    if "Error" not in report:
                        save_ai_report(report)
                st.markdown(report)
        
        st.sidebar.markdown("---")

        # 5. The Main Watchlist Table
        st.subheader(f"📊 Live 180-Day Breakout Watchlist (Top {len(df_display)})")
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
        st.warning("No breakout stocks found in today's data.")
else:
    st.error("Missing daily_watchlist.csv. Ensure your 6AM IST GitHub Action is running.")
