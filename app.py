import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

# 1. PAGE SETUP
st.set_page_config(layout="wide", page_title="Institutional Footprint Scanner")

# 2. API KEY SETUP (FROM STREAMLIT SECRETS)
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.sidebar.warning("⚠️ OpenAI Key not found in Secrets. AI Analysis will be skipped.")

# 3. CORE CALCULATION ENGINE
def analyze_with_volume_lookback(df):
    """Calculates Price Breakout and the Max Relative Volume of the last 10 days."""
    close = df['Close']
    volume = df['Volume']
    curr_p = float(close.iloc[-1])
    
    # A. 6-Month High & Staircase Pattern
    # Look back 126 trading days (approx 6 months)
    high_6m = float(close.iloc[-126:-1].max())
    
    # Staircase: Higher Highs and Higher Lows in the last 20 days
    recent = df.tail(20)
    h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
    h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['High'].iloc[10:20].min())
    
    is_breakout = curr_p > high_6m
    is_staircase = (h2 > h1) and (l2 > l1)
    
    # B. 10-Day Max RVOL (Footprint of Smart Money)
    rvol_list = []
    days_ago_list = []
    
    for i in range(1, 11):
        target_vol = volume.iloc[-i]
        # Compare to the 20-day average leading up to that day
        hist_avg = volume.iloc[-(i+21):-i].mean()
        day_rvol = target_vol / hist_avg if hist_avg > 0 else 0
        rvol_list.append(day_rvol)
    
    max_rvol_10d = max(rvol_list)
    # Find which day the spike happened (0 = today, 9 = nine days ago)
    days_ago = rvol_list.index(max_rvol_10d) 
    
    return curr_p, max_rvol_10d, (is_breakout and is_staircase), days_ago

# 4. SIDEBAR CONTROLS
st.sidebar.title("🛡️ Risk & Quality Filters")
min_cap_m = st.sidebar.number_input("Min Market Cap ($Millions)", value=300)
vol_threshold = st.sidebar.slider("Min 'Footprint' RVOL (10-Day Max)", 1.0, 5.0, 2.0)

# 5. MAIN INTERFACE
st.title("👣 The $300M+ Institutional Footprint Scanner")
st.write("Searching for technical breakouts backed by significant recent volume.")

user_input = st.text_input("Watchlist (Comma Separated)", "PLTR, SOFI, HOOD, TSLA, NVDA, AMD, CELH")

if st.button("🚀 Start Deep Market Scan"):
    # Define tickers list from input
    tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    
    for ticker in tickers:
        with st.container():
            try:
                stock = yf.Ticker(ticker)
                
                # STEP 1: Get History (More reliable than .info)
                df = stock.history(period="1y")
                if df.empty or len(df) < 130:
                    continue
                
                # STEP 2: Market Cap Check (Fail-safe)
                try:
                    info = stock.info
                    mkt_cap = info.get('marketCap', 0)
                except:
                    mkt_cap = 0 # Default to 0 if Yahoo blocks the info request
                
                # Apply the $300M Filter if data is available
                if mkt_cap > 0 and mkt_cap < (min_cap_m * 1_000_000):
                    st.write(f"⏭️ Skipping {ticker}: Market Cap too low (${mkt_cap/1_000_000:.1f}M)")
                    continue

                # STEP 3: Run Analysis
                price, max_vol, is_match, days_ago = analyze_with_volume_lookback(df)
                
                # STEP 4: Apply Volume Filter
                if max_vol < vol_threshold:
                    continue
                
                # STEP 5: Display Results
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    st.subheader(ticker)
                    st.metric("Price", f"${price:.2f}")
                    if mkt_cap > 0:
                        st.write(f"Cap: **${mkt_cap/1_000_000:.0f}M**")
                    else:
                        st.write("Cap: *Data Hidden*")
                
                with col2:
                    spike_text = "today" if days_ago == 0 else f"{days_ago} days ago"
                    st.write(f"📊 **Max RVOL (10d):** {max_vol:.2f}x (Spiked {spike_text})")
                    
                    if is_match:
                        st.success("🎯 STRATEGY MATCH: STAIRCASE + BREAKOUT")
                        # Trigger AI if key is present
                        if 'client' in globals():
                            prompt = f"Analyze {ticker} (${price}). It has a 10-day volume spike of {max_vol}x. In 2 sentences: Is this a Graham 'Value' play or a high-risk trend?"
                            ai_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                            st.info(ai_res.choices[0].message.content)
                    else:
                        st.warning("Significant volume found, but technical pattern is incomplete.")
                
                with col3:
                    if st.checkbox("View Chart", key=f"chart_{ticker}"):
                        st.line_chart(df['Close'].tail(60))
                
                st.divider()
                time.sleep(1.2) # Delay to stay safe from Yahoo's ban-bot
                
            except Exception as e:
                st.error(f"Error scanning {ticker}. Yahoo might be busy.")
                time.sleep(2)
