import streamlit as st
import pandas as pd
import yfinance as yf
import os
import datetime
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Multi-Bagger Intel 2026")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # Using v1beta for access to the more capable 'pro' reasoning models
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1beta'} 
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Missing GEMINI_API_KEY.")
    client = None

# --- 2. THE "DEEP DIVE" ENGINE ---

def get_high_conviction_analysis(df):
    """Performs a comprehensive sector and fundamental cross-reference."""
    if not client: return "AI Client not initialized."
    
    # Send more data: Top 30 stocks for better comparative context
    csv_context = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].head(30).to_csv(index=False)
    
    prompt = f"""
    Act as a Senior Hedge Fund Portfolio Manager. 
    Analyze this 180-day breakout watchlist:
    {csv_context}
    
    REQUIRED RESEARCH DEPTH:
    1. SECTOR ROTATION: Which 3-4 stocks belong to the strongest 2026 macro themes (e.g. AI Infra, Nuclear, Defense, or Biotech)?
    2. THE 'MOATS': For the top 5 candidates, explain the likely fundamental reason for this breakout. 
    3. MOMENTUM QUALITY: Identify which stocks have 'Institutional Accumulation' (steady velocity + high RVOL) vs 'Retail Spikes'.
    4. ENTRY STRATEGY: Provide specific buy-zone advice for the top 10 tickers.
    5. MULTI-BAGGER POTENTIAL: Which 3 have the specific characteristics of a 5x-10x runner?
    
    Format with professional headings and clear, actionable bullet points.
    """
    
    try:
        # Switching to the 'Pro' model for much deeper reasoning and longer responses
        response = client.models.generate_content(
            model="gemini-1.5-pro", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Deep Analysis unavailable: {str(e)}"

def get_fundamental_audit(ticker):
    """Fetches real fundamental data to feed the AI for a specific stock."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        audit_data = {
            "Market Cap": info.get("marketCap"),
            "Revenue Growth": info.get("revenueGrowth"),
            "Profit Margins": info.get("profitMargins"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Debt-to-Equity": info.get("debtToEquity"),
            "Insider Ownership": info.get("heldPercentInsiders"),
            "Short Ratio": info.get("shortRatio")
        }
        
        prompt = f"""
        Provide an EMERGENCY AUDIT for {ticker}.
        DATA: {audit_data}
        
        DEEP RESEARCH TASKS:
        1. FUNDAMENTAL HEALTH: Is this company actually making money or is it a 'zombie' stock?
        2. INDUSTRY POSITION: Who are their competitors and do they have a tech/cost advantage?
        3. RED FLAGS: Analyze the debt and short ratio. Is there a squeeze risk or bankruptcy risk?
        4. 2026 OUTLOOK: Detailed research on why this stock could be a multi-bagger.
        """
        
        response = client.models.generate_content(model="gemini-1.5-pro", contents=prompt)
        return response.text, audit_data
    except Exception as e:
        return f"Fundamental lookup failed: {str(e)}", {}

# --- 3. MAIN APP UI ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        st.title("🏹 Institutional Multi-Bagger Intelligence")
        
        # --- TOP SECTION: BATCH STRATEGY ---
        with st.expander("🌍 GLOBAL SECTOR & MOMENTUM ANALYSIS", expanded=True):
            if st.button("🚀 Run Deep Sector Research (All Stocks)"):
                with st.status("Performing comparative institutional research...", expanded=True):
                    report = get_high_conviction_analysis(df)
                st.markdown(report)
        
        st.markdown("---")
        
        # --- MIDDLE SECTION: INDIVIDUAL TICKER AUDIT ---
        st.header("🔬 Individual Fundamental Audit")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            target_ticker = st.selectbox("Select Ticker for Audit", df['Ticker'].unique())
            run_audit = st.button("🔍 Run Full Fundamental Audit")
        
        with col2:
            if run_audit:
                with st.status(f"Auditing {target_ticker} balance sheet and industry position..."):
                    audit_text, metrics = get_fundamental_audit(target_ticker)
                
                # Display Key Stats
                m_cols = st.columns(3)
                m_cols[0].metric("Rev Growth", f"{metrics.get('Revenue Growth', 0)*100:.1f}%")
                m_cols[1].metric("Profit Margin", f"{metrics.get('Profit Margins', 0)*100:.1f}%")
                m_cols[2].metric("Debt/Equity", metrics.get('Debt-to-Equity', 'N/A'))
                
                st.markdown(audit_text)

        st.markdown("---")

        # --- BOTTOM SECTION: RAW DATA ---
        st.header("📊 Momentum Watchlist Data")
        st.dataframe(
            df.sort_values("Velocity %", ascending=False),
            use_container_width=True,
            column_config={
                "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
                "High_180d": None, "Slope": None 
            },
            hide_index=True
        )
    else:
        st.warning("Daily scan is empty.")
else:
    st.error("Missing daily_watchlist.csv.")
