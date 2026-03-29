import streamlit as st
import pandas as pd
import yfinance as yf
import os

st.set_page_config(layout="wide", page_title="180-Day Breakout Funnel")

st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Stocks Clearing 6-Month Resistance with Staircase Confirmation")

@st.cache_data(ttl=3600)
def get_industry(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('industry', 'N/A')
    except: return 'N/A'

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # Add TradingView Chart Links
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        # Sort by Slope by default
        df = df.sort_values(by="Slope", ascending=False)
        
        # Fetch Industry info in background
        with st.spinner("Classifying Industries..."):
            df['Industry'] = df['Ticker'].apply(get_industry)

        # UI: Sidebar Filters
        st.sidebar.header("Refine View")
        min_rvol = st.sidebar.slider("Min RVOL (Informational)", 0.0, 5.0, 0.0)
        df_display = df[df['RVOL'] >= min_rvol]

        # DISPLAY TABLE
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Chart": st.column_config.LinkColumn("Chart 📈", display_text="View Breakout"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "High_180d": st.column_config.NumberColumn("180D Resistance", format="$%.2f"),
                "Slope": st.column_config.NumberColumn("Trend Velocity"),
                "RVOL": st.column_config.NumberColumn("Rel Volume (180d Avg)", format="%.2fx"),
                "Industry": st.column_config.TextColumn("Industry")
            }
        )
        
        # Dashboard Insight
        top_stock = df_display.iloc[0]
        st.info(f"💡 **Observation:** {top_stock['Ticker']} is currently the strongest breakout in the **{top_stock['Industry']}** space.")
    else:
        st.warning("No stocks cleared their 180-day high today.")
else:
    st.error("Data file missing. Please trigger the GitHub Action.")
