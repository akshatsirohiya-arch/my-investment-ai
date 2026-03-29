import streamlit as st
import yfinance as yf
import pandas as pd

st.title("Staircase Strategy Scanner")
st.write("Searching for 6-Month Breakouts with 2 Higher Highs/Lows")

# 1. Choose a stock to test
ticker_symbol = st.text_input("Enter Ticker (e.g., NVDA, AAPL, MSFT)", "NVDA")

if st.button("Run Strategy Check"):
    # 2. Download 1 year of price data
    data = yf.download(ticker_symbol, period="1y", interval="1d")
    
    if not data.empty:
        # Get the closing prices
        prices = data['Close']
        
        # 3. Check for 6-Month Breakout
        # (Look at the high of the last 126 trading days)
        six_month_high = prices.iloc[-126:-1].max()
        current_price = prices.iloc[-1]
        
        is_breakout = current_price > six_month_high
        
        # 4. Check for the "Staircase" (Higher Highs/Lows)
        # We look at the last 20 days for this pattern
        recent = data.tail(20)
        highs = recent['High']
        lows = recent['Low']
        
        # Split the 20 days into two 10-day halves to find 2 distinct steps
        # We force these to be single numbers (floats) using .item() or .max()
h1 = float(highs.iloc[0:10].max())
l1 = float(lows.iloc[0:10].min())
h2 = float(highs.iloc[10:20].max())
l2 = float(lows.iloc[10:20].min())
        
        is_staircase = (h2 > h1) and (l2 > l1)

        # 5. Show Results
        st.subheader(f"Analysis for {ticker_symbol}")
        
        if is_breakout and is_staircase:
            st.success("✅ MATCH! This stock is in a confirmed uptrend staircase.")
        elif is_breakout:
            st.warning("⚠️ Breakout detected, but the 2-High/2-Low pattern isn't clear yet.")
        else:
            st.error("❌ No breakout detected in the last 6 months.")
            
        st.write(f"Current Price: ${current_price:.2f}")
        st.line_chart(prices.tail(60)) # Show a 3-month chart
