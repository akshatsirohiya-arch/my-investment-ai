import streamlit as st
import yfinance as yf
import pandas as pd

st.title("Staircase Strategy Scanner")
st.write("Searching for 6-Month Breakouts with 2 Higher Highs/Lows")

ticker_symbol = st.text_input("Enter Ticker (e.g., NVDA, AAPL, MSFT)", "NVDA")

if st.button("Run Strategy Check"):
    # 1. Download data
    data = yf.download(ticker_symbol, period="1y", interval="1d")
    
    if not data.empty:
        # Get the closing prices
        close_prices = data['Close']
        
        # --- FIX 1: Breakout Logic ---
        # We look at the high of the previous 6 months (126 days)
        # We use .max().item() to make sure it's just ONE number
        six_month_high = float(close_prices.iloc[-126:-1].max())
        current_price = float(close_prices.iloc[-1])
        
        is_breakout = current_price > six_month_high
        
        # --- FIX 2: Staircase Logic ---
        recent = data.tail(20)
        
        # Find the High and Low for the first 10 days
        h1 = float(recent['High'].iloc[0:10].max())
        l1 = float(recent['Low'].iloc[0:10].min())
        
        # Find the High and Low for the last 10 days
        h2 = float(recent['High'].iloc[10:20].max())
        l2 = float(recent['Low'].iloc[10:20].min())
        
        # Now compare single numbers
        is_staircase = (h2 > h1) and (l2 > l1)

        # --- RESULTS ---
        st.subheader(f"Analysis for {ticker_symbol}")
        
        # Now this 'if' statement will work because both sides are single True/False
        if is_breakout and is_staircase:
            st.success("✅ MATCH! This stock is in a confirmed uptrend staircase.")
        elif is_breakout:
            st.warning("⚠️ Breakout detected, but the 2-High/2-Low pattern isn't confirmed in the last 20 days.")
        else:
            st.error("❌ No 6-month breakout detected.")
            
        st.write(f"Current Price: ${current_price:.2f}")
        st.write(f"6-Month High was: ${six_month_high:.2f}")
        st.line_chart(close_prices.tail(60))
