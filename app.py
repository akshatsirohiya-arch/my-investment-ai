import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

st.set_page_config(layout="wide", page_title="AI Investment Researcher")

st.title("🚀 My Advanced AI Strategy Scanner")
st.write("Step 1: Finding 6-Month Breakouts with a 'Staircase' Pattern (2 Highs/2 Lows)")

# List of stocks to scan (Started with a few, you can add all 2000 later)
TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA", "META", "AMZN", "NFLX"] 

def analyze_stock(ticker):
    # 1. Get the last 1 year of data
    data = yf.download(ticker, period="1y", interval="1d", progress=False)
    if len(data) < 150: return None
    
    close = data['Close']
    
    # 2. Check for 6-Month Breakout
    six_month_high = close.iloc[-130:-1].max() # High of previous 6 months
    current_price = close.iloc[-1]
    
    is_breakout = current_price > six_month_high
    
    # 3. Simple 'Staircase' Check (Last 20 days)
    # This checks if recent lows are getting higher
    recent_data = close.tail(20)
    low1 = recent_data.iloc[0:10].min()
    low2 = recent_data.iloc[10:20].min()
    
    is_staircase = low2 > low1 # The second 'dip' is higher than the first
    
    if is_breakout and is_staircase:
        # 4. Fetch Fundamentals (The 'Health' Check)
        info = yf.Ticker(ticker).info
        return {
            "Ticker": ticker,
            "Price": round(current_price, 2),
            "Rev Growth": info.get('revenueGrowth', 0) * 100,
            "Profit Margin": info.get('profitMargins', 0) * 100,
            "Cash": info.get('freeCashflow', 0)
        }
    return None

# The Button to start the scan
if st.button("Start Global Scan"):
    results = []
    for t in TICKERS:
        st.write(f"Analyzing {t}...")
        res = analyze_stock(t)
        if res:
            results.append(res)
    
    if results:
        df = pd.DataFrame(results)
        st.success("Found potential matches!")
        st.dataframe(df)
    else:
        st.warning("No stocks currently match your 'Staircase' criteria.")
