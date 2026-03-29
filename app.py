import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests
from openai import OpenAI

# --- 1. PAGE CONFIG & AI SETUP ---
st.set_page_config(layout="wide", page_title="Total Market Footprint Scanner")

# Initialize AI if Key is in Secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.sidebar.warning("⚠️ AI Analysis Disabled (No API Key found in Secrets)")

# --- 2. DATA UTILITIES ---
@st.cache_data(ttl=86400)
def get_total_us_universe():
    """Fetches every ticker currently listed on NASDAQ, NYSE, and AMEX."""
    try:
        # Fetching a comprehensive list of US tickers
        url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
        response = requests.get(url)
        tickers = [t.strip().upper() for t in response.text.splitlines() if t.strip()]
        return tickers
    except Exception:
        return ["AAPL", "TSLA", "NVDA", "PLTR", "SOFI", "AMD", "META"]

def analyze_logic(df):
    """Calculates the Staircase Breakout and 10-Day Max Relative Volume."""
    close = df['Close']
    volume = df['Volume']
    curr_p = float(close.iloc[-1])
    
    # Technical: 6-Month High & Staircase
    high_6m = float(close.iloc[-126:-1].max())
    recent = df.tail(20)
    h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
    h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
    
    is_breakout = curr_p > high_6m
    is_staircase = (h2 > h1) and (l2 > l1)
    
    # Volume: 10-Day Max RVOL
    rvol_list = []
    for i in range(1, 11):
        target_vol = volume.iloc[-i]
        hist_avg = volume.iloc[-(i+21):-i].mean()
        rvol_list.append(target_vol / hist_avg if hist_avg > 0 else 0)
    
    max_rvol = max(rvol_list)
    days_ago = rvol_list.index(max_rvol)
    
    return curr_p, max_rvol, (is_breakout and is_staircase), days_ago

# --- 3. SIDEBAR (The Filters) ---
st.sidebar.title("🛡️ Funnel Controls")
min_cap_m = st.sidebar.number_input("Min Market Cap ($Millions)", value=300)
vol_req = st.sidebar.slider("Min RVOL Surge (10-Day Max)", 1.0, 5.0, 2.0)
st.sidebar.info("The scanner checks the Entire US Market. This takes time due to Yahoo Finance rate limits.")

# --- 4. MAIN INTERFACE ---
st.title("🌪️ Total US Market Institutional Funnel")
st.write(f"Scanning for breakouts with a **${min_cap_m}M** floor and **{vol_req}x** volume surge.")

if st.button("🔭 Launch Global Search"):
    universe = get_total_us_universe()
    
    # Real-Time Funnel Statistics
    st.subheader("📊 Live Funnel Statistics")
    stat1, stat2, stat3, stat4 = st.columns(4)
    w_total = stat1.empty()
    w_cap = stat2.empty()
    w_vol = stat3.empty()
    w_match = stat4.empty()
    
    prog_bar = st.progress(0)
    status_msg = st.empty()
    
    # Counters
    c_scanned = 0
    c_skipped_cap = 0
    c_skipped_vol = 0
    c_matches = 0

    results_container = st.container()

    for idx, ticker in enumerate(universe):
        c_scanned += 1
        prog_bar.progress((idx + 1) / len(universe))
        
        # Update Widgets
        w_total.metric("Total Universe", c_scanned)
        w_cap.metric("Skipped (Low Cap)", c_skipped_cap)
        w_vol.metric("Skipped (Low Vol)", c_skipped_vol)
        w_match.metric("Watchlist Hits", c_matches)
        
        try:
            stock = yf.Ticker(ticker)
            
            # STAGE 1: Fast Market Cap Check
            info = stock.info
            m_cap = info.get('marketCap', 0)
            
            if m_cap != 0 and m_cap < (min_cap_m * 1_000_000):
                c_skipped_cap += 1
                continue

            # STAGE 2: History & Pattern Scan
            df = stock.history(period="1y")
            if df.empty or len(df) < 130:
                continue
            
            price, rvol, is_match, days_ago = analyze_logic(df)
            
            # STAGE 3: Volume Surge Check
            if rvol < vol_req:
                c_skipped_vol += 1
                continue
            
            # STAGE 4: Display The "Finalists"
            c_matches += 1
            with results_container:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.subheader(ticker)
                    st.metric("Price", f"${price:.2f}")
                    if m_cap > 0:
                        st.caption(f"Cap: ${m_cap/1_000_000:.0f}M")
                
                with col2:
                    spike_txt = "Today" if days_ago == 0 else f"{days_ago} days ago"
                    st.write(f"📈 **Max RVOL (10d):** {rvol:.2f}x (Spiked {spike_txt})")
                    
                    if is_match:
                        st.success("🎯 STAIRCASE CONFIRMED")
                        # Optional AI Analysis
                        if 'client' in globals():
                            try:
                                prompt = f"Analyze {ticker} at ${price}. 10-day vol spike is {rvol}x. Brief 2-sentence summary: Value or Hype?"
                                res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                                st.info(f"🤖 AI Analyst: {res.choices[0].message.content}")
                            except:
                                pass
                    else:
                        st.warning("Volume present, but technical pattern still forming.")
                
                with col3:
                    with st.expander("View Chart"):
                        st.line_chart(df['Close'].tail(60))
                st.divider()
            
            # Essential delay to prevent IP Ban from Yahoo
            time.sleep(1.1)

        except Exception:
            continue

    status_msg.success(f"✅ Scan Complete. Found {c_matches} high-conviction setups.")
