import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

# 1. SETUP & CONFIG
st.set_page_config(layout="wide", page_title="Staircase AI Analyst")

# Pull the key automatically from your Streamlit Secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("OpenAI Key not found in Secrets! Please add it to your Streamlit Settings.")

# 2. THE "BRAIN" FUNCTIONS
@st.cache_data(ttl=3600) # Remembers data for 1 hour to stay under rate limits
def get_data(ticker):
    stock = yf.Ticker(ticker)
    # Download 1 year of history
    df = stock.history(period="1y")
    # Get basic company info
    info = stock.info
    return df, info

def analyze_staircase(df):
    """Calculates the 6-month breakout and 2-step staircase"""
    close_prices = df['Close']
    current_price = float(close_prices.iloc[-1])
    
    # 6-Month High (excluding today)
    six_month_high = float(close_prices.iloc[-126:-1].max())
    is_breakout = current_price > six_month_high
    
    # Staircase: Look at last 20 days (Split into two 10-day buckets)
    recent = df.tail(20)
    h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
    h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
    
    is_staircase = (h2 > h1) and (l2 > l1)
    return current_price, six_month_high, is_breakout, is_staircase

# 3. THE APP INTERFACE
st.title("📈 Staircase Strategy AI")
st.write("Professional Technical Scanner + Graham Value Analysis")

watchlist_raw = st.text_input("Enter Tickers (separated by commas)", "NVDA, AAPL, COST, AMZN")
tickers = [t.strip().upper() for t in watchlist_raw.split(",")]

if st.button("Run Full Market Analysis"):
    for ticker in tickers:
        with st.container():
            try:
                # Get the data
                df, info = get_data(ticker)
                
                if not df.empty:
                    # Run the Math
                    price, m6_high, breakout, staircase = analyze_staircase(df)
                    rev_growth = info.get('revenueGrowth', 0) * 100
                    
                    # --- COMPACT ROW DESIGN ---
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        st.subheader(ticker)
                        st.write(f"Current: **${price:.2f}**")
                        st.write(f"6M High: ${m6_high:.2f}")
                    
                    with col2:
                        if breakout and staircase:
                            st.success("✅ STRATEGY MATCH")
                            # AI Analysis
                            prompt = f"Analyze {ticker} (${price}). It's in a technical breakout. In 2 sentences: Is this a 'Value' play per Benjamin Graham, and what is the main risk?"
                            response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                            st.info(response.choices[0].message.content)
                        elif breakout:
                            st.warning("⚠️ Breakout only (No staircase yet)")
                        else:
                            st.write("❌ No pattern detected.")
                    
                    with col3:
                        # Checkbox to show/hide the chart
                        if st.checkbox("View Chart", key=f"btn_{ticker}"):
                            st.line_chart(df['Close'].tail(60))
                    
                    st.divider()
                
                # Small delay to prevent Yahoo from getting angry
                time.sleep(1.5)
                
            except Exception as e:
                st.error(f"Could not load {ticker}. Error: {e}")
