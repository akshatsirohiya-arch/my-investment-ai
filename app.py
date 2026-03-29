import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

st.set_page_config(layout="wide", page_title="AI Research Assistant")

# --- SIDEBAR: KEY INPUT ---
st.sidebar.title("Configuration")
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

st.title("🤖 AI-Powered Investment Researcher")
st.write("Scanning for Breakouts and Consulting the 'Intelligent Investor' AI.")

user_input = st.text_input("Your Watchlist", "NVDA, AAPL, MSFT, COST, TSLA")
ticker_list = [t.strip().upper() for t in user_input.split(",")]

# --- AI FUNCTION ---
def ask_ai(ticker, price, growth):
    if not api_key:
        return "Please enter your API Key in the sidebar to see AI Analysis."
    
    client = OpenAI(api_key=api_key)
    
    instructions = f"""
    You are a professional investment analyst familiar with 'The Intelligent Investor' (Benjamin Graham) 
    and 'The Art and Science of Investing'. 
    
    The stock {ticker} is currently priced at ${price} and has a revenue growth of {growth}%. 
    It just hit a 6-month breakout with a 'Staircase' pattern (2 higher highs/lows).
    
    In 3 short sentences:
    1. Is this a 'Defensive' or 'Enterprising' investment according to Graham?
    2. What is the biggest risk for this specific company right now?
    3. Final verdict: Invest or Wait?
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": instructions}]
    )
    return response.choices[0].message.content

# --- THE SCANNER ---
if st.button("Start AI Research"):
    for ticker in ticker_list:
        with st.expander(f"Analyzing {ticker}...", expanded=True):
            try:
                stock = yf.Ticker(ticker)
                data = stock.history(period="1y")
                
                if not data.empty:
                    # 1. Technical Math
                    close_prices = data['Close']
                    six_month_high = float(close_prices.iloc[-126:-1].max())
                    current_price = float(close_prices.iloc[-1])
                    
                    recent = data.tail(20)
                    h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
                    h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
                    
                    is_match = (current_price > six_month_high) and (h2 > h1) and (l2 > l1)
                    
                    # 2. Fundamental Pull
                    rev_growth = stock.info.get('revenueGrowth', 0) * 100

                    # 3. Display Status
                    if is_match:
                        st.success(f"✅ {ticker} fits your Staircase Strategy!")
                        # Trigger the AI Brain
                        st.write("--- AI ANALYST REPORT ---")
                        report = ask_ai(ticker, current_price, rev_growth)
                        st.info(report)
                    else:
                        st.warning(f"❌ {ticker} does not meet all criteria yet.")
                    
                    st.line_chart(close_prices.tail(100))
                
                time.sleep(1) # Be nice to Yahoo
            except Exception as e:
                st.error(f"Error checking {ticker}: {e}")
