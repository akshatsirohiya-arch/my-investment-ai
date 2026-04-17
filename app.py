import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Institutional Momentum Command Center")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # v1beta is necessary for the latest 2026 models
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
    """Handles 429 rate limits automatically."""
    if not client: return "AI Client not initialized."
    for _ in range(3):
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                time.sleep(3)
                continue
            return f"AI Error: {str(e)}"
    return "Rate limit reached. Try again in a moment."

@st.cache_data(ttl=86400)
def get_industry_metadata(ticker):
    """Fetches industry/sector data from yfinance (cached)."""
    try:
        time.sleep(0.1)
        info = yf.Ticker(ticker).info
        return info.get('industry', 'N/A')
    except:
        return "N/A"

# --- 3. RESEARCH LOGIC ---

def get_high_conviction_summary(df):
    csv_context = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].head(15).to_csv(index=False)
    prompt = f"""
    Act as a Hedge Fund Strategist. Analyze these 180-day breakouts:
    {csv_context}
    
    1. Identify 'Top 5' potential multi-baggers for 2026.
    2. Which macro sectors are leading this list?
    3. Call out any suspicious outliers (high price/low volume).
    """
    return call_gemini_with_retry(prompt)

def run_deep_audit(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        audit_data = {
            "Rev Growth": info.get("revenueGrowth"),
            "Debt/Equity": info.get("debtToEquity"),
            "Margins": info.get("profitMargins"),
            "Short Ratio": info.get("shortRatio")
        }
        prompt = f"Perform a Deep Fundamental Audit on {ticker}. DATA: {audit_data}. Analyze Moat, Red Flags, and 2026 Entry Strategy."
        return call_gemini_with_retry(prompt), audit_data
    except Exception as e:
        return f"Audit Error: {str(e)}", {}

# --- 4. MAIN UI LAYOUT ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    # Pre-processing
    df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
    df['Chart 📈'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
    
    st.title("🏹 Institutional Multi-Bagger Intelligence")

    # --- SIDEBAR FILTERS (RESTORED) ---
    st.sidebar.header("🎯 Quality Filters")
    min_rvol = st.sidebar.slider("Min Relative Volume (RVOL)", 0.0, 10.0, 1.2)
    min_vel = st.sidebar.slider("Min Velocity % (Annualized)", 0, 500, 30)
    
    df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Velocity %'] >= min_vel)].copy()
    df_filtered = df_filtered.sort_values(by="Velocity %", ascending=False)

    # --- TOP: GLOBAL STRATEGY ---
    with st.expander("🌍 GLOBAL SECTOR & CONVICTION SUMMARY", expanded=True):
        if st.button("🚀 Run Institutional Research"):
            with st.spinner("Analyzing current watchlist..."):
                st.markdown(get_high_conviction_summary(df_filtered))
    
    st.markdown("---")
    
    # --- MIDDLE: INDIVIDUAL AUDIT ---
    st.header("🔬 Individual Fundamental Audit")
    col_a, col_b = st.columns([1, 3])
    
    with col_a:
        target = st.selectbox("Select Ticker for Audit", df_filtered['Ticker'].unique())
        run_audit = st.button("🔍 Run Full Audit")
    
    with col_b:
        if run_audit:
            report, metrics = run_deep_audit(target)
            st.session_state['report'] = report
            st.session_state['metrics'] = metrics
            
        if 'report' in st.session_state:
            m = st.session_state['metrics']
            c = st.columns(3)
            c[0].metric("Rev Growth", f"{m.get('Rev Growth', 0)*100:.1f}%" if m.get('Rev Growth') else "N/A")
            c[1].metric("Net Margin", f"{m.get('Margins', 0)*100:.1f}%" if m.get('Margins') else "N/A")
            c[2].metric("Debt/Equity", m.get('Debt/Equity', 'N/A'))
            st.markdown(st.session_state['report'])

    st.markdown("---")

    # --- BOTTOM: THE DATA TABLE (RESTORED) ---
    st.header(f"📊 Momentum Watchlist ({len(df_filtered)} Stocks)")
    
    # Add Industry Data
    if st.checkbox("🔍 Load Industry/Sector Data"):
        with st.spinner("Classifying..."):
            df_filtered['Industry'] = df_filtered['Ticker'].apply(get_industry_metadata)

    st.dataframe(
        df_filtered,
        use_container_width=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Industry": st.column_config.TextColumn("Industry"),
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
