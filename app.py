import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Momentum Command Center")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # Standard v1beta for high-quota lite models
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1beta'} 
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Missing GEMINI_API_KEY in Secrets.")
    client = None

# --- 2. CORE UTILITIES ---

def call_ai_safe(prompt):
    """Calls the most stable Lite model for 2026 to avoid 404s."""
    if not client: return "AI Client not initialized."
    
    # FIX: Using the universal stable alias for 2026
    model_id = "gemini-2.0-flash-lite" 
    
    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ QUOTA EXHAUSTED: Please wait 60 seconds."
        return f"AI Error: {str(e)}"

@st.cache_data(ttl=86400)
def get_industry_metadata(ticker):
    try:
        return yf.Ticker(ticker).info.get('industry', 'N/A')
    except:
        return "N/A"

# --- 3. MAIN UI LAYOUT ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    # Prep data
    df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
    df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
    
    st.title("🏹 Multi-Bagger Intel Dashboard")

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("🎯 Quality Filters")
    min_rvol = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.2)
    min_vel = st.sidebar.slider("Min Velocity %", 0, 500, 30)
    
    df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
    df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

    # --- SECTION 1: AI RESEARCH (PERSISTENT & .TXT DOWNLOAD) ---
    st.header("🤖 Institutional Strategy Report")
    
    # Session state to survive refreshes
    if 'persisted_report' not in st.session_state:
        st.session_state['persisted_report'] = None

    if st.button("🚀 Run AI Analysis"):
        with st.spinner("Analyzing top breakouts..."):
            # Sending minimal data to save tokens
            csv_data = df_filtered[['Ticker', 'RVOL', 'Velocity %']].head(12).to_csv(index=False)
            prompt = f"Analyze these 180-day breakouts for 2026: {csv_data}. Pick Top 5 and explain catalysts."
            st.session_state['persisted_report'] = call_ai_safe(prompt)

    if st.session_state['persisted_report']:
        report_text = st.session_state['persisted_report']
        
        # DOWNLOAD OPTION: TXT
        st.download_button(
            label="📥 Download Report (.txt)",
            data=report_text,
            file_name=f"AI_Report_{time.strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
        
        st.markdown(report_text)
        
        if st.button("🗑️ Clear Saved Analysis"):
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
            "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
            "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
            "High_180d": None, "Slope": None 
        },
        hide_index=True
    )
else:
    st.error("Missing daily_watchlist.csv.")
