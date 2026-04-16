import streamlit as st
import pandas as pd
import yfinance as yf
import os
import datetime
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Momentum Command Center")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # 2026 Stable Client: Using the standard v1 endpoint for guaranteed uptime
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1'} 
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Missing GEMINI_API_KEY in Streamlit Secrets.")
    client = None

# --- 2. LOGIC FUNCTIONS ---

def get_batch_summary(df):
    """Summarizes top movers using the stable 2026 workhorse model."""
    if not client: return "AI Client not initialized."
    
    # Context compression: Only send top 15 to keep AI sharp
    csv_context = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].head(15).to_csv(index=False)
    
    prompt = f"""
    Analyze these 180-day breakouts:
    {csv_context}
    
    1. Identify the 'Top 3' multi-bagger candidates for 2026 based on momentum quality.
    2. Group by Sector.
    3. Call out 'Fake Breakouts' (High velocity but suspicious volume).
    Return a concise Markdown report.
    """
    
    try:
        # gemini-2.5-flash is the 2026 stable standard for high-speed analysis
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"AI Summary currently unavailable: {str(e)}"

@st.cache_data(ttl=86400)
def get_industry_fast(ticker):
    """Cached industry lookup to prevent dashboard lag."""
    try:
        time.sleep(0.1)
        return yf.Ticker(ticker).info.get('industry', 'N/A')
    except:
        return "N/A"

# --- 3. MAIN APP UI ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # Processing
        df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        # Sidebar Controls
        st.sidebar.header("🎯 Filters")
        min_rvol = st.sidebar.slider("Min Relative Volume (RVOL)", 0.0, 10.0, 1.0)
        min_vel = st.sidebar.slider("Min Velocity %", 0, 500, 20)
        
        df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
        df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

        # --- SECTION 1: AI STRATEGIC SUMMARY (TOP) ---
        st.title("🏹 AI Multi-Bagger Command Center")
        
        with st.container():
            st.header("🤖 Today's Strategic Intelligence")
            if not df_filtered.empty:
                if st.button("🚀 Run AI Analysis"):
                    with st.status("Analyzing top breakouts...", expanded=True):
                        report = get_batch_summary(df_filtered)
                    st.markdown(report)
                else:
                    st.info("Click the button above to analyze the current watchlist.")
            else:
                st.warning("Adjust filters to include stocks for AI analysis.")

        st.markdown("---")

        # --- SECTION 2: THE WATCHLIST (BOTTOM) ---
        st.header(f"📊 Live Momentum Shortlist ({len(df_filtered)} stocks)")
        
        load_ind = st.checkbox("🔍 Load Industry & Sector Data", value=False)
        if load_ind:
            with st.spinner("Classifying sectors..."):
                df_filtered['Industry'] = df_filtered['Ticker'].apply(get_industry_fast)

        # High-Density Data Table
        st.dataframe(
            df_filtered,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Industry": st.column_config.TextColumn("Industry", width="medium"),
                "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
                "High_180d": None, "Slope": None 
            },
            hide_index=True
        )
    else:
        st.warning("Daily scan is empty. Check your scanner logs.")
else:
    st.error("Missing 'daily_watchlist.csv'. Ensure the 6AM IST GitHub Action is running.")
