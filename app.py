import streamlit as st
import pandas as pd
import yfinance as yf
import os
import datetime
from google import genai

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Multi-Bagger Command Center")

# Initialize Gemini Client
if "GEMINI_API_KEY" in st.secrets:
    try:
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1'}
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Gemini API Key missing.")
    client = None

# --- AI ANALYSIS FUNCTION ---
def get_batch_analysis(df):
    if not client: return "AI Client not initialized."
    csv_data = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].to_csv(index=False)
    prompt = f"""
    Analyze this 180-day breakout watchlist:
    {csv_data}
    1. Identify the 'Top 10' multi-baggers for 2026.
    2. Group by Sector.
    3. Call out 'Fake Breakouts'.
    Return a Markdown report with a table.
    """
    try:
        response = client.models.generate_content(model="gemini-3-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

# --- MAIN UI ---
if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. Processing
        df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        # 2. Sidebar Filters (RELAXED DEFAULTS)
        st.sidebar.header("🎯 Filter Settings")
        min_rvol = st.sidebar.slider("Min Rel Volume", 0.0, 5.0, 0.0) # Set to 0.0 to see everything
        min_vel = st.sidebar.slider("Min Velocity %", 0, 300, 0)     # Set to 0 to see everything
        
        df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
        df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

        # --- SECTION 1: AI ANALYSIS (TOP) ---
        st.header("🤖 AI Strategic Recommendations")
        
        # FIX: The button now shows even if the list is small
        if not df_filtered.empty:
            if st.button("🚀 Run Multi-Bagger Analysis"):
                with st.status("Gemini 3 processing...", expanded=True):
                    report = get_batch_analysis(df_filtered)
                st.markdown(report)
            else:
                st.info("Click the button to analyze the filtered list below.")
        else:
            st.warning("No stocks match your filters. Adjust the sidebar to see more.")

        st.markdown("---")

        # --- SECTION 2: RAW WATCHLIST (BOTTOM) ---
        st.header(f"📊 Full Watchlist ({len(df_filtered)} stocks)")
        
        if st.checkbox("🔍 Load Industry Data"):
            with st.spinner("Fetching..."):
                df_filtered['Industry'] = df_filtered['Ticker'].map(
                    lambda x: yf.Ticker(x).info.get('industry', 'N/A')
                )

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
        st.warning("The daily_watchlist.csv file is empty.")
else:
    st.error("Missing daily_watchlist.csv. Your 6AM scan might have failed.")
