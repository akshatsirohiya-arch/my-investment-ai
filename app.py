import streamlit as st
import pandas as pd
import yfinance as yf
import os
import datetime
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="AI Multi-Bagger Hunter 2026")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # Forcing v1 stable API with the modern GenAI SDK
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1'}
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Missing GEMINI_API_KEY in Secrets.")
    client = None

# --- 2. CORE FUNCTIONS ---

def get_batch_analysis(df):
    """Sends filtered list to AI. Fixed for 2026 404 errors."""
    if not client: return "AI Client not initialized."
    
    # Context compression for faster AI reasoning
    csv_data = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].to_csv(index=False)
    
    prompt = f"""
    Act as a Senior Growth Equity Analyst. Analyze this 180-day breakout watchlist:
    {csv_data}
    1. Identify the 'Top 10' potential multi-baggers for the 2026 cycle.
    2. Group them by Sector strength.
    3. Flag 'Fake Breakouts' where velocity doesn't match volume profile.
    Return a Markdown report with a summary table.
    """

    # 2026 Stable aliases: 'preview' suffix is required for Gemini 3 in v1 endpoint
    models_to_try = ["gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-2.5-flash"]
    
    for model_id in models_to_try:
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception:
            continue # Try next model if 404 or rate limited
            
    return "AI Analysis Error: All 2026 model endpoints returned 404. Check API Key permissions."

@st.cache_data(ttl=86400)
def get_industry_fast(ticker):
    """Cached industry lookup to prevent app lag."""
    try:
        time.sleep(0.1)
        return yf.Ticker(ticker).info.get('industry', 'N/A')
    except:
        return "N/A"

# --- 3. UI LAYOUT ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # Data Prep
        df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        # Sidebar Controls
        st.sidebar.header("🎯 Quality Filters")
        min_rvol = st.sidebar.slider("Min Relative Volume (RVOL)", 0.0, 10.0, 0.0)
        min_vel = st.sidebar.slider("Min Velocity % (Annualized)", 0, 500, 0)
        
        df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
        df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

        # SECTION 1: AI RECOMMENDATIONS (TOP)
        st.header("🤖 AI Strategic Analysis")
        if not df_filtered.empty:
            if st.button("🚀 Identify Top 20 Multi-Baggers"):
                with st.status("Gemini 3 performing batch analysis...", expanded=True):
                    report = get_batch_analysis(df_filtered)
                st.markdown(report)
            else:
                st.info("Click to run AI analysis on the filtered list below.")
        else:
            st.warning("Filter results are empty. Adjust sliders to include more stocks.")

        st.markdown("---")

        # SECTION 2: THE WATCHLIST (BOTTOM)
        st.header(f"📊 Live Momentum Shortlist ({len(df_filtered)} stocks)")
        
        load_ind = st.checkbox("🔍 Load Industry & Sector Data")
        if load_ind:
            with st.spinner("Classifying..."):
                df_filtered['Industry'] = df_filtered['Ticker'].apply(get_industry_fast)

        # Professional Data Table
        st.dataframe(
            df_filtered,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Industry": st.column_config.TextColumn("Industry"),
                "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
                "High_180d": None, "Slope": None 
            },
            hide_index=True
        )
    else:
        st.warning("The daily scan found no breakouts today.")
else:
    st.error("Missing 'daily_watchlist.csv'. Ensure the GitHub Action scanner is active.")
