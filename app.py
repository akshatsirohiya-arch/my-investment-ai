import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Institutional Momentum Command")

if "GEMINI_API_KEY" in st.secrets:
    try:
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

# --- 2. THE STABLE ENGINE ---

def call_ai_safe(prompt):
    """Uses the most stable 2026 free-tier model to avoid 404/429 errors."""
    if not client: return "AI Client not initialized."
    
    # In April 2026, gemini-2.5-flash-lite is the stable free-tier workhorse
    model_id = "gemini-2.5-flash-lite" 
    
    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ DAILY LIMIT REACHED: You've hit the 1,000 RPD free tier limit. Please wait until midnight PST or upgrade to Tier 1 (Pay-as-you-go)."
        return f"AI Error: {str(e)}"

# --- 3. UI & PERSISTENCE ---

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

    # SECTION 1: PERSISTENT AI REPORT
    if 'persisted_report' not in st.session_state:
        st.session_state['persisted_report'] = None

    if st.button("🚀 Run Institutional Analysis"):
        with st.spinner("Analyzing top breakouts..."):
            # STRIP DATA: Only send essential metrics to save tokens
            lite_data = df_filtered[['Ticker', 'RVOL', 'Velocity %']].head(10).to_csv(index=False)
            prompt = f"Analyze these 180-day breakouts for 2026: {lite_data}. Pick Top 3 with catalysts."
            st.session_state['persisted_report'] = call_ai_safe(prompt)

    # Show saved report if it exists (internet-drop proof)
    if st.session_state['persisted_report']:
        report_text = st.session_state['persisted_report']
        
        # DOWNLOAD BUTTON (.TXT)
        st.download_button(
            label="📥 Download Analysis (.txt)",
            data=report_text,
            file_name=f"Market_Report_{time.strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
        st.markdown(report_text)

    st.markdown("---")

    # SECTION 2: LIVE DATA
    st.header(f"📊 Watchlist ({len(df_filtered)} Stocks)")
    
    if st.checkbox("🔍 Load Industry Data"):
        with st.spinner("Classifying..."):
            # Simple apply to avoid quota-heavy batch calls
            df_filtered['Industry'] = df_filtered['Ticker'].apply(lambda x: yf.Ticker(x).info.get('industry', 'N/A'))

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
