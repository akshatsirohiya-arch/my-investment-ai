import streamlit as st
import yfinance as yf
import pandas as pd
import time
from openai import OpenAI

# 1. PAGE SETUP
st.set_page_config(layout="wide", page_title="Institutional Footprint Scanner")

# 2. API KEY SETUP
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.sidebar.warning("⚠️ OpenAI Key not found in Secrets. AI Analysis will be skipped.")

# 3. CORE CALCULATION ENGINE
def analyze_with_volume_lookback(df):
    close = df['Close']
    volume = df['Volume']
    curr_p = float(close.iloc[-1])
    
    # 6-Month High & Staircase
    high_6m = float(close.iloc[-126:-1].max())
    recent = df.tail(20)
    h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
    h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
    
    is_breakout = curr_p > high_6m
    is_staircase = (h2 > h1) and (l2 > l1)
    
    # 10-Day Max RVOL
    rvol_list = []
    for i in range(1, 11):
        target_vol = volume.iloc[-i]
        hist_avg = volume.iloc[-(i+21):-i].mean()
        day_rvol = target_vol / hist_avg if hist_avg > 0 else 0
        rvol_list.append(day_rvol)
    
    max_rvol_10d = max(rvol_list)
    days_ago = rvol_list.index(max_rvol_10d) 
    
    return curr_p, max_rvol_10d, (is_breakout and is_staircase), days_ago

# 4. SIDEBAR
st.sidebar.title("🛡️ Risk & Quality Filters")
min_cap_m = st.sidebar.number_input("Min Market Cap ($Millions)", value=300)
vol_threshold = st.sidebar.slider("Min 'Footprint' RVOL (10-Day Max)", 1.0, 5.0, 2.0)
show_all_charts = st.sidebar.checkbox("Show all charts by default", value=False)

# 5. MAIN INTERFACE
st.title("🚀 The $300M+ Footprint Scanner")

user_input = st.text_input("Watchlist", "PLTR, SOFI, HOOD, TSLA, NVDA, AMD, CELH")
tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

if st.button("🔍 Run Deep Scan"):
    # We use a placeholder so the UI stays put
    results_area = st.container()
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            
            if df.empty or len(df) < 130:
                continue
            
            # Market Cap Check
            try:
                info = stock.info
                mkt_cap = info.get('marketCap', 0)
            except:
                mkt_cap = 0
            
            if mkt_cap > 0 and mkt_cap < (min_cap_m * 1_000_000):
                continue

            price, max_vol, is_match, days_ago = analyze_with_volume_lookback(df)
            
            if max_vol < vol_threshold:
                continue
                
            with results_area:
                # HEADER ROW
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.markdown(f"### {ticker}")
                    st.metric("Price", f"${price:.2f}")
                
                with c2:
                    spike_text = "today" if days_ago == 0 else f"{days_ago} days ago"
                    st.write(f"📊 **Max RVOL (10d):** {max_vol:.2f}x (Spiked {spike_text})")
                    if is_match:
                        st.success("🎯 MATCH: STAIRCASE + BREAKOUT")
                    else:
                        st.info("High Volume detected. Pattern still forming.")
                
                with c3:
                    # AI logic (only if match found to save credits)
                    if is_match and 'client' in globals():
                        try:
                            prompt = f"Analyze {ticker} (${price}). 10-day volume spike is {max_vol}x. Value play or risky trend? 2 sentences."
                            ai_res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
                            st.caption(ai_res.choices[0].message.content)
                        except:
                            st.caption("AI Analysis unavailable.")

                # CHART AREA (Fixed the 'getting stuck' issue)
                # If 'Show all charts' is off, we use an expander which is much more stable than a checkbox
                if show_all_charts:
                    st.line_chart(df['Close'].tail(60))
                else:
                    with st.expander(f"📈 View {ticker} Chart"):
                        st.line_chart(df['Close'].tail(60))
                
                st.divider()
                time.sleep(1)
                
        except Exception as e:
            st.error(f"Error scanning {ticker}")
