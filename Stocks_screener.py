import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import io

# --- Configuration ---
st.set_page_config(page_title="Fundamental Terminal", layout="wide")
st.title("📈 Fundamental Terminal")
st.markdown("Live Screener & Visual Analyzer for Indian Equities")

# --- Function to fetch Live Index Data from the Internet ---
@st.cache_data(ttl=86400) # Caches the list for 24 hours
def get_nse_tickers(index_name):
    # Official NSE archive URLs for major indices
    urls = {
        "Nifty 50": "ind_nifty50list.csv",
        "Nifty Next 50": "ind_niftynext50list.csv",
        "Nifty 100": "ind_nifty100list.csv",
        "Nifty 200": "ind_nifty200list.csv",
        "Nifty 500": "ind_nifty500list.csv",
        "Nifty Midcap 100": "ind_niftymidcap100list.csv",
        "Nifty Smallcap 100": "ind_niftysmallcap100list.csv",
        "Nifty Bank": "ind_niftybanklist.csv",
        "Nifty IT": "ind_niftyitlist.csv",
        "Nifty Pharma": "ind_niftypharmalist.csv",
        "Nifty FMCG": "ind_niftyfmcglist.csv",
        "Nifty Auto": "ind_niftyautolist.csv",
        "Nifty Metal": "ind_niftymetallist.csv",
        "Nifty Energy": "ind_niftyenergylist.csv"
    }
    
    base_url = "https://archives.nseindia.com/content/indices/"
    url = base_url + urls.get(index_name)
    
    try:
        # Disguise request to prevent NSE from blocking the download
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers, timeout=10)
        
        # Read the raw internet text directly into a Pandas dataframe
        df = pd.read_csv(io.StringIO(response.text))
        
        # Extract the 'Symbol' column and append '.NS' for Yahoo Finance
        tickers = df['Symbol'].astype(str) + ".NS"
        return tickers.tolist()
        
    except Exception as e:
        st.error("Failed to connect to NSE servers. Using fallback list.")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS"]

# --- Sidebar UI: Define Peer Group ---
st.sidebar.header("1. Define Sector / Universe")
# Updated selection box with all the new indices
index_keys = [
    "Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200", "Nifty 500", 
    "Nifty Midcap 100", "Nifty Smallcap 100", "Nifty Bank", "Nifty IT", 
    "Nifty Pharma", "Nifty FMCG", "Nifty Auto", "Nifty Metal", "Nifty Energy"
]
index_choice = st.sidebar.selectbox("Fetch stocks from:", index_keys)

universe_tickers = get_nse_tickers(index_choice)
tickers = st.sidebar.multiselect("Selected Stocks:", universe_tickers, default=universe_tickers)

# --- Sidebar UI: The Live Screener Filters ---
st.sidebar.header("2. Healthy Business Criteria")
min_roe = st.sidebar.slider("Minimum ROE (%)", 0, 40, 15)
max_de = st.sidebar.slider("Maximum Debt-to-Equity", 0.0, 3.0, 1.0)
max_pe = st.sidebar.slider("Maximum P/E Ratio", 0, 150, 25)

# --- Fetch Financials from Yahoo Finance ---
@st.cache_data(ttl=3600) 
def fetch_financials(ticker_list):
    data = []
    for t in ticker_list:
        try:
            stock = yf.Ticker(t)
            info = stock.info
            
            pe = info.get("trailingPE", None)
            roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None
            de = info.get("debtToEquity", None)
            if de is not None: de = de / 100 
            
            data.append({
                "Company": t.replace(".NS", ""),
                "Price (₹)": info.get("currentPrice", None),
                "P/E (TTM)": round(pe, 2) if pe else None,
                "ROE (%)": round(roe, 2) if roe else None,
                "Debt/Equity": round(de, 2) if de else None
            })
        except Exception:
            continue
    return pd.DataFrame(data).dropna()

# --- Create App Tabs ---
tab1, tab2 = st.tabs(["📊 The Terminal", "📖 Fundamentals Guide"])

# ==========================================
# TAB 1: THE TERMINAL LOGIC
# ==========================================
with tab1:
    if len(tickers) > 100:
        st.info("⚠️ **Large Universe Selected:** Pulling live fundamentals for 100+ stocks takes a few minutes. Please wait.")

    with st.spinner(f"Pulling live fundamentals for {len(tickers)} stocks..."):
        df = fetch_financials(tickers)

    if not df.empty:
        filtered_df = df[
            (df["ROE (%)"] >= min_roe) & 
            (df["Debt/Equity"] <= max_de) & 
            (df["P/E (TTM)"] <= max_pe)
        ]

        # Render: The Live Screener
        st.subheader(f"The Live Screener: {index_choice}")
        st.write(f"Showing **{len(filtered_df)}** fundamentally strong companies out of the {len(tickers)} peers selected:")
        st.dataframe(filtered_df.sort_values(by="ROE (%)", ascending=False), use_container_width=True)

        # Render: The Visual Analyzer
        st.divider()
        st.subheader("The Visual Analyzer: Relative Valuation")
        st.markdown("Comparing **P/E Ratio** vs **Return on Equity (ROE)** across your selected sector peers.")

        fig = px.scatter(
            df, x="P/E (TTM)", y="ROE (%)", text="Company", size="Price (₹)",
            color="Company", title="Sector Valuation Map (Top Left = Ideal, Lower Left = Cheap but low return)",
            labels={"P/E (TTM)": "Trailing P/E (Lower is Cheaper)", "ROE (%)": "Return on Equity (Higher is Better)"}
        )
        fig.update_traces(textposition='top center')
        fig.add_vline(x=max_pe, line_dash="dash", line_color="red", annotation_text="Max P/E Limit")
        fig.add_hline(y=min_roe, line_dash="dash", line_color="green", annotation_text="Min ROE Limit")
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No fundamental data found. The API might be temporarily rate-limited.")

# ==========================================
# TAB 2: EDUCATIONAL GUIDE
# ==========================================
with tab2:
    st.header("The 'Healthy Business' Checklist")
    st.write("Fundamental analysis is about buying pieces of excellent businesses at reasonable prices. Here is exactly what our screener filters for and why.")

    st.subheader("1. ROE (Return on Equity)")
    st.markdown("""
    * **What it means:** How much profit a company generates with the money shareholders have invested. (Net Income ÷ Shareholder's Equity).
    * **The Screener Target:** **> 15%**
    * **Why it matters:** A consistently high ROE proves that the company's management is highly efficient at using your money to grow the business. It is the ultimate measure of a "quality" business.
    """)

    st.subheader("2. Debt-to-Equity (D/E)")
    st.markdown("""
    * **What it means:** How much debt the company uses to finance its assets relative to the value of shareholders' equity. 
    * **The Screener Target:** **< 1.0** (Meaning they have less debt than equity).
    * **Why it matters:** High debt is dangerous during economic downturns because interest payments must be made regardless of profits. A low D/E ratio ensures the company can survive tough times without going bankrupt. *(Note: Banks naturally have high D/E ratios because taking deposits counts as debt, so skip this metric when analyzing the Bank Nifty).*
    """)

    st.subheader("3. P/E Ratio (Price-to-Earnings)")
    st.markdown("""
    * **What it means:** How much the market is willing to pay today for ₹1 of the company's earnings. (Stock Price ÷ Earnings Per Share).
    * **The Screener Target:** **< 25** (Or lower than its direct peers).
    * **Why it matters:** This is your **Valuation Check**. A great business is a terrible investment if you pay too much for it. A lower P/E *relative to its competitors* suggests the stock might be undervalued.
    """)

    st.divider()

    st.header("Important Concepts")
    st.markdown("""
    * **TTM (Trailing Twelve Months):** Financials are normally reported once a year. TTM adds up the *last four quarterly reports* to give you a rolling, real-time picture of the company's health today, rather than waiting for the annual report.
    * **Relative Valuation:** P/E ratios vary wildly by sector. A P/E of 30 might be cheap for an IT company but ridiculously expensive for a Metal company. You **must** compare a stock to its direct peers (e.g., compare TCS to Infosys, not to Tata Steel). This is why the Visual Analyzer chart in Tab 1 is so important!
    """)