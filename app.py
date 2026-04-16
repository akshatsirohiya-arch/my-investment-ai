import streamlit as st
import pandas as pd
import yfinance as yf
import os
import datetime
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Institutional AI Hunter 2026")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # In April 2026, Gemini 3.1 Pro requires the v1beta endpoint
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

# --- 2. LOGIC FUNCTIONS ---

def get_high_conviction_summary(df):
    """Comparative research across the entire watchlist."""
    if not client: return "AI Client not initialized."
    
    csv_context = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].head(30).to_csv(index=False)
    
    prompt = f"""
    Act as a Senior Hedge Fund Portfolio Manager. 
    Analyze this 180-day breakout watchlist: {csv_context}
    
    1. Identify the 'Top 5' high-conviction candidates for the 2026 macro cycle.
    2. Which sectors are showing true institutional accumulation?
    3. Call out 'Value Traps'—stocks that look fast but have poor technical foundations.
    Return a professional, high-density research report.
    """
    
    try:
        # gemini-3.1-pro-preview is the current flagship for reasoning
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"AI Research currently unavailable: {str(e)}"

def run_deep_audit(ticker):
    """Detailed audit of one ticker: Fundamentals, Moat, and Entry zones."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Gathering critical 2026 data points
        audit_data = {
            "Rev Growth": info.get("revenueGrowth"),
            "Margins": info.get("profitMargins"),
            "Debt/Equity": info.get("debtToEquity"),
            "Free Cash Flow": info.get("freeCashflow"),
            "Short Ratio": info.get("shortRatio")
        }
        
        prompt = f"""
        Perform a Deep Audit on {ticker} for a multi-bagger thesis.
        METRICS: {audit_data}
        
        1. THE MOAT: What is their competitive advantage in the 2026 economy?
        2. FINANCIAL HEALTH: Critique their cash flow and debt. Is there a bankruptcy or dilution risk?
        3. RED FLAGS: Analyze short interest and recent news sentiment.
        4. VERDICT & ENTRY: Provide a specific price-action strategy (Entry zones and Stop-losses).
        """
        
        response = client.models.generate_content(model="gemini-3.1-pro-preview", contents=prompt)
        return response.text, audit_data
    except Exception as e:
        return f"Audit Error: {str(e)}", {}

# --- 3. MAIN APP UI ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
    df = df.sort_values(by="Velocity %", ascending=False)
    
    st.title("🏹 Multi-Bagger Intelligence Dashboard")
    
    # --- TOP: STRATEGIC SUMMARY ---
    with st.expander("🌍 GLOBAL SECTOR & CONVICTION SUMMARY", expanded=True):
        if st.button("🚀 Run Institutional Research"):
            with st.status("Analyzing entire watchlist using Gemini 3.1 Pro..."):
                st.markdown(get_high_conviction_summary(df))
    
    st.markdown("---")
    
    # --- MIDDLE: THE DEEP DIVE ---
    st.header("🔬 Deep-Dive Individual Audit")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        target = st.selectbox("Select Ticker", df['Ticker'].unique())
        if st.button(f"🔍 Audit {target}"):
            with st.status(f"Auditing {target} Fundamentals..."):
                report, metrics = run_deep_audit(target)
                st.session_state['audit_report'] = report
                st.session_state['audit_metrics'] = metrics
    
    with col2:
        if 'audit_report' in st.session_state:
            m = st.session_state['audit_metrics']
            c = st.columns(3)
            c[0].metric("Rev Growth", f"{m.get('Rev Growth', 0)*100:.1f}%")
            c[1].metric("Net Margin", f"{m.get('Margins', 0)*100:.1f}%")
            c[2].metric("Debt/Equity", m.get('Debt/Equity', 'N/A'))
            
            st.markdown(st.session_state['audit_report'])

    st.markdown("---")

    # --- BOTTOM: THE LIST ---
    st.header("📊 Full Watchlist Data")
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Velocity %": st.column_config.NumberColumn("Velocity %", format="%.0f%%"),
            "RVOL": st.column_config.NumberColumn("Rel Vol", format="%.2fx"),
            "High_180d": None, "Slope": None 
        },
        hide_index=True
    )
else:
    st.error("daily_watchlist.csv not found.")
