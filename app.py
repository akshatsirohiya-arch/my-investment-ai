import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Momentum Command Center")

if "GEMINI_API_KEY" in st.secrets:
    try:
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1beta'} 
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Missing GEMINI_API_KEY.")
    client = None

# --- 2. CORE UTILITIES ---

def call_gemini_with_retry(prompt, model_id="gemini-2.0-flash"):
    if not client: return "AI Client not initialized."
    # Reduced retries to avoid getting stuck in a loop during quota lockout
    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "QUOTA_LIMIT: You've hit the limit. Wait 60 seconds before trying again."
        return f"AI Error: {str(e)}"

@st.cache_data(ttl=86400)
def get_industry_metadata(ticker):
    try:
        time.sleep(0.1)
        return yf.Ticker(ticker).info.get('industry', 'N/A')
    except:
        return "N/A"

# --- 3. MAIN UI LAYOUT ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
    df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
    
    st.title("🏹 Institutional Intelligence")

    # SIDEBAR FILTERS
    st.sidebar.header("🎯 Quality Filters")
    min_rvol = st.sidebar.slider("Min RVOL", 0.0, 10.0, 1.2)
    min_vel = st.sidebar.slider("Min Velocity %", 0, 500, 30)
    
    df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
    df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

    # --- SECTION 1: PERSISTENT BATCH ANALYSIS ---
    st.header("🌍 Global Sector Analysis")
    
    # Check if we already have an analysis saved in memory
    if 'global_report' not in st.session_state:
        st.session_state['global_report'] = None

    if st.button("🚀 Run AI Research"):
        with st.spinner("Analyzing top 15 breakouts..."):
            csv_context = df_filtered[['Ticker', 'Price', 'Velocity %', 'RVOL']].head(15).to_csv(index=False)
            prompt = f"Analyze these 180-day breakouts for 2026 multi-bagger potential: {csv_context}"
            # Save to session state so it survives refreshes
            st.session_state['global_report'] = call_gemini_with_retry(prompt)

    # Display the report if it exists in memory
    if st.session_state['global_report']:
        st.info("Showing saved analysis. Click 'Run' again only if data changes.")
        st.markdown(st.session_state['global_report'])
        if st.button("Clear Saved Analysis"):
            st.session_state['global_report'] = None
            st.rerun()

    st.markdown("---")
    
    # --- SECTION 2: PERSISTENT INDIVIDUAL AUDIT ---
    st.header("🔬 Individual Fundamental Audit")
    target = st.selectbox("Select Ticker", df_filtered['Ticker'].unique())
    
    # Initialize session state for audit
    if 'audit_cache' not in st.session_state:
        st.session_state['audit_cache'] = {}

    if st.button(f"🔍 Audit {target}"):
        with st.spinner(f"Auditing {target}..."):
            stock = yf.Ticker(target)
            info = stock.info
            metrics = {
                "Rev Growth": info.get("revenueGrowth"),
                "Debt/Equity": info.get("debtToEquity"),
                "Margins": info.get("profitMargins")
            }
            prompt = f"Audit {target} fundamentals for a multi-bagger thesis. DATA: {metrics}"
            report = call_gemini_with_retry(prompt)
            # Store in a dictionary with ticker as key
            st.session_state['audit_cache'][target] = {"report": report, "metrics": metrics}

    # Display from cache if available
    if target in st.session_state['audit_cache']:
        data = st.session_state['audit_cache'][target]
        m = data['metrics']
        c = st.columns(3)
        c[0].metric("Rev Growth", f"{m.get('Rev Growth', 0)*100:.1f}%" if m.get('Rev Growth') else "N/A")
        c[1].metric("Net Margin", f"{m.get('Margins', 0)*100:.1f}%" if m.get('Margins') else "N/A")
        c[2].metric("Debt/Equity", m.get('Debt/Equity', 'N/A'))
        st.markdown(data['report'])

    st.markdown("---")

    # --- SECTION 3: THE DATA TABLE ---
    st.header(f"📊 Watchlist ({len(df_filtered)} Stocks)")
    if st.checkbox("🔍 Load Industry Data"):
        with st.spinner("Classifying..."):
            df_filtered['Industry'] = df_filtered['Ticker'].apply(get_industry_metadata)

    st.dataframe(
        df_filtered,
        use_container_width=True,
        column_config={
            "Chart 📈": st.column_config.LinkColumn("Chart", display_text="View Chart"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
            "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
            "High_180d": None, "Slope": None 
        },
        hide_index=True
    )
else:
    st.error("Missing 'daily_watchlist.csv'.")
