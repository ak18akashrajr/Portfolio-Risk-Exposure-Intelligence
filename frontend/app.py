import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Constants
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Portfolio Risk Exposure Intelligence", layout="wide")

st.title("📊 Portfolio Risk Exposure Intelligence")

# Sidebar for Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Transactions", "Upload Data"])

if page == "Upload Data":
    st.header("📤 Upload Portfolio Data")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        if st.button("Process File"):
            with st.spinner("Processing..."):
                files = {"file": uploaded_file.getvalue()}
                try:
                    response = requests.post(f"{BACKEND_URL}/upload", files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
                    if response.status_code == 200:
                        st.success("File processed successfully!")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Could not connect to backend: {e}")

elif page == "Dashboard":
    st.header("📈 Portfolio Overview")
    
    try:
        response = requests.get(f"{BACKEND_URL}/holdings")
        if response.status_code == 200:
            holdings = response.json()
            if holdings:
                df_holdings = pd.DataFrame(holdings)
                
                # Metrics
                total_invested = df_holdings['total_invested'].sum()
                st.metric("Total Invested", f"₹{total_invested:,.2f}")
                
                # Visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Asset Allocation")
                    fig_pie = px.pie(df_holdings, values='total_invested', names='stock_name', title="Exposure by Stock")
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    st.subheader("Holdings Details")
                    st.dataframe(df_holdings[['stock_name', 'symbol', 'isin', 'quantity', 'avg_price', 'total_invested', 'last_transaction_date']])
                
                st.subheader("Investment Timeline")
                # Group by date to see investment over time
                response_tx = requests.get(f"{BACKEND_URL}/transactions")
                if response_tx.status_code == 200:
                    df_tx = pd.DataFrame(response_tx.json())
                    df_tx['execution_time'] = pd.to_datetime(df_tx['execution_time'])
                    df_tx = df_tx.sort_values('execution_time')
                    
                    # Cumulative investment
                    df_tx = df_tx.sort_values('execution_time')
                    df_tx['investment_change'] = df_tx.apply(lambda x: x['price'] if x['type'].upper() == 'BUY' else -x['price'], axis=1)
                    df_tx['cumulative_invested'] = df_tx['investment_change'].cumsum()
                    
                    fig_line = px.line(df_tx, x='execution_time', y='cumulative_invested', title="Cumulative Investment Over Time")
                    st.plotly_chart(fig_line, use_container_width=True)
                    
            else:
                st.info("No holdings found. Please upload your transaction history.")
        else:
            st.error("Failed to fetch holdings from backend.")
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")

elif page == "Transactions":
    st.header("📜 Transaction History")
    
    try:
        response = requests.get(f"{BACKEND_URL}/transactions")
        if response.status_code == 200:
            transactions = response.json()
            if transactions:
                df_tx = pd.DataFrame(transactions)
                # Format time
                df_tx['execution_time'] = pd.to_datetime(df_tx['execution_time'])
                st.dataframe(df_tx.sort_values(by='execution_time', ascending=False))
            else:
                st.info("No transactions found.")
        else:
            st.error("Failed to fetch transactions.")
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
