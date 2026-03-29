import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

st.set_page_config(layout="wide", page_title="AI Research Assistant")

# --- SIDEBAR ---
st.sidebar.title("Settings")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

@st.cache_data(ttl=1200)
def get_historical_data(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="1y")

st.title("🤖 Compact AI Staircase Scanner")
user_input = st.text_input("Watchlist", "NVDA, AAPL, COST, MSFT, TSLA, AMZN")
ticker_list = [t.strip().upper() for t in user_input.split(",")]

if st.button("Start Global Research"):
    # We use a container to keep things organized
    for ticker in ticker_list:
        with st.container():
            try:
                data = get_historical_data(ticker)
                if not data.empty:
                    close_prices = data['Close']
                    current_price = float(close_prices.iloc[-1])
                    
                    # --- MATH ---
                    six_month_high = float(close_prices.iloc[-126:-1].max())
                    recent = data.tail(20)
                    h1, h2 = float(recent['High'].iloc[0:10].max()), float(recent['High'].iloc[10:20].max())
                    l1, l2 = float(recent['Low'].iloc[0:10].min()), float(recent['Low'].iloc[10:20].min())
                    
                    is_match = (current_price > six_month_high) and (h2 > h1) and (l2 > l1)
                    
                    # --- COMPACT DISPLAY ---
                    # Using columns to show info on one line
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        st.markdown(f"### {ticker}")
                        st.write(f"Price: **${current_price:.2f}**")
                    
                    with col2:
                        if is_match:
                            st.success("✅ STRATEGY MATCH")
                            if api_key:
                                client = OpenAI(api_key=api_key)
                                res = client.chat.completions.create(
                                    model="gpt-4o",
                                    messages=[{"role": "user", "content": f"Quick 2-sentence value analysis of {ticker} at ${current_price}."}]
                                )
                                st.info(res.choices[0].message.content)
                        else:
                            st.write("Pattern: *Incomplete*")

                    with col3:
                        # THE CLICKABLE CHART FEATURE
                        show_chart = st.checkbox("Show Chart", key=f"chart_{ticker}")
                    
                    if show_chart:
                        st.line_chart(close_prices.tail(60))
                    
                    st.divider() # Thin line between stocks
                
                time.sleep(2) 

            except Exception as e:
                st.error(f"Skipping {ticker}: Connection Busy.")
