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

    /* ChatGPT-style Chat Bubbles */
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        padding: 1.2rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stChatMessage"]:hover {
        background: rgba(255, 255, 255, 0.05) !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
    }

    /* Differentiate User and Assistant bubbles */
    [data-testid="stChatMessage"][data-testid="stChatMessageContent"] {
        margin-left: 0 !important;
    }
    
    /* User Message Styling */
    section[data-testid="stChatMessage"]:has(img[alt="user"]) {
        border-left: 4px solid #38bdf8 !important;
    }

    /* Assistant Message Styling */
    section[data-testid="stChatMessage"]:has(img[alt="assistant"]) {
        border-left: 4px solid #10b981 !important;
    }

    /* Chat Input Styling - Pin to bottom with premium glassmorphism */
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 2rem !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 70% !important;
        max-width: 1000px !important;
        background: rgba(15, 23, 42, 0.9) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        box-shadow: 0 -5px 25px rgba(0, 0, 0, 0.2) !important;
        z-index: 1000 !important;
    }
    
    /* Ensure chat history has space to scroll above fixed input */
    .stChatFloatingInputContainer {
        padding-bottom: 5rem !important;
        background-color: transparent !important;
    }

    /* Better typography for chat */
    .stChatMessage p {
        font-size: 1rem !important;
        line-height: 1.6 !important;
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Application Title with Gradient
st.markdown("<h1 style='text-align: center;'>🚀 Portfolio Risk & Exposure Intelligence</h1>", unsafe_allow_html=True)

# Top Navigation Bar using Tabs
tabs = st.tabs(["📈 Dashboard", "📜 Transactions", "✍️ Manual Entry", "📤 Upload Data", "🤖 AI Assistant"])

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
            category = st.selectbox("Asset Category", ["Equity(Stocks)", "Debt(Bonds, FD)", "Commodity", "REIT", "Liquid Cash"])
            
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
                    "geography": geography,
                    "category": category
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
                m1, m2, m3, m4 = st.columns(4)
                total_invested = df_holdings['total_invested'].sum()
                
                # Check for live data status
                last_updated = pd.to_datetime(df_holdings['last_updated_at']).max()
                is_stale = (pd.Timestamp.now() - last_updated).total_seconds() > 300 if not pd.isna(last_updated) else True
                status_color = "#10b981" if not is_stale else "#f59e0b"
                status_text = "Live" if not is_stale else "Stale"
                
                current_valuation = df_holdings['current_valuation'].sum() if 'current_valuation' in df_holdings else 0.0
                total_pnl = current_valuation - total_invested
                pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
                
                m1.metric("Invested Value", f"₹{total_invested:,.2f}")
                m2.metric("Current Value", f"₹{current_valuation:,.2f}", f"{total_pnl:,.2f} ({pnl_pct:.2f}%)")
                m3.metric("Total Assets", len(df_holdings))
                
                with m4:
                    st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); text-align: center;">
                            <p style="margin: 0; color: #94a3b8; font-size: 0.8rem;">Data Status</p>
                            <p style="margin: 0; color: {status_color}; font-weight: 700; font-size: 1.1rem;">● {status_text}</p>
                            <p style="margin: 0; color: #64748b; font-size: 0.7rem;">{last_updated.strftime('%H:%M:%S') if not pd.isna(last_updated) else 'Never'}</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.divider()
                
                # Visualizations
                st.subheader("Portfolio Distribution")
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("<p style='text-align: center; font-weight: 600;'>Asset Allocation</p>", unsafe_allow_html=True)
                    fig_pie = px.pie(
                        df_holdings, 
                        values='current_valuation' if 'current_valuation' in df_holdings and df_holdings['current_valuation'].sum() > 0 else 'total_invested', 
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
                
                with c2:
                    st.markdown("<p style='text-align: center; font-weight: 600;'>Category Exposure</p>", unsafe_allow_html=True)
                    df_cat = df_holdings.groupby('category')['total_invested'].sum().reset_index()
                    fig_cat = px.pie(
                        df_cat,
                        values='total_invested',
                        names='category',
                        color_discrete_sequence=px.colors.sequential.Blues_r,
                        hole=0.4
                    )
                    fig_cat.update_layout(
                        margin=dict(t=0, b=0, l=0, r=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_color="white",
                        showlegend=False
                    )
                    st.plotly_chart(fig_cat, use_container_width=True)

                with c3:
                    st.markdown("<p style='text-align: center; font-weight: 600;'>Geographic Exposure</p>", unsafe_allow_html=True)
                    df_geo = df_holdings.groupby('geography')['total_invested'].sum().reset_index()
                    fig_geo = px.pie(
                        df_geo,
                        values='total_invested',
                        names='geography',
                        color_discrete_sequence=px.colors.sequential.Purp_r,
                        hole=0.4
                    )
                    fig_geo.update_layout(
                        margin=dict(t=0, b=0, l=0, r=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_color="white",
                        showlegend=False
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)
                
                st.divider()
                st.subheader("Real-time Holdings Details")
                # Calculate PNL per holding
                if 'current_price' in df_holdings:
                    df_holdings['pnl'] = df_holdings['current_valuation'] - df_holdings['total_invested']
                    df_holdings['pnl_%'] = (df_holdings['pnl'] / df_holdings['total_invested'] * 100).fillna(0)
                
                cols_to_show = ['stock_name', 'symbol', 'category', 'quantity', 'avg_price', 'total_invested']
                if 'current_price' in df_holdings:
                    cols_to_show += ['current_price', 'current_valuation', 'pnl', 'pnl_%']

                st.dataframe(
                    df_holdings[cols_to_show].sort_values(by='total_invested', ascending=False),
                    use_container_width=True,
                    height=300
                )
                
                st.divider()
                st.subheader("Capital Deployment & Valuation History")
                try:
                    res_hist = requests.get(f"{BACKEND_URL}/valuation-history")
                    if res_hist.status_code == 200:
                        hist_data = res_hist.json()
                        if hist_data:
                            df_hist = pd.DataFrame(hist_data)
                            df_hist['date'] = pd.to_datetime(df_hist['date'])
                            
                            # Melt the dataframe for plotly (long format)
                            df_melted = df_hist.melt(id_vars=['date'], value_vars=['invested_value', 'market_value'], 
                                                    var_name='Series', value_name='Value (₹)')
                            
                            # Clean up series names for display
                            df_melted['Series'] = df_melted['Series'].replace({
                                'invested_value': 'Invested Value',
                                'market_value': 'Portfolio Valuation'
                            })
                            
                            fig_area = px.area(
                                df_melted, 
                                x='date', 
                                y='Value (₹)', 
                                color='Series',
                                color_discrete_map={
                                    'Invested Value': 'rgba(56, 189, 248, 0.4)',  # Cyan-ish
                                    'Portfolio Valuation': 'rgba(16, 185, 129, 0.4)' # Green-ish
                                },
                                markers=False
                            )
                            
                            fig_area.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color="white",
                                xaxis_title="Timeline",
                                yaxis_title="Value (₹)",
                                margin=dict(t=20, b=20, l=20, r=20),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig_area, use_container_width=True)
                        else:
                            st.info("No historical data available yet.")
                    else:
                        st.warning("Could not fetch valuation history.")
                except Exception as e:
                    st.error(f"Chart Error: {e}")
                    
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
                df_tx['execution_time'] = pd.to_datetime(df_tx['execution_time'], format='ISO8601')
                
                st.dataframe(
                    df_tx[['execution_time', 'stock_name', 'symbol', 'type', 'quantity', 'price', 'category', 'geography', 'exchange', 'order_id']].sort_values(by='execution_time', ascending=False),
                    use_container_width=True,
                    height=500
                )
            else:
                st.info("No transaction history found.")
        else:
            st.error("Failed to fetch transactions.")
    except Exception as e:
        st.error(f"📡 Backend unreachable: {e}")

with tabs[4]: # AI Assistant
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🤖 GPT Portfolio Assistant</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8;'>Real-time AI analysis for your portfolio.</p>", unsafe_allow_html=True)
    st.divider()
    
    # Create a scrollable container for the chat history
    chat_container = st.container()
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    with chat_container:
        # Show welcome message if no history
        if not st.session_state.messages:
            with st.chat_message("assistant"):
                st.markdown("""
                Hello! I'm your **GPT Portfolio Assistant**. I have real-time access to your holdings and transaction history.
                
                How can I help you today? You can ask me things like:
                - *'What is my total exposure in India?'*
                - *'Compare my November 2024 and 2025 transactions.'*
                """)

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message["content"]
            
            # Simple check if content is JSON (for chart data)
            if content.startswith("{") and "chart_type" in content:
                try:
                    data = json.loads(content)
                    st.write(data["message"])
                    df_chart = pd.DataFrame(data["data"])
                    if data["chart_type"] == "bar":
                        fig = px.bar(df_chart, x='label', y='value', color_discrete_sequence=['#38bdf8'])
                    elif data["chart_type"] == "line":
                        fig = px.line(df_chart, x='label', y='value', color_discrete_sequence=['#38bdf8'])
                    elif data["chart_type"] == "pie":
                        fig = px.pie(df_chart, values='value', names='label', color_discrete_sequence=px.colors.sequential.Blues_r)
                    
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.markdown(content)
            else:
                st.markdown(content)

    # Chat input
    if prompt := st.chat_input("Ask a question about your portfolio..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            with st.spinner("AI is thinking..."):
                response = requests.post(
                    f"{BACKEND_URL}/chat", 
                    json={"history": st.session_state.messages}
                )
                if response.status_code == 200:
                    answer = response.json().get("response")
                    
                    # Add assistant response to history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    # Rerun to display new message with potential chart logic
                    st.rerun()
                else:
                    st.error(f"❌ Error: {response.json().get('detail', 'Failed to get response')}")
        except Exception as e:
            st.error(f"📡 Connection failure: {e}")
