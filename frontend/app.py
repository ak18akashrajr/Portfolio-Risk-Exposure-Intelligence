import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Constants
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Portfolio Risk Exposure Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    /* Main container background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }

    /* Glassmorphism sidebar (if used) and containers */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(8px);
        border-radius: 10px;
        padding: 10px 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    /* Titles and Headers */
    h1 {
        font-size: 1.8rem !important;
        margin-bottom: 1rem !important;
    }
    h2 {
        font-size: 1.4rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
    }

    /* Button Styling */
    .stButton > button {
        background: linear-gradient(90deg, #0ea5e9 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.3rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.4);
    }

    /* Tabs (Navbar) styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 5px;
        padding-bottom: 5px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom: 2px solid #38bdf8 !important;
    }

    /* Reduce vertical spacing between elements */
    .stMarkdown, .stVerticalBlock {
        gap: 0.5rem !important;
    }

    /* Hide standard Streamlit header and footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Center aligning elements */
    .centered-container {
        display: flex;
        justify-content: center;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# Application Title with Gradient
st.markdown("<h1 style='text-align: center;'>🚀 Portfolio Risk & Exposure Intelligence</h1>", unsafe_allow_html=True)

# Top Navigation Bar using Tabs
tabs = st.tabs(["📈 Dashboard", "📜 Transactions", "✍️ Manual Entry", "📤 Upload Data"])

with tabs[3]: # Upload Data
    st.header("Upload Portfolio Data")
    st.info("Upload your Excel file to sync your trades and holdings.")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        if st.button("Process & Sync File"):
            with st.spinner("Analyzing and synchronizing data..."):
                try:
                    response = requests.post(f"{BACKEND_URL}/upload", files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
                    if response.status_code == 200:
                        st.success("✨ Portfolio successfully synchronized!")
                        st.balloons()
                    else:
                        st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"📡 Backend Connection Failed: {e}")

with tabs[2]: # Manual Transaction
    st.header("Add Transaction Manually")
    
    with st.form("manual_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("Stock Symbol (e.g. RELIANCE.NS)").upper()
            tx_type = st.selectbox("Transaction Type", ["BUY", "SELL"])
            exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        
        with col2:
            quantity = st.number_input("Quantity", min_value=1, step=1)
            price = st.number_input("Total Transaction Value (₹)", min_value=0.01)
            geography = st.text_input("Geography", value="India")
            
        st.divider()
        st.markdown("### Optional Metadata")
        col3, col4 = st.columns(2)
        with col3:
            stock_name = st.text_input("Full Stock Name")
        with col4:
            isin = st.text_input("ISIN Number")
            
        submitted = st.form_submit_button("🔥 Add Transaction")
        
        if submitted:
            if not symbol:
                st.error("❗ Stock Symbol is mandatory.")
            else:
                payload = {
                    "symbol": symbol,
                    "type": tx_type,
                    "quantity": quantity,
                    "price": price,
                    "exchange": exchange,
                    "stock_name": stock_name if stock_name else None,
                    "isin": isin if isin else None,
                    "geography": geography
                }
                
                try:
                    response = requests.post(f"{BACKEND_URL}/transactions/manual", json=payload)
                    if response.status_code == 200:
                        st.success(f"✅ Transaction Securely Recorded! Order ID: `{response.json().get('order_id')}`")
                    else:
                        st.error(f"❌ Backend Rejection: {response.json().get('detail')}")
                except Exception as e:
                    st.error(f"📡 Connection Lost: {e}")

with tabs[0]: # Dashboard
    st.header("Portfolio Overview")
    
    try:
        response = requests.get(f"{BACKEND_URL}/holdings")
        if response.status_code == 200:
            holdings = response.json()
            if holdings:
                df_holdings = pd.DataFrame(holdings)
                
                # Metrics at top
                m1, m2, m3 = st.columns(3)
                total_invested = df_holdings['total_invested'].sum()
                m1.metric("Current Exposure", f"₹{total_invested:,.2f}")
                m2.metric("Total Assets", len(df_holdings))
                m3.metric("Avg. Yield", "--") # Placeholder for future logic
                
                st.divider()
                
                # Visualizations
                col1, col2 = st.columns([1, 1.2])
                
                with col1:
                    st.subheader("Asset Allocation")
                    fig_pie = px.pie(
                        df_holdings, 
                        values='total_invested', 
                        names='stock_name',
                        color_discrete_sequence=px.colors.sequential.Tealgrn,
                        hole=0.4
                    )
                    fig_pie.update_layout(
                        margin=dict(t=0, b=0, l=0, r=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_color="white",
                        showlegend=False
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    st.subheader("Real-time Holdings")
                    st.dataframe(
                        df_holdings[['stock_name', 'symbol', 'geography', 'quantity', 'avg_price', 'total_invested']],
                        use_container_width=True,
                        height=400
                    )
                
                st.divider()
                st.subheader("Capital Deployment History")
                # Group by date to see investment over time
                response_tx = requests.get(f"{BACKEND_URL}/transactions")
                if response_tx.status_code == 200:
                    df_tx = pd.DataFrame(response_tx.json())
                    if not df_tx.empty:
                        df_tx['execution_time'] = pd.to_datetime(df_tx['execution_time'])
                        df_tx = df_tx.sort_values('execution_time')
                        
                        df_tx['investment_change'] = df_tx.apply(lambda x: x['price'] if x['type'].upper() == 'BUY' else -x['price'], axis=1)
                        df_tx['cumulative_invested'] = df_tx['investment_change'].cumsum()
                        
                        fig_line = px.area(
                            df_tx, 
                            x='execution_time', 
                            y='cumulative_invested',
                            color_discrete_sequence=['#38bdf8']
                        )
                        fig_line.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font_color="white",
                            xaxis_title="Time",
                            yaxis_title="Invested Value (₹)",
                            margin=dict(t=20, b=20, l=20, r=20)
                        )
                        st.plotly_chart(fig_line, use_container_width=True)
                    
            else:
                st.info("💡 Your portfolio is empty. Add transactions to see analytics.")
        else:
            st.error("❌ Failed to synchronize with database.")
    except Exception as e:
        st.error(f"📡 Connectivity Error: {e}")

with tabs[1]: # Transactions
    st.header("Transaction Ledger")
    
    try:
        response = requests.get(f"{BACKEND_URL}/transactions")
        if response.status_code == 200:
            transactions = response.json()
            if transactions:
                df_tx = pd.DataFrame(transactions)
                df_tx['execution_time'] = pd.to_datetime(df_tx['execution_time'])
                
                st.dataframe(
                    df_tx[['execution_time', 'stock_name', 'symbol', 'type', 'quantity', 'price', 'geography', 'exchange', 'order_id']].sort_values(by='execution_time', ascending=False),
                    use_container_width=True,
                    height=500
                )
            else:
                st.info("No transaction history found.")
        else:
            st.error("Failed to fetch transactions.")
    except Exception as e:
        st.error(f"📡 Backend unreachable: {e}")
