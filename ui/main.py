import streamlit as st
import pandas as pd
import requests

# Configuration
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Portfolio Risk Intelligence", layout="wide")

st.title("Portfolio Risk & Exposure Intelligence (India)")

# Sidebar Action
st.sidebar.header("Actions")
if st.sidebar.button("Refresh Data from Folder"):
    try:
        with st.spinner("Analyzing 'holdings_transactions' folder..."):
            resp = requests.post(f"{API_URL}/portfolio/refresh")
            if resp.status_code == 200:
                st.sidebar.success("Data Refreshed!")
                st.rerun()
            else:
                st.sidebar.error(f"Failed: {resp.text}")
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")

# Main Dashboard
try:
    resp = requests.get(f"{API_URL}/portfolio/dashboard")
    
    if resp.status_code == 200:
        data = resp.json()
        portfolio_id = data.get("portfolio_id")
        holdings = data.get("holdings", [])
        
        if not holdings:
            st.info("No holdings found. Please put Excel files in 'holdings_transactions' and click Refresh.")
        else:
            df = pd.DataFrame(holdings)
            
            # Key Metrics
            total_value = df["market_value"].sum()
            total_cost = (df["avg_cost"] * df["quantity"]).sum()
            total_pnl = total_value - total_cost
            pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Portfolio Value", f"₹ {total_value:,.2f}")
            c2.metric("Total Investment", f"₹ {total_cost:,.2f}")
            c3.metric("Unrealized P&L", f"₹ {total_pnl:,.2f}", f"{pnl_pct:.2f}%")
            
            st.markdown("---")
            
            # Charts
            import plotly.express as px
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Asset Allocation")
                type_dist = df.groupby("type")["market_value"].sum().reset_index()
                fig1 = px.pie(type_dist, values='market_value', names='type', title='Asset Allocation')
                st.plotly_chart(fig1, use_container_width=True)
                
            with col2:
                st.subheader("Sector Exposure (Equity)")
                sector_dist = df[df['type'] == 'Equity'].groupby("sector")["market_value"].sum().reset_index()
                if not sector_dist.empty:
                    fig2 = px.pie(sector_dist, values='market_value', names='sector', title='Sector Exposure')
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No Equity sector data available")
            
            # Holdings Table
            st.subheader("Holdings Details")
            
            # Calculate P&L for display
            df["invested_value"] = df["quantity"] * df["avg_cost"]
            df["pnl"] = df["market_value"] - df["invested_value"]
            df["pnl_pct"] = (df["pnl"] / df["invested_value"] * 100).fillna(0)
            
            # Reorder & Rename
            display_df = df[[
                "symbol", "type", "sector", "quantity", 
                "avg_cost", "current_price", 
                "invested_value", "market_value", 
                "pnl", "pnl_pct"
            ]].copy()
            
            display_df.columns = [
                "Symbol", "Type", "Sector", "Qty", 
                "Avg Price", "CMP", 
                "Invested", "Current Val", 
                "P&L", "P&L %"
            ]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "Avg Price": st.column_config.NumberColumn(format="₹ %.2f"),
                    "CMP": st.column_config.NumberColumn(format="₹ %.2f"),
                    "Invested": st.column_config.NumberColumn(format="₹ %.2f"),
                    "Current Val": st.column_config.NumberColumn(format="₹ %.2f"),
                    "P&L": st.column_config.NumberColumn(format="₹ %.2f"),
                    "P&L %": st.column_config.NumberColumn(format="%.2f%%"),
                },
                hide_index=True
            )
            
            # Risk Analysis
            st.markdown("---")
            st.subheader("Risk Intelligence")
            
            try:
                risk_resp = requests.get(f"{API_URL}/analytics/{portfolio_id}/risk")
                if risk_resp.status_code == 200:
                    metrics = risk_resp.json()
                    if "error" in metrics:
                        st.warning(metrics["error"])
                    else:
                        r1, r2, r3 = st.columns(3)
                        r1.metric("Annualized Volatility", f"{metrics.get('volatility', 0)}%")
                        r2.metric("Portfolio Beta", metrics.get('beta', 0))
                        r3.metric("Max Drawdown (1Y)", f"{metrics.get('max_drawdown', 0)}%")
                else:
                    st.error("Could not fetch risk metrics")
            except Exception as e:
                st.error(f"Risk Service Error: {e}")
                
            # Gold-Silver Ratio Analysis
            st.markdown("---")
            st.subheader("Commodities Intelligence (Gold/Silver)")
            
            try:
                gs_resp = requests.get(f"{API_URL}/commodities/gold-silver")
                if gs_resp.status_code == 200:
                    gs_data = gs_resp.json()
                    if "error" in gs_data:
                        st.warning(gs_data["error"])
                    else:
                        g1, g2, g3 = st.columns(3)
                        g1.metric("Gold (USD/g)", f"${gs_data.get('gold_usd_per_gram', 0):.2f}")
                        g2.metric("Silver (USD/g)", f"${gs_data.get('silver_usd_per_gram', 0):.2f}")
                        g3.metric("Gold-Silver Ratio", f"{gs_data.get('ratio', 0):.2f}")
                        
                        decision = gs_data.get('decision', 'N/A')
                        if "SILVER" in decision:
                            st.success(f"Strategy: {decision}")
                        elif "GOLD" in decision:
                            st.warning(f"Strategy: {decision}")
                        else:
                            st.info(f"Strategy: {decision}")
                else:
                    st.error("Could not fetch commodities data")
            except Exception as e:
                st.error(f"Commodities Service Error: {e}")

            # Stress Testing
            st.markdown("---")
            st.subheader("Stress Testing")
            scenario = st.selectbox("Select Scenario", ["MARKET_CRASH_20", "MARKET_CORRECTION_10"])
            if st.button("Run Simulation"):
                s_resp = requests.get(f"{API_URL}/analytics/{portfolio_id}/stress/{scenario}")
                if s_resp.status_code == 200:
                    res = s_resp.json()
                    impact = res.get('estimated_impact_pct', 0)
                    loss_val = total_value * (impact / 100)
                    st.error(f"Estimated Impact: {impact}% (₹ {loss_val:,.2f})")
                else:
                    st.error("Stress Test Failed")

    elif resp.status_code == 404:
         st.warning("No data initialized. Please click 'Refresh Data from Folder' in the sidebar.")
    else:
        st.error(f"API Error: {resp.text}")
        
except Exception as e:
    st.error(f"Backend Connection Error: {e}. Is the server running?")
