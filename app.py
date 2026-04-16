import streamlit as st
import pandas as pd
import yfinance as yf
from fpdf import FPDF
import datetime
from google import genai

# --- PDF GENERATOR CLASS ---
class StockReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Institutional Deep-Dive Analysis', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, label, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

# --- AI DEEP DIVE FUNCTION ---
def run_deep_analysis(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Gathering Fundamental Context
    fundamentals = {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "Debt-to-Equity": info.get("debtToEquity", "N/A"),
        "Free Cash Flow": info.get("freeCashflow", "N/A"),
        "Profit Margins": info.get("profitMargins", "N/A"),
        "Dividend Yield": info.get("dividendYield", "N/A")
    }
    
    prompt = f"""
    Perform a CFO-level deep dive on {ticker}. 
    FUNDAMENTALS: {fundamentals}
    
    Analyze:
    1. Financial Health: Is the balance sheet strong enough for a multi-bagger run?
    2. Entry Timing: Based on the 180-day breakout, is the current price an 'Entry Zone' or 'Overextended'?
    3. Risks: What could kill this thesis in 2026?
    4. Final Verdict: Immediate Buy, Wait for Pullback, or Avoid.
    """
    
    try:
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return response.text, fundamentals
    except:
        return "Analysis failed. Model busy.", fundamentals

# --- UI LAYOUT ---
st.title("🏹 Deep Intelligence Dashboard")

# Select a stock from your existing shortlist
if 'df_filtered' in locals() or 'df' in locals():
    target_ticker = st.selectbox("Select Ticker for Deep Dive", df_filtered['Ticker'].unique())

    if st.button(f"Generate PDF Report for {target_ticker}"):
        with st.status("Analyzing fundamentals & generating PDF...", expanded=True):
            report_text, metrics = run_deep_analysis(target_ticker)
            
            # Create PDF
            pdf = StockReport()
            pdf.add_page()
            pdf.chapter_title(f"Stock: {target_ticker} - Analysis Date: {datetime.date.today()}")
            
            # Add Key Metrics Table to PDF
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 10, "Key Fundamental Metrics:", 0, 1)
            for k, v in metrics.items():
                pdf.set_font('Arial', '', 10)
                pdf.cell(0, 7, f"{k}: {v}", 0, 1)
            
            pdf.ln(5)
            pdf.chapter_title("AI Strategic Verdict")
            pdf.chapter_body(report_text)
            
            # Binary output for download
            pdf_output = pdf.output(dest='S').encode('latin-1')
            
        st.success("Analysis Complete!")
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_output,
            file_name=f"{target_ticker}_DeepDive_{datetime.date.today()}.pdf",
            mime="application/pdf"
        )
        st.markdown(report_text)
