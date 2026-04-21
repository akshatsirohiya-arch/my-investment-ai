import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Institutional AI Dashboard")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # v1beta is the most stable for the 2026 Lite models
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

# --- 2. LOGIC FUNCTIONS ---

def call_ai_safe(prompt):
    """Calls the high-limit Flash-Lite model with quota handling."""
    if not client: return "AI Client not initialized."
    
    # 2026 High-Quota Model for Free Users
    model_id = "gemini-2.0-flash-lite-preview-02-05" 
    
    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ QUOTA EXHAUSTED: Please wait 60 seconds or try again tomorrow."
        return f"AI Error: {str(e)}"

@st.cache_data(ttl=86400)
def get_industry_metadata(ticker):
    try:
        return yf.Ticker(ticker).info.get('industry', 'N/A')
    except:
        return "N/A"

# --- 3. MAIN UI ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
    df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
    
    # Sidebar Filters
    st.sidebar.header("🎯 Quality Filters")
    min_rvol = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.2)
    min_vel = st.sidebar.slider("Min Velocity %", 0, 500, 30)
    
    df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
    df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

    st.title("🏹 Multi-Bagger Intel Dashboard")

    # --- SECTION 1: AI RESEARCH (PERSISTENT & DOWNLOADABLE) ---
    st.header("🤖 Institutional Strategy Report")
    
    # Initialize session state so reports survive internet drops/refreshes
    if 'persisted_report' not in st.session_state:
        st.session_state['persisted_report'] = None

    col_btn1, col_btn2 = st.columns([1, 5])
    
    with col_btn1:
        if st.button("🚀 Run AI Analysis"):
            with st.spinner("Generating deep research..."):
                # Optimize tokens by sending only essential columns
                csv_data = df_filtered[['Ticker', 'RVOL', 'Velocity %']].head(12).to_csv(index=False)
                prompt = f"""
                Act as a Growth Fund Manager. Analyze these breakouts for 2026:
                {csv_data}
                1. Pick Top 5 multi-bagger candidates.
                2. Explain the macro catalysts.
                3. Call out risks or 'Fake' moves.
                """
                st.session_state['persisted_report'] = call_ai_safe(prompt)

    # If a report exists in memory, show it and enable download
    if st.session_state['persisted_report']:
        report_text = st.session_state['persisted_report']
        
        # Download Button
        st.download_button(
            label="📥 Download AI Report (.txt)",
            data=report_text,
            file_name=f"Market_Analysis_{time.strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )
        
        st.markdown(report_text)
        
        if st.button("🗑️ Clear Report"):
            st.session_state['persisted_report'] = None
            st.rerun()

    st.markdown("---")

    # --- SECTION 2: RAW DATA VIEW ---
    st.header(f"📊 Live Watchlist ({len(df_filtered)} Stocks)")
    
    if st.checkbox("🔍 Load Industry Data"):
        with st.spinner("Fetching sectors..."):
            df_filtered['Industry'] = df_filtered['Ticker'].apply(get_industry_metadata)

    st.dataframe(
        df_filtered,
        use_container_width=True,
        column_config={
            "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View Chart"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
            "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
            "High_180d": None, "Slope": None 
        },
        hide_index=True
    )
else:
    st.error("Missing daily_watchlist.csv.")
