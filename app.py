import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# --- NEW STEALTH SETTINGS ---
# This makes your app look like a real browser to avoid the Rate Limit Error
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

st.title("Staircase Strategy + Fundamentals")
st.write("Checking Technical Trend and Financial Health")

ticker_symbol = st.text_input("Enter Ticker", "NVDA")

if st.button("Run Full Research"):
    # We pass the 'session' we created above into yfinance
    stock = yf.Ticker(ticker_symbol, session=session)
    
    try:
        data = stock.history(period="1y")
        info = stock.info
        
        if not data.empty:
            close_prices = data['Close']
            
            # --- TECHNICAL CHECK ---
            six_month_high = float(close_prices.iloc[-126:-1].max())
            current_price = float(close_prices.iloc[-1])
            is_breakout = current_price > six_month_high
            
            recent = data.tail(20)
            h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
            h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
            is_staircase = (h2 > h1) and (l2 > l1)

            # --- FUNDAMENTAL CHECK ---
            rev_growth = info.get('revenueGrowth', 0) * 100 
            profit_margin = info.get('profitMargins', 0) * 100
            
            # --- DISPLAY RESULTS ---
            st.subheader(f"Results for {ticker_symbol}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${current_price:.2f}")
            col2.metric("Revenue Growth", f"{rev_growth:.1f}%")
            col3.metric("Profit Margin", f"{profit_margin:.1f}%")

            if is_breakout and is_staircase:
                st.success("✅ MATCH: 6-Month Breakout + Staircase Trend.")
            else:
                st.warning("⚠️ Technical pattern is incomplete.")

            st.line_chart(close_prices.tail(100))
            
    except Exception as e:
        st.error(f"Yahoo Finance is currently blocking requests. Please try again in 5 minutes. Error: {e}")
