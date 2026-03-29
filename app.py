import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="AI Strategy Scanner", layout="wide")
st.title("📈 Staircase Strategy Scanner")

ticker_symbol = st.text_input("Enter Ticker", "NVDA").upper()

if st.button("Run Research"):
    stock = yf.Ticker(ticker_symbol)
    
    try:
        # 1. Pull Price History (This usually works even when 'info' is blocked)
        data = stock.history(period="1y")
        
        if not data.empty:
            close_prices = data['Close']
            
            # --- TECHNICAL LOGIC ---
            six_month_high = float(close_prices.iloc[-126:-1].max())
            current_price = float(close_prices.iloc[-1])
            is_breakout = current_price > six_month_high
            
            recent = data.tail(20)
            h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
            h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
            is_staircase = (h2 > h1) and (l2 > l1)

            # --- DISPLAY TECHNICALS ---
            st.subheader(f"Analysis for {ticker_symbol}")
            st.metric("Current Price", f"${current_price:.2f}")

            if is_breakout and is_staircase:
                st.success("✅ STRATEGY MATCH: 6-Month Breakout + Staircase.")
            elif is_breakout:
                st.info("⚠️ BREAKOUT: At highs, but staircase is forming.")
            else:
                st.error("❌ NO BREAKOUT: Below 6-month high.")

            st.line_chart(close_prices.tail(100))

            # --- THE SAFETY NET FOR FUNDAMENTALS ---
            st.divider()
            st.write("### Financial Health Check")
            try:
                info = stock.info
                rev_growth = info.get('revenueGrowth', 0) * 100
                profit_margin = info.get('profitMargins', 0) * 100
                
                col1, col2 = st.columns(2)
                col1.metric("Revenue Growth", f"{rev_growth:.1f}%")
                col2.metric("Profit Margin", f"{profit_margin:.1f}%")
            except:
                st.warning("📡 Financial data (Revenue/Profit) is temporarily unavailable from Yahoo. Technical chart is still valid.")

    except Exception as e:
        st.error("Could not load price data. Please wait a moment and try a different ticker.")
