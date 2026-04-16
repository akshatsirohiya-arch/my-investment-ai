import streamlit as st
import pandas as pd
import yfinance as yf
import os
import datetime
import time
from google import genai

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Multi-Bagger Command Center")

# Initialize Gemini 3 Client
if "GEMINI_API_KEY" in st.secrets:
    try:
        # Explicitly using the 2026 Stable Client setup
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1'}
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Streamlit Secrets.")
    client = None

# --- AI ANALYSIS FUNCTION ---

def get_batch_analysis(df):
    """Sends the filtered watchlist to AI for a top-down strategic report."""
    if not client: return "AI Client not initialized."
    
    # We send a clean version of the data to keep the prompt focused
    csv_data = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].to_csv(index=False)
    
    prompt = f"""
    Act as an Institutional Growth Strategist. Analyze this 180-day breakout watchlist:
    
    {csv_data}
    
    TASK:
    1. Identify the 'Top 10' highest-probability multi-baggers for the next 12 months.
    2. Group them by Sector (e.g., Tech, Energy, Industrials).
    3. Call out any 'Fake Breakouts' (High velocity but suspicious volume or unsustainable trends).
    4. Provide a 1-sentence macro verdict for today: {datetime.date.today()}.
    
    Return the analysis in a clean Markdown format with a table for the Top 10.
    """

    try:
        # Using the latest Gemini 3 Flash for superior reasoning speed
        response = client.models.generate_content(
            model="gemini-3-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

# --- MAIN UI LAYOUT ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. Processing
        df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        # 2. Sidebar Filters (Affects both AI and Table)
        st.sidebar.header("🎯 Filter Settings")
        min_rvol = st.sidebar.slider("Min Rel Volume", 0.0, 10.0, 1.2)
        min_vel = st.sidebar.slider("Min Velocity %", 0, 300, 30)
        
        df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
        df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

        # --- SECTION 1: AI ANALYSIS (TOP) ---
        st.header("🤖 AI Strategic Recommendations")
        
        if st.button("🚀 Run Multi-Bagger Analysis"):
            with st.status("Gemini 3 processing market context...", expanded=True):
                report = get_batch_analysis(df_filtered)
            st.markdown(report)
        else:
            st.info("Click the button above to generate today's AI Deep-Dive Report.")

        st.markdown("---")

        # --- SECTION 2: RAW WATCHLIST (BOTTOM) ---
        st.header("📊 Full Momentum Watchlist")
        
        # Load Industry Data checkbox
        if st.checkbox("🔍 Load Industry/Sector Data"):
            with st.spinner("Fetching sectors..."):
                # Fast lookup (caching handled by Streamlit internally here)
                df_filtered['Industry'] = df_filtered['Ticker'].map(
                    lambda x: yf.Ticker(x).info.get('industry', 'N/A')
                )

        st.dataframe(
            df_filtered,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
                "High_180d": None, "Slope": None # Clean up technical columns
            },
            hide_index=True
        )
    else:
        st.warning("No data found in daily_watchlist.csv.")
else:
    st.error("Missing daily_watchlist.csv. Please wait for the 6AM IST scanner to complete.")
