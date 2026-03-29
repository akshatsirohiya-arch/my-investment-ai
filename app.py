import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

st.set_page_config(layout="wide", page_title="AI Research Assistant")

# --- CONFIGURATION ---
st.sidebar.title("Settings")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# --- CACHING DATA (The Secret Sauce) ---
# This tells the app to remember the data for 10 minutes (600 seconds)
@st.cache_data(ttl=600)
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="1y"), stock.info

st.title("🤖 AI-Powered Investment Researcher")
user_input = st.text_input("Watchlist", "NVDA, AAPL, COST, MSFT")
ticker_list = [t.strip().upper() for t in user_input.split(",")]

if st.button("Start AI Research"):
    for ticker in ticker_list:
        with st.expander(f"Analysis: {ticker}", expanded=True):
            try:
                # Use our cached function
                data, info = get_stock_data(ticker)
                
                if not data.empty:
                    close_prices = data['Close']
                    current_price = float(close_prices.iloc[-1])
                    
                    # Technical Logic
                    six_month_high = float(close_prices.iloc[-126:-1].max())
                    recent = data.tail(20)
                    h1, h2 = float(recent['High'].iloc[0:10].max()), float(recent['High'].iloc[10:20].max())
                    l1, l2 = float(recent['Low'].iloc[0:10].min()), float(recent['Low'].iloc[10:20].min())
                    
                    is_match = (current_price > six_month_high) and (h2 > h1) and (l2 > l1)
                    
                    if is_match:
                        st.success(f"✅ {ticker}: Strategy Match!")
                        if api_key:
                            client = OpenAI(api_key=api_key)
                            # AI Logic
                            res = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[{"role": "user", "content": f"Analyze {ticker} at ${current_price} based on Graham's Value principles. 3 sentences max."}]
                            )
                            st.info(res.choices[0].message.content)
                    else:
                        st.warning(f"❌ {ticker}: No breakout pattern.")
                    
                    st.line_chart(close_prices.tail(60))
                
                # Wait 2 seconds between stocks to avoid Rate Limits
                time.sleep(2) 

            except Exception as e:
                st.error(f"Skipping {ticker}: Limit reached. Try again in a minute.")
