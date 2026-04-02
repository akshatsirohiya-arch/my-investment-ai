import streamlit as st
import pandas as pd
import os
import urllib.parse

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="180-Day Breakout Command Center")

st.title("🏹 Momentum Strategy Command Center")
st.subheader("180-Day Range Breakouts: Technicals + AI Deep-Dive")

# --- HELPER: GENERATE PROMPT LINK ---
def get_gemini_link(ticker, price, velocity):
    # Professional prompt designed for the Gemini 2026 Web Interface
    raw_prompt = (
        f"Analyze {ticker} stock at ${price}. "
        f"It has a 180-day breakout velocity of {velocity}%. "
        "Is this a sustainable institutional move or a blow-off top? "
        "Check April 2026 news and volume profile."
    )
    # URL Encoding ensures the spaces and symbols don't break the browser link
    query = urllib.parse.quote(raw_prompt)
    return f"https://gemini.google.com/app?q={query}"

# --- MAIN LOGIC ---
if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. Data Processing
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        
        # 2. Add Link Columns
        # Restore TradingView
        df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        # New Gemini Deep Dive Link
        df['AI Analysis 🤖'] = df.apply(
            lambda x: get_gemini_link(x['Ticker'], x['Price'], round(x['Annualized_Return'], 1)), 
            axis=1
        )
        
        # 3. Sidebar Filters
        st.sidebar.header("🎯 Quality Filters")
        min_rvol = st.sidebar.slider("Min Relative Volume (RVOL)", 0.0, 5.0, 1.0)
        min_velocity = st.sidebar.slider("Min Velocity %", 0, 200, 20)
        
        # Filtering logic
        df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Annualized_Return'] >= min_velocity)].copy()
        df_filtered = df_filtered.sort_values(by="Annualized_Return", ascending=False)

        # 4. Table Display
        st.info(f"💡 Tip: Click 'Ask Gemini' to open a pre-filled analysis prompt for that specific ticker.")
        
        st.dataframe(
            df_filtered,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", help="Stock Symbol"),
                "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View Chart"),
                "AI Analysis 🤖": st.column_config.LinkColumn("Deep Dive", display_text="Ask Gemini"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Annualized_Return": st.column_config.NumberColumn("Velocity %", format="%.1f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
                "High_180d": None, 
                "Slope": None 
            },
            hide_index=True
        )

    else:
        st.warning("No stocks match your current filters. Try lowering the RVOL or Velocity requirements.")
else:
    st.error("File 'daily_watchlist.csv' not found. Please run your GitHub Action scanner.")
