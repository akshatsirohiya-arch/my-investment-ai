import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

# 1. SETUP
st.set_page_config(layout="wide", page_title="Professional Footprint Scanner")

# Access OpenAI Key from Secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.sidebar.warning("Note: AI Analysis disabled (Check Streamlit Secrets for API Key)")

# 2. THE MATH FUNCTIONS
def analyze_with_volume_lookback(df):
    close = df['Close']
    volume = df['Volume']
    curr_p = float(close.iloc[-1])
    
    # A. 6-Month High & Staircase
    high_6m = float(close.iloc[-126:-1].max())
    recent = df.tail(20)
    h1, h2 = float(recent['High'].iloc[0:10].max()), float(recent['High'].iloc[10:20].max())
    l1, l2 = float(recent['Low'].iloc[0:10].min()), float(recent['Low'].iloc[10:20].min())
    is_staircase = (curr_p > high_6m) and (h2 > h1) and (l2 > l1)
    
    # B. 10-Day Max RVOL (Footprint)
    rvol_list = []
    # Check each of the last 10 days
    for i in range(1, 11):
        target_vol = volume.iloc[-i]
        historical_avg = volume.iloc[-(i+21):-i].mean()
        day_rvol = target_vol / historical_avg if historical_avg > 0 else 0
        rvol_list.append(day_rvol)
    
    max_rvol_10d = max(rvol_list)
    return curr_p, max_rvol_10d, is_staircase

# 3. SIDEBAR (The Bouncer)
st.sidebar.title("🛡️ Risk & Quality Filters")
min_cap_m = st.sidebar.number_input("Min Market Cap ($Millions)", value=300)
vol_threshold = st.sidebar.slider("Min 'Footprint' RVOL (10-Day Max)", 1.0, 5.0, 2.0)

# 4. MAIN INTERFACE
st.title("👣 The $300M+ Footprint Scanner")
st.write("Excluding risky penny stocks. Looking for Institutional volume spikes.")

user_input = st.text_input("Enter Watchlist (e.g. PLTR, SOFI, HOOD, TSLA)", "PLTR, SOFI, HOOD")

if st.button("🚀 Run Deep Scan"):
    # CREATE THE LIST FIRST (Fixes NameError)
    tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    
    for ticker in tickers:
        with st.container():
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # --- FILTER 1: THE $300M FLOOR ---
                mkt_cap = info.get('marketCap', 0)
                if mkt_cap < (min_cap_m * 1_000_000):
                    st.write(f"⏭️ Skipping {ticker}: Too small (${mkt_cap/1_000_000:.1f}M)")
                    continue
                
                # --- FILTER 2: DATA & VOLUME ---
                df = stock.history(period="1y")
                if df.empty or len(df) < 130:
                    continue
                    
                price, max_vol, is_match = analyze_with_volume_lookback(df)
                
                # --- FILTER 3: THE RVOL THRESHOLD ---
                if max_vol < vol_threshold:
                    continue
                
                # --- DISPLAY SUCCESSFUL MATCHES ---
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.subheader(ticker)
                    st.metric("Price", f"${price:.2f}")
                    st.write(f"Cap: **${mkt_cap/1_000_000:.0f}M**")
                
                with col2:
                    st.write(f"📈 **Max RVOL (10d):** {max_vol:.2f}x")
                    if is_match:
                        st.success("✅ STAIRCASE PATTERN CONFIRMED")
                        # Optional AI Analysis
                        if 'client' in locals():
                            prompt = f"Quick analysis of {ticker} (${price}). Is it a value buy or speculative bubble? 2 sentences."
                            ai_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                            st.info(ai_res.choices[0].message.content)
                    else:
                        st.warning("Volume present, but pattern still forming.")
                
                with col3:
                    if st.checkbox("View Chart", key=f"view_{ticker}"):
                        st.line_chart(df['Close'].tail(60))
                
                st.divider()
                time.sleep(0.5) # Be kind to Yahoo
                
            except Exception as e:
                st.error(f"Error checking {ticker}")
