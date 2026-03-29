import streamlit as st
import yfinance as yf
import pandas as pd

st.title("Staircase Strategy + Fundamentals")
st.write("Checking Technical Trend and Financial Health")

ticker_symbol = st.text_input("Enter Ticker", "NVDA")

if st.button("Run Full Research"):
    # 1. Download Price & Company Info
    stock = yf.Ticker(ticker_symbol)
    data = stock.history(period="1y")
    info = stock.info # This pulls the "Financial Medical Record"
    
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
        # We use .get() to avoid errors if the data is missing
        rev_growth = info.get('revenueGrowth', 0) * 100 
        profit_margin = info.get('profitMargins', 0) * 100
        fcf = info.get('freeCashflow', 0)
        
        # --- DISPLAY RESULTS ---
        st.subheader(f"Results for {ticker_symbol}")
        
        # Column Layout for a clean look
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", f"${current_price:.2f}")
        col2.metric("Revenue Growth", f"{rev_growth:.1f}%")
        col3.metric("Profit Margin", f"{profit_margin:.1f}%")

        if is_breakout and is_staircase:
            st.success("✅ TECHNICAL MATCH: 6-Month Breakout + Staircase Trend.")
        else:
            st.warning("⚠️ Technical pattern is incomplete.")

        # Logic for "Quality"
        if rev_growth > 15 and profit_margin > 10:
            st.success("💎 FUNDAMENTAL QUALITY: Strong growth and healthy margins.")
        else:
            st.info("ℹ️ Fundamentals: Growth or margins are below the 'High Quality' threshold.")

        st.write(f"Free Cash Flow: ${fcf:,.0f}")
        st.line_chart(close_prices.tail(100))
