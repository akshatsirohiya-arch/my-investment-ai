import streamlit as st
import pandas as pd
import yfinance as yf
import os
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Institutional AI Hunter")

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

# --- 2. ROBUST AI WRAPPER (Handles 429 Errors) ---

def call_gemini_with_retry(prompt, model_id="gemini-2.0-flash"):
    """Attempts to call AI with a retry backoff for rate limits."""
    if not client: return "AI Client not initialized."
    
    max_retries = 3
    for i in range(max_retries):
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                time.sleep(3) # Wait 3 seconds if rate limited
                continue
            return f"AI Error: {str(e)}"
    return "Rate limit exceeded. Please wait a minute and try again."

# --- 3. RESEARCH FUNCTIONS ---

def get_high_conviction_summary(df):
    # Only send Top 15 to stay within Free Tier token limits
    csv_context = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].head(15).to_csv(index=False)
    prompt = f"Act as a Hedge Fund Manager. Analyze these breakouts: {csv_context}. Identify Top 5 multi-bagger candidates and their 2026 catalysts."
    return call_gemini_with_retry(prompt)

def run_deep_audit(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        audit_data = {
            "Rev Growth": info.get("revenueGrowth"),
            "Debt/Equity": info.get("debtToEquity"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Short Ratio": info.get("shortRatio")
        }
        prompt = f"Perform a Deep Fundamental Audit on {ticker}. DATA: {audit_data}. Analyze Moat, Financial Health, and specific Entry/Exit zones for 2026."
        return call_gemini_with_retry(prompt), audit_data
    except Exception as e:
        return f"Audit Error: {str(e)}", {}

# --- 4. MAIN APP UI ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
    df = df.sort_values(by="Velocity %", ascending=False)
    
    st.title("🏹 Multi-Bagger Intelligence")
    
    # --- TOP: STRATEGIC SUMMARY ---
    with st.expander("🌍 GLOBAL SECTOR SUMMARY", expanded=True):
        if st.button("🚀 Run Institutional Research"):
            with st.spinner("Analyzing with Gemini Flash (High Speed)..."):
                st.markdown(get_high_conviction_summary(df))
    
    st.markdown("---")
    
    # --- MIDDLE: THE DEEP DIVE ---
    st.header("🔬 Deep-Dive Individual Audit")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        target = st.selectbox("Select Ticker", df['Ticker'].unique())
        if st.button(f"🔍 Audit {target}"):
            report, metrics = run_deep_audit(target)
            st.session_state['audit_report'] = report
            st.session_state['audit_metrics'] = metrics
    
    with col2:
        if 'audit_report' in st.session_state:
            m = st.session_state['audit_metrics']
            c = st.columns(3)
            c[0].metric("Rev Growth", f"{m.get('Rev Growth', 0)*100:.1f}%" if m.get('Rev Growth') else "N/A")
            c[1].metric("Debt/Equity", m.get('Debt/Equity', 'N/A'))
            c[2].metric("Short Ratio", m.get('Short Ratio', 'N/A'))
            st.markdown(st.session_state['audit_report'])

    st.markdown("---")

    # --- BOTTOM: DATA TABLE ---
    st.header("📊 Full Watchlist Data")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.error("daily_watchlist.csv not found.")
