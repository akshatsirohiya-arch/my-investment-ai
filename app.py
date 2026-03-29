import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

# 1. SETUP
st.set_page_config(layout="wide", page_title="Market Trend Hunter")

# Access OpenAI Key from Secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.sidebar.error("⚠️ OpenAI Key missing in Streamlit Secrets!")

# 2. THE DISCOVERY ENGINE
@st.cache_data(ttl=3600)
def get_trending_tickers():
    # This grabs the "Most Active" stocks currently on the market
    try:
        trending = yf.Search("", max_results=20).tickers
        # Filter for actual stock symbols (usually 3-5 letters)
        clean_list = [t['symbol'] for t in trending if len(t['symbol']) <= 5]
        return clean_list
    except:
        return ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "META", "AMZN", "GOOGL"]

@st.cache_data(ttl=1200)
def get_data(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="1y"), stock.info

def analyze_staircase(df):
    close_prices = df['Close']
    current_price = float(close_prices.iloc[-1])
    six_month_high = float(close_prices.iloc[-126:-1].max())
    
    recent = df.tail(20)
    h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
    h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
    
    is_match = (current_price > six_month_high) and (h2 > h1) and (l2 > l1)
    return current_price, six_month_high, is_match

# 3. SIDEBAR CONTROLS
st.sidebar.title("🛠️ Discovery Tools")
if st.sidebar.button("🔥 Load Top Trending Stocks"):
    trending_list = get_trending_tickers()
    st.session_state.watchlist = ", ".join(trending_list)

# 4. MAIN INTERFACE
st.title("🎯 AI Trend Hunter")
st.write("Scan your watchlist or load the market's most active stocks.")

# Manage the watchlist in "Session State" so it updates when you click the button
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = "NVDA, AAPL, MSFT"

user_input = st.text_input("Current Watchlist", st.session_state.watchlist)
tickers = [t.strip().upper() for t in user_input.split(",")]

if st.button("🚀 Start Global Analysis"):
    results_found = 0
    for ticker in tickers:
        with st.container():
            try:
                df, info = get_data(ticker)
                if not df.empty:
                    price, m6_high, is_match = analyze_staircase(df)
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        st.subheader(ticker)
                        st.write(f"Price: **${price:.2f}**")
                    
                    with col2:
                        if is_match:
                            results_found += 1
                            st.success("🎯 STRATEGY MATCH")
                            prompt = f"Analyze {ticker} at ${price}. Is this a high-quality trend or a bubble? 2 sentences."
                            response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                            st.info(response.choices[0].message.content)
                        else:
                            st.write("Pattern: *Waiting for breakout...*")
                    
                    with col3:
                        if st.checkbox("Show Chart", key=f"c_{ticker}"):
                            st.line_chart(df['Close'].tail(60))
                    
                    st.divider()
                time.sleep(1)
            except:
                continue
    
    if results_found == 0:
        st.info("No perfect matches found in this list. Try the 'Trending' button!")
