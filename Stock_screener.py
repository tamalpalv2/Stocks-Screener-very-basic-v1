import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import io

# --- Configuration ---
st.set_page_config(page_title="Fundamental Terminal", layout="wide")
st.title("📈 Fundamental Terminal")
st.markdown("Live Screener & Peer Analyzer for Indian Equities")

# --- The Built-In Sector Database (For Tab 2) ---
SECTOR_DATABASE = {
    "IT & Software": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS", "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS"],
    "Banking & Finance": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "BAJFINANCE.NS", "CHOLAFIN.NS", "PNB.NS", "INDUSINDBK.NS"],
    "Pharmaceuticals": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "LUPIN.NS", "AUROPHARMA.NS", "BIOCON.NS", "TORNTPHARM.NS", "ALKEM.NS"],
    "FMCG (Consumer Goods)": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS", "GODREJCP.NS", "TATACONSUM.NS", "MARICO.NS", "COLPAL.NS"],
    "Automobile": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "TVSMOTOR.NS", "ASHOKLEY.NS"],
    "Energy, Oil & Gas": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS", "BPCL.NS", "TATAPOWER.NS", "IOC.NS", "GAIL.NS"],
    "Metals & Mining": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "NMDC.NS", "SAIL.NS", "JINDALSTEL.NS"],
    "Infrastructure & Cement": ["ULTRACEMCO.NS", "GRASIM.NS", "SHREECEM.NS", "AMBUJACEM.NS", "LT.NS", "DLF.NS", "ADANIPORTS.NS"]
}

# --- Function to fetch Live Index Data from NSE ---
@st.cache_data(ttl=86400) 
def get_nse_tickers(index_name):
    urls = {
        "Nifty 50": "ind_nifty50list.csv",
        "Nifty Next 50": "ind_niftynext50list.csv",
        "Nifty 100": "ind_nifty100list.csv",
        "Nifty 200": "ind_nifty200list.csv",
        "Nifty 500": "ind_nifty500list.csv",
        "Nifty Midcap 50": "ind_niftymidcap50list.csv",
        "Nifty Midcap 100": "ind_niftymidcap100list.csv",
        "Nifty Smallcap 100": "ind_niftysmallcap100list.csv",
        "Nifty Bank": "ind_niftybanklist.csv",
        "Nifty IT": "ind_niftyitlist.csv",
        "Nifty Pharma": "ind_niftypharmalist.csv",
        "Nifty FMCG": "ind_niftyfmcglist.csv",
        "Nifty Auto": "ind_niftyautolist.csv",
        "Nifty Metal": "ind_niftymetallist.csv",
        "Nifty Energy": "ind_niftyenergylist.csv",
        "Nifty Financial Services": "ind_niftyfinlist.csv"
    }
    
    base_url = "https://archives.nseindia.com/content/indices/"
    url = base_url + urls.get(index_name)
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers, timeout=10)
        
        df = pd.read_csv(io.StringIO(response.text))
        tickers = df['Symbol'].astype(str) + ".NS"
        return tickers.tolist()
        
    except Exception as e:
        st.error("⚠️ Failed to connect to NSE servers. Using a fallback list.")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS", "SUNPHARMA.NS"]

INDEX_OPTIONS = [
    "Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200", "Nifty 500", 
    "Nifty Midcap 50", "Nifty Midcap 100", "Nifty Smallcap 100", "Nifty Bank", 
    "Nifty IT", "Nifty Pharma", "Nifty FMCG", "Nifty Auto", "Nifty Metal", 
    "Nifty Energy", "Nifty Financial Services"
]

# --- Helper Function: Plot Normalized EPS ---
# By separating this out, we can reuse it for both indices and custom sectors
def render_eps_chart(selected_peers, chart_title):
    with st.spinner(f"Calculating Normalized EPS for {len(selected_peers)} companies..."):
        all_eps_data = []
        
        for company in selected_peers:
            ticker_symbol = f"{company}.NS" 
            stock_data = yf.Ticker(ticker_symbol)
            
            income_stmt = stock_data.income_stmt
            current_price = stock_data.info.get("currentPrice")
            
            if current_price and not income_stmt.empty and ('Diluted EPS' in income_stmt.index or 'Basic EPS' in income_stmt.index):
                eps_key = 'Diluted EPS' if 'Diluted EPS' in income_stmt.index else 'Basic EPS'
                eps_series = income_stmt.loc[eps_key]
                
                shares_per_1000 = 1000 / current_price
                
                for date, eps_val in eps_series.items():
                    normalized_earnings = eps_val * shares_per_1000
                    all_eps_data.append({
                        "Company": company,
                        "Year": pd.to_datetime(date).year,
                        "Earnings (₹) per ₹1000": round(normalized_earnings, 2)
                    })
        
        if all_eps_data:
            eps_df = pd.DataFrame(all_eps_data).sort_values(by="Year")
            
            eps_fig = px.line(
                eps_df, x="Year", y="Earnings (₹) per ₹1000", color="Company", markers=True,
                title=chart_title,
                labels={"Earnings (₹) per ₹1000": "Profit Owned per ₹1,000 (₹)"}
            )
            eps_fig.update_layout(xaxis_type='category') 
            st.plotly_chart(eps_fig, use_container_width=True)
            
            st.info("💡 **How to read this:** If a company's line is at ₹40 in 2023, it means for every ₹1,000 you invest today, you are buying ₹40 of their 2023 profits. The steeper the upward slope, the better.")
        else:
            st.warning("Could not find historical EPS or price data for these specific companies.")

# --- Sidebar UI: Define Peer Group for Screener ---
st.sidebar.header("1. Screener Universe")
index_choice = st.sidebar.selectbox("Choose Index for Screener:", INDEX_OPTIONS)
universe_tickers = get_nse_tickers(index_choice)
tickers = st.sidebar.multiselect("Active Companies:", universe_tickers, default=universe_tickers)

# --- Sidebar UI: The Live Screener Filters ---
st.sidebar.header("2. Healthy Business Criteria")
min_roe = st.sidebar.slider("Minimum ROE (%)", 0, 40, 15)
max_de = st.sidebar.slider("Maximum Debt-to-Equity", 0.0, 5.0, 1.5)
max_pe = st.sidebar.slider("Maximum P/E Ratio", 0, 150, 35)

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
tab1, tab2, tab3 = st.tabs(["📊 Screener & Valuation", "📈 Normalized EPS (Fair Value)", "📖 Fundamentals Guide"])

# ==========================================
# TAB 1: THE SCREENER LOGIC
# ==========================================
with tab1:
    if len(tickers) > 100:
        st.info(f"⚠️ **Large Universe Selected:** Pulling live fundamentals for {len(tickers)} stocks. This may take a few minutes.")

    with st.spinner(f"Pulling live data for {index_choice}..."):
        df = fetch_financials(tickers)

    if not df.empty:
        filtered_df = df[
            (df["ROE (%)"] >= min_roe) & 
            (df["Debt/Equity"] <= max_de) & 
            (df["P/E (TTM)"] <= max_pe)
        ]

        st.subheader(f"Index Screener: {index_choice}")
        st.write(f"Showing fundamentally strong companies out of the {len(tickers)} checked:")
        st.dataframe(filtered_df.sort_values(by="ROE (%)", ascending=False), use_container_width=True)

        st.divider()
        st.subheader("Relative Valuation Map")
        fig = px.scatter(
            df, x="P/E (TTM)", y="ROE (%)", text="Company", size="Price (₹)",
            color="Company", title=f"{index_choice} Valuation Map",
            labels={"P/E (TTM)": "Trailing P/E (Lower is Cheaper)", "ROE (%)": "Return on Equity (Higher is Better)"}
        )
        fig.update_traces(textposition='top center', marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
        fig.add_vline(x=max_pe, line_dash="dash", line_color="red", annotation_text="Max P/E")
        fig.add_hline(y=min_roe, line_dash="dash", line_color="green", annotation_text="Min ROE")
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No fundamental data found. Check your internet connection.")

# ==========================================
# TAB 2: NORMALIZED EPS ANALYSIS (PER ₹1000)
# ==========================================
with tab2:
    st.subheader("Fair Comparison: Earnings per ₹1,000 Invested")
    st.write("Nominal EPS is misleading because share prices differ. This normalizes historical earnings, showing how much profit your money would 'own' each year if you invested ₹1,000 at today's stock price.")
    
    # --- Part 1: Compare by Index ---
    st.markdown("### 1. Compare by NSE Index")
    eps_index_choice = st.selectbox("Choose Index:", INDEX_OPTIONS, key="eps_index_dropdown")
    eps_universe_tickers = get_nse_tickers(eps_index_choice)
    clean_eps_universe = [t.replace(".NS", "") for t in eps_universe_tickers]
    
    default_eps_selection = clean_eps_universe[:3] if len(clean_eps_universe) >= 3 else clean_eps_universe
    
    selected_index_peers = st.multiselect(
        "Select Companies from Index:", 
        options=clean_eps_universe, 
        default=default_eps_selection,
        key="eps_index_multiselect"
    )
    
    if selected_index_peers:
        render_eps_chart(selected_index_peers, f"Historical Earnings Yield - {eps_index_choice}")
        
    st.divider()
    
    # --- Part 2: Compare by Hardcoded Sector ---
    st.markdown("### 2. Compare by Business Category (Sector)")
    eps_sector_choice = st.selectbox("Choose Category:", list(SECTOR_DATABASE.keys()), key="eps_sector_dropdown")
    sector_universe_tickers = SECTOR_DATABASE[eps_sector_choice]
    clean_sector_universe = [t.replace(".NS", "") for t in sector_universe_tickers]
    
    default_sector_selection = clean_sector_universe[:3] if len(clean_sector_universe) >= 3 else clean_sector_universe
    
    selected_sector_peers = st.multiselect(
        "Select Competitors:", 
        options=clean_sector_universe, 
        default=default_sector_selection,
        key="eps_sector_multiselect"
    )

    if selected_sector_peers:
        render_eps_chart(selected_sector_peers, f"Historical Earnings Yield - {eps_sector_choice}")

# ==========================================
# TAB 3: EDUCATIONAL GUIDE
# ==========================================
with tab3:
    st.header("The Parameters of a 'Good' Company")
    st.write("While every industry is different, a fundamentally strong company generally scores well across these four core categories:")
    
    # Updated Markdown table with the deviation explanation column
    st.markdown("""
    | Category | Key Metric | What It Measures | What "Good" Looks Like | What Happens If It Deviates |
    | :--- | :--- | :--- | :--- | :--- |
    | **Profitability** | **Return on Equity (ROE)** | How efficiently management uses shareholder money to generate profit. | Consistently above 15%. | **If Lower:** The company is inefficient with your capital. It may be destroying shareholder wealth or struggling to generate meaningful returns. |
    | **Debt Level** | **Debt-to-Equity Ratio** | How heavily the company relies on borrowed money to operate. | Less than 1.0 (ideally very low or zero). | **If Higher:** High risk. Crushing interest payments will eat into profits, and the company could face bankruptcy during an economic downturn. |
    | **Valuation** | **Price-to-Earnings (P/E)** | How much you have to pay for every unit of profit the company makes. | Lower than its peers and its own historical average. | **If Higher:** You are overpaying. Even if it is a great business, buying at a high P/E limits your upside and increases the risk of a sharp stock crash. |
    | **Growth** | **EPS (Earnings Per Share)** | Whether the company's actual profits are increasing over time. | Steady, consistent growth over 3 to 5 years. | **If Declining/Erratic:** The business is shrinking, highly cyclical, or losing market share. The stock price will likely stagnate or fall. |
    """)
    
    st.info("💡 **Pro Tip:** Banks and financial institutions naturally carry high debt because customer deposits are counted as liabilities. You can generally ignore the Debt-to-Equity rule when analyzing the Banking & Finance sector.")
