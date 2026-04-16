import streamlit as st
import pandas as pd
import yfinance as yf
from fpdf import FPDF
import datetime
import os
import time
from google import genai

# --- 1. SETTINGS & CLIENT INIT ---
st.set_page_config(layout="wide", page_title="Institutional AI Hunter 2026")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # 2026 Fix: Gemini 3 models require the v1beta endpoint for preview access
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options={'api_version': 'v1beta'} 
        )
    except Exception as e:
        st.sidebar.error(f"Client Init Error: {e}")
        client = None
else:
    st.sidebar.warning("🔑 Missing GEMINI_API_KEY in Streamlit Secrets.")
    client = None

# --- 2. PDF GENERATOR CLASS ---
class StockReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'EQUITY DEEP-DIVE REPORT', 0, 1, 'C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, f'Generated on: {datetime.date.today()}', 0, 1, 'C')
        self.ln(10)

    def section_title(self, label):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, label, 0, 1, 'L', True)
        self.ln(4)

    def write_body(self, text):
        self.set_font('helvetica', '', 10)
        # Using multi_cell to handle long AI responses
        self.multi_cell(0, 6, text)
        self.ln()

# --- 3. LOGIC FUNCTIONS ---

def get_batch_summary(df):
    """Summarizes the top movers for the dashboard."""
    csv_context = df[['Ticker', 'Price', 'Velocity %', 'RVOL']].to_csv(index=False)
    prompt = f"Analyze these 180-day breakouts: {csv_context}. Pick top 3 for 2026 and why."
    try:
        response = client.models.generate_content(model="gemini-3.1-flash-preview", contents=prompt)
        return response.text
    except: return "AI Summary currently unavailable."

def run_deep_analysis(ticker):
    """Fetches fundamentals and runs a CFO-level AI analysis."""
    stock = yf.Ticker(ticker)
    info = stock.info
    
    metrics = {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "Debt/Equity": info.get("debtToEquity", "N/A"),
        "Margins": info.get("profitMargins", "N/A"),
        "Beta": info.get("beta", "N/A"),
        "Cash": info.get("totalCash", "N/A")
    }
    
    prompt = f"""
    Act as a Hedge Fund Manager. Perform a Deep Dive on {ticker}.
    DATA: {metrics}
    1. Entry Zone: Is the current 180-day breakout a 'Buy' or 'Overextended'?
    2. Fundamentals: Is the balance sheet multi-bagger quality?
    3. Sentiment: What is the 2026 outlook for this sector?
    4. Verdict: Enter Now, Wait for Pullback, or Avoid.
    """
    
    try:
        response = client.models.generate_content(model="gemini-3.1-pro-preview", contents=prompt)
        return response.text, metrics
    except Exception as e:
        return f"Deep Analysis Error: {str(e)}", metrics

# --- 4. MAIN APP UI ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    df['Velocity %'] = (df['Slope'] / df['Price']) * 252 * 100
    df = df.sort_values(by="Velocity %", ascending=False)
    
    # Sidebar Filters
    st.sidebar.header("🎯 Filters")
    min_rvol = st.sidebar.slider("Min RVOL", 0.0, 5.0, 0.0)
    df_filtered = df[df['RVOL'] >= min_rvol].copy()

    # HEADER SECTION: AI STRATEGIC SUMMARY
    st.title("🏹 AI Multi-Bagger Command Center")
    
    with st.expander("🤖 TODAY'S MARKET INTELLIGENCE", expanded=True):
        if st.button("Generate Strategic Summary"):
            st.write(get_batch_summary(df_filtered.head(20)))
        else:
            st.info("Click above to summarize the current watchlist.")

    st.markdown("---")

    # MID SECTION: DEEP DIVE & PDF
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🕵️ Deep Analysis")
        target = st.selectbox("Pick a stock to audit:", df_filtered['Ticker'].unique())
        
        if st.button(f"Generate PDF for {target}"):
            with st.status("Reviewing Fundamentals...", expanded=True):
                report_text, data = run_deep_analysis(target)
                
                # Build PDF
                pdf = StockReport()
                pdf.add_page()
                pdf.section_title(f"TECHNICAL & FUNDAMENTAL AUDIT: {target}")
                
                # Add Metrics
                pdf.set_font('helvetica', 'B', 10)
                for k, v in data.items():
                    pdf.cell(50, 8, f"{k}:", 1)
                    pdf.cell(0, 8, f" {v}", 1, 1)
                
                pdf.ln(10)
                pdf.section_title("AI VERDICT & STRATEGY")
                # Clean text for PDF encoding
                pdf.write_body(report_text.encode('latin-1', 'replace').decode('latin-1'))
                
                pdf_bytes = pdf.output() # In fpdf2, output() returns bytes by default
                
            st.download_button(
                label=f"📥 Download {target} Report",
                data=pdf_bytes,
                file_name=f"{target}_Audit_{datetime.date.today()}.pdf",
                mime="application/pdf"
            )
            st.success("Report Ready!")

    with col2:
        st.subheader("📊 Live Watchlist View")
        st.dataframe(
            df_filtered,
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
    st.error("daily_watchlist.csv not found. Check your 6AM scanner.")
