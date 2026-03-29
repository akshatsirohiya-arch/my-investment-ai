import streamlit as st
import yfinance as yf
import pandas as pd

# --- APP INTERFACE ---
st.set_page_config(page_title="AI Strategy Scanner", layout="wide")
st.title("📈 Staircase Strategy + Fundamentals")
st.write("Checking for 6-Month Breakouts and 'Higher Highs / Higher Lows'")

# Input for the stock ticker
ticker_symbol = st.text_input("Enter Ticker (e.g., NVDA, AAPL, MSFT, COST)", "NVDA")

if st.button("Run Research"):
    # 1. Connect to Yahoo Finance
    stock = yf.Ticker(ticker_symbol)
    
    try:
        # 2. Pull Price History (1 Year)
        data = stock.history(period="1y")
        
        # 3. Pull Financial "Vitals"
        info = stock.info
        
        if not data.empty:
            close_prices = data['Close']
            
            # --- TECHNICAL LOGIC (The Staircase) ---
            # Find the highest price of the previous 6 months (roughly 126 trading days)
            six_month_high = float(close_prices.iloc[-126:-1].max())
            current_price = float(close_prices.iloc[-1])
            
            # 1. Is it a breakout?
            is_breakout = current_price > six_month_high
            
            # 2. Is there a "Staircase" (Last 20 days)?
            recent = data.tail(20)
            h1 = float(recent['High'].iloc[0:10].max())
            l1 = float(recent['Low'].iloc[0:10].min())
            h2 = float(recent['High'].iloc[10:20].max())
            l2 = float(recent['Low'].iloc[10:20].min())
            
            is_staircase = (h2 > h1) and (l2 > l1)

            # --- FUNDAMENTAL LOGIC ---
            # Get Revenue Growth and Profit Margin (expressed as percentages)
            rev_growth = info.get('revenueGrowth', 0) * 100 
            profit_margin = info.get('profitMargins', 0) * 100
            
            # --- DISPLAY THE RESULTS ---
            st.subheader(f"Results for {ticker_symbol}")
            
            # Create three clean boxes for the numbers
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${current_price:.2f}")
            col2.metric("Revenue Growth", f"{rev_growth:.1f}%")
            col3.metric("Profit Margin", f"{profit_margin:.1f}%")

            # Final Verdicts
            if is_breakout and is_staircase:
                st.success("✅ STRATEGY MATCH: 6-Month Breakout + Confirmed Staircase Trend.")
            elif is_breakout:
                st.info("⚠️ BREAKOUT: Price is at new highs, but the 2-High/2-Low staircase isn't fully formed.")
            else:
                st.error("❌ NO BREAKOUT: Price is still below its 6-month peak.")

            if rev_growth > 15:
                st.success(f"🔥 GROWTH: Excellent Revenue Growth ({rev_growth:.1f}%) detected.")

            # Show the visual trend
            st.write("Last 100 Days Performance:")
            st.line_chart(close_prices.tail(100))
            
        else:
            st.error("Could not find data for that ticker. Please check the spelling.")

    except Exception as e:
        st.error("Yahoo Finance is busy. Please wait 1 minute and click the button again.")
        st.write(f"Technical details: {e}")
