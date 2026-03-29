import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(layout="wide", page_title="AI Batch Scanner")

st.title("🔍 Multi-Stock Strategy Scanner")
st.write("Enter multiple tickers separated by commas (e.g., NVDA, AAPL, MSFT, COST, TSLA)")

# 1. Input for a list of stocks
user_input = st.text_input("Your Watchlist", "NVDA, AAPL, MSFT, COST, TSLA, AMZN, GOOGL")
ticker_list = [t.strip().upper() for t in user_input.split(",")]

if st.button("Start Global Scan"):
    results = []
    progress_bar = st.progress(0)
    
    for index, ticker in enumerate(ticker_list):
        # Update progress bar
        progress_bar.progress((index + 1) / len(ticker_list))
        st.write(f"Analyzing {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
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

                # --- SCORE ---
                status = "❌ No Match"
                if is_breakout and is_staircase:
                    status = "✅ STRATEGY MATCH"
                elif is_breakout:
                    status = "⚠️ Breakout Only"

                results.append({
                    "Ticker": ticker,
                    "Price": round(current_price, 2),
                    "6M High": round(six_month_high, 2),
                    "Status": status
                })
            
            # SMALL PAUSE: This helps prevent the "Rate Limit" error
            time.sleep(1) 
            
        except Exception as e:
            st.warning(f"Skipping {ticker} due to data error.")

    # 2. Display the Final Table
    if results:
        df = pd.DataFrame(results)
        st.divider()
        st.subheader("📊 Scan Results")
        
        # Highlight the matches
        st.dataframe(df.style.applymap(
            lambda x: 'background-color: #d4edda' if x == "✅ STRATEGY MATCH" else '', 
            subset=['Status']
        ))
    else:
        st.error("No results found.")
