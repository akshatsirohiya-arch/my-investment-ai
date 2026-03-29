import streamlit as st
import pandas as pd
import os
import yfinance as yf

st.set_page_config(layout="wide", page_title="Total Market Momentum")

st.title("🏹 Elite Momentum Funnel")
st.subheader("Total Market Staircase Patterns")

# --- DATA LOADING ---
if not os.path.exists("daily_watchlist.csv"):
    st.error("No data found. Please run the GitHub Action scanner.")
    st.stop()

df = pd.read_csv("daily_watchlist.csv")

# --- ENHANCEMENT: Fetch Industry for winners ---
@st.cache_data(ttl=3600)
def get_extra_info(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('industry', 'N/A'), info.get('sector', 'N/A')
    except:
        return 'N/A', 'N/A'

if not df.empty:
    # Sort by Momentum Slope
    df = df.sort_values(by="Slope", ascending=False).head(50) # Top 50 for performance
    
    # Add Industry & Chart Links
    if 'Industry' not in df.columns:
        with st.spinner("Fetching Industry and Chart data..."):
            df[['Industry', 'Sector']] = df['Ticker'].apply(lambda x: pd.Series(get_extra_info(x)))
    
    # Create a clickable TradingView Link
    df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")

    # --- DISPLAY TABLE ---
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Chart": st.column_config.LinkColumn("View Chart", display_text="Open Chart 📈"),
            "Slope": st.column_config.NumberColumn("Momentum Score", format="%.4f"),
            "RVOL": st.column_config.NumberColumn("Vol Surge", format="%.1fx"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        }
    )

    # --- TOP PICK ANALYSIS ---
    top = df.iloc[0]
    st.success(f"🏆 **Top Pick:** {top['Ticker']} in **{top['Industry']}**")
    st.write(f"This stock has the highest 'Staircase Slope' today. [Click here to see the chart]({top['Chart']})")

else:
    st.info("No stocks currently meet the staircase criteria.")
