import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

st.set_page_config(layout="wide", page_title="AI Research Assistant")

# --- SIDEBAR SETTINGS ---
st.sidebar.title("Settings")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# --- CACHING (Saves Data for 20 Minutes) ---
@st.cache_data(ttl=1200)
def get_historical_data(ticker):
    # Historical price data is rarely rate-limited
    stock = yf.Ticker(ticker)
    return stock.history(period="1y")

st.title("🤖 AI Staircase Scanner")
user_input = st.text_input("Watchlist (Comma Separated)", "NVDA, AAPL, COST, MSFT, TSLA, AMZN")
ticker_list = [t.strip().upper() for t in user_input.split(",")]

if st.button("Start Global Research"):
    for ticker in ticker_list:
        # Use an expander so the screen doesn't get cluttered
        with st.expander(f"Checking {ticker}...", expanded=True):
            try:
                # 1. Get Prices (Low risk of rate limit)
                data = get_historical_data(ticker)
                
                if not data.empty:
                    close_prices = data['Close']
                    current_price = float(close_prices.iloc[-1])
                    
                    # --- STAIRCASE MATH ---
                    six_month_high = float(close_prices.iloc[-126:-1].max())
                    recent = data.tail(20)
                    h1, h2 = float(recent['High'].iloc[0:10].max()), float(recent['High'].iloc[10:20].max())
                    l1, l2 = float(recent['Low'].iloc[0:10].min()), float(recent['Low'].iloc[10:20].min())
                    
                    is_breakout = current_price > six_month_high
                    is_staircase = (h2 > h1) and (l2 > l1)
                    
                    # 2. Display Result
                    if is_breakout and is_staircase:
                        st.success(f"🎯 {ticker}: Perfect Strategy Match!")
                        
                        # Only call AI if we have a match (Saves requests)
                        if api_key:
                            client = OpenAI(api_key=api_key)
                            res = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[{"role": "user", "content": f"Summarize {ticker} investment case based on Benjamin Graham's 'Intelligent Investor'. Is it a value play or speculation? 2 sentences."}]
                            )
                            st.info(res.choices[0].message.content)
                    elif is_breakout:
                        st.warning(f"⚠️ {ticker}: Breakout detected, but no staircase.")
                    else:
                        st.write(f"📉 {ticker}: No breakout pattern found.")
                    
                    st.line_chart(close_prices.tail(60))
                
                # IMPORTANT: Pause to keep Yahoo happy
                time.sleep(3) 

            except Exception as e:
                st.error(f"Yahoo is pausing requests for {ticker}. Skipping to next...")
                time.sleep(5) # Longer pause if we hit a wall
