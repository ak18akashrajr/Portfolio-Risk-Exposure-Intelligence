import os
import json
import yfinance as yf
from dotenv import load_dotenv
from sqlmodel import Session, select, func, text
from .database import engine
from .models import Transaction, Holding
from .ingestion import add_manual_transaction, update_holdings
from .utils import get_market_data_mock
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

load_dotenv()

# --- Telemetry & Optimization ---
# Disable CrewAI telemetry to prevent connection timeouts in restricted environments
os.environ["OTEL_SDK_DISABLED"] = "true"

# --- LLM Configurations ---
# 1. Fast Model (Routing, Simple Tasks, Formatting)
llm_fast = LLM(
    model="gemini/gemini-flash-lite-latest",
    api_key=os.environ.get("GOOGLE_API_KEY"),
    temperature=0.1
)

# 2. Reasoning Model (Complex Analysis, SQL Generation)
# Using flash-lite here too to avoid the strict 429 quotas of the 'pro' model in this environment
llm_reasoning = LLM(
    model="gemini/gemini-flash-lite-latest", 
    api_key=os.environ.get("GOOGLE_API_KEY"),
    temperature=0.1
)

# --- Specialized Tool Functions ---

@tool("execute_sql_query")
def execute_sql_query(query: str):
    """
    Executes a read-only SQL query on the portfolio database.
    Useful for complex aggregations, filtering, and analysis.
    Only SELECT statements are allowed.
    
    TABLES AVAILABLE:
    1. "transaction": columns [id, stock_name, symbol, isin, type (BUY/SELL), quantity, price, exchange, order_id, execution_time (ISO format), geography, category, status]
    2. "holding": columns [symbol (PK), stock_name, isin, quantity, avg_price, total_invested, geography, category, last_transaction_date]
    
    IMPORTANT: The "transaction" table name is a reserved keyword in some SQL dialects, always quote it as `"transaction"` in your queries.
    DATES: execution_time is stored as a string. Use strftime('%Y', execution_time) or strftime('%Y-%m', execution_time) for filtering.
    """
    if not query.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed for security reasons."}
    
    with Session(engine) as session:
        try:
            result = session.exec(text(query))
            rows = [dict(row._mapping) for row in result]
            return {
                "status": "success",
                "data": rows,
                "count": len(rows),
                "query": query
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

@tool("get_market_data")
def get_market_data(symbol: str):
    """
    Fetches live market price and details for a stock symbol (e.g., RELIANCE.NS, AAPL).
    Falls back to mock data if the network is restricted.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.last_price
        
        if price is None or price == 0:
            raise ValueError("Price not found")

        return {
            "symbol": symbol,
            "price": price,
            "currency": "INR" if ".NS" in symbol or ".BO" in symbol else "USD",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Live Market Data",
            "status": "success"
        }
    except Exception as e:
        mock_data = get_market_data_mock(symbol)
        mock_data["source"] = "mock_data"
        return mock_data

@tool("get_portfolio_analysis")
def get_portfolio_analysis():
    """
    Analyzes the user's holdings and transactions to provide a summary.
    """
    with Session(engine) as session:
        holdings = session.exec(select(Holding)).all()
        transactions = session.exec(select(Transaction)).all()
        
        holdings_list = [
            {
                "symbol": h.symbol,
                "name": h.stock_name,
                "quantity": h.quantity,
                "avg_cost": h.avg_price,
                "total_invested": h.total_invested
            } for h in holdings
        ]
        
        total_invested = sum(h.total_invested for h in holdings)
        
        return {
            "holdings": holdings_list,
            "total_invested_value": total_invested,
            "transaction_count": len(transactions),
            "source": "internal-db"
        }

@tool("get_historical_holdings")
def get_historical_holdings(date_str: str):
    """
    Reconstructs the portfolio holdings as they were on a specific date.
    Input format: 'YYYY-MM-DD' (e.g., '2025-01-31').
    """
    try:
        # Normalize date for search
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Please use YYYY-MM-DD."}

    with Session(engine) as session:
        # Fetch all transactions up to the target date
        transactions = session.exec(
            select(Transaction).where(Transaction.execution_time <= target_date)
        ).all()
        
        if not transactions:
            return {"status": "success", "date": date_str, "holdings": [], "total_invested": 0, "message": "No transactions found on or before this date."}

        # Aggregate holdings
        historical_holdings = {}
        for tx in transactions:
            symbol = tx.symbol
            if symbol not in historical_holdings:
                historical_holdings[symbol] = {
                    "symbol": symbol,
                    "name": tx.stock_name,
                    "quantity": 0,
                    "total_cost": 0.0
                }
            
            if tx.type.upper() == "BUY":
                historical_holdings[symbol]["quantity"] += tx.quantity
                historical_holdings[symbol]["total_cost"] += (tx.quantity * tx.price)
            elif tx.type.upper() == "SELL":
                historical_holdings[symbol]["quantity"] -= tx.quantity
                # For historical cost, we'll keep it simple: reduce proportion. 
                # (Actual avg cost calculation usually depends on FIFO/LIFO, 
                # but simple aggregation is sufficient for basic historical comparison).
                if historical_holdings[symbol]["quantity"] > 0:
                    historical_holdings[symbol]["total_cost"] *= ( (historical_holdings[symbol]["quantity"]) / (historical_holdings[symbol]["quantity"] + tx.quantity) )
                else:
                    historical_holdings[symbol]["total_cost"] = 0

        # Filter out zero holdings and format
        result_list = []
        total_value = 0
        for symbol, data in historical_holdings.items():
            if data["quantity"] > 0:
                avg_price = data["total_cost"] / data["quantity"] if data["quantity"] > 0 else 0
                result_list.append({
                    "symbol": symbol,
                    "name": data["name"],
                    "quantity": data["quantity"],
                    "avg_cost": round(avg_price, 2),
                    "total_invested": round(data["total_cost"], 2)
                })
                total_value += data["total_cost"]

        return {
            "status": "success",
            "date": date_str,
            "holdings": result_list,
            "total_invested_value": round(total_value, 2),
            "transaction_count": len(transactions),
            "source": "internal-db-history"
        }

@tool("place_order_tool")
def place_order_tool(symbol: str, tx_type: str, quantity: int, price: float, exchange: str = "NSE"):
    """
    Places a manual transaction order in the database and updates holdings.
    """
    with Session(engine) as session:
        try:
            transaction = add_manual_transaction(
                session=session,
                symbol=symbol.upper(),
                tx_type=tx_type.upper(),
                quantity=quantity,
                price=price,
                exchange=exchange.upper()
            )
            return {
                "status": "success",
                "message": f"Successfully placed {tx_type} order for {quantity} shares of {symbol} at INR {price}.",
                "order_id": transaction.order_id
            }
        except Exception as e:
            return {"status": "error", "message": f"Database update failed: {str(e)}"}

@tool("delete_transaction_tool")
def delete_transaction_tool(order_id: str = None, symbol: str = None):
    """
    Deletes transactions by order ID or all transactions for a specific symbol.
    """
    with Session(engine) as session:
        try:
            if order_id:
                transaction = session.exec(select(Transaction).where(Transaction.order_id == order_id)).first()
                if not transaction:
                    return {"status": "error", "message": "Transaction not found."}
                session.delete(transaction)
                msg = f"Transaction {order_id} deleted."
            elif symbol:
                transactions = session.exec(select(Transaction).where(Transaction.symbol == symbol.upper())).all()
                if not transactions:
                    return {"status": "error", "message": "No transactions found."}
                for tx in transactions:
                    session.delete(tx)
                msg = f"All transactions for {symbol} deleted."
            
            session.commit()
            update_holdings(session)
            return {"status": "success", "message": msg}
        except Exception as e:
            return {"status": "error", "message": f"Deletion failed: {str(e)}"}

@tool("generate_chart_data")
def generate_chart_data(chart_type: str, data_points: list):
    """
    Formats data for chart generation on the frontend.
    data_points should be a list of objects with label and value.
    """
    return {
        "chart_type": chart_type,
        "data": data_points,
        "message": "Chart data generated successfully."
    }

# --- Agent Definitions ---

market_analyst = Agent(
    role='Live Market Data Agent',
    goal='Provide up-to-date market prices and financial information.',
    backstory="""You fetch accurate market data. 
    IMPORTANT: If you use the output of a tool that mentions 'mock_data', you MUST explicitly write the phrase 'mock_data' in your final answer. 
    If the tool output indicates 'Live Market Data', you MUST explicitly write the phrase 'Live Market Data' in your final answer. 
    This is a strict requirement from the user.""",
    tools=[get_market_data],
    llm=llm_reasoning, 
    verbose=True,
    allow_delegation=False
)

portfolio_specialist = Agent(
    role='Transaction cum Holdings Agent',
    goal='Manage and summarize user holdings and transactions.',
    backstory="""You summarize portfolio data clearly. 
    CRITICAL: You MUST use the 'get_portfolio_analysis' tool to fetch the actual data. 
    NEVER invent or hallucinate holdings. If the tool returns no data, state that the portfolio is empty.
    Always mention that the data is from the internal database.""",
    tools=[get_portfolio_analysis],
    llm=llm_fast,
    verbose=True,
    allow_delegation=False
)

data_ingester = Agent(
    role='Data Agent',
    goal='Ensure data integrity and handle general data requests.',
    backstory="""You ensure data follows rules and schemas.""",
    tools=[get_portfolio_analysis],
    llm=llm_fast,
    verbose=True,
    allow_delegation=False
)

analytics_agent = Agent(
    role='Expert Financial Analyst',
    goal='Provide sophisticated risk assessment and investment insights.',
    backstory="""You are a world-class financial quantitative analyst. 
    You provide deep insights from portfolio data, including sector diversification, risk concentration, and potential market exposure.
    CRITICAL: You MUST use the 'get_portfolio_analysis' or 'execute_sql_query' tools to fetch real data for current state.
    HISTORICAL ANALYSIS: If the user asks for a comparison across dates (e.g., "Jan 2025 vs Jan 2026"), you MUST use the 'get_historical_holdings' tool for EACH date to reconstruct the portfolio state at those times.
    NEVER invent or hallucinate holdings. Check tables 'transaction' and 'holding' in database.
    SUPER REQUIREMENT: Always attempt to provide a "Macro Insight" or "Risk Score" based on the holdings you find. 
    If you see high concentration in one stock, warn the user. If the data is empty, suggest how to get started.""",
    tools=[get_portfolio_analysis, execute_sql_query, get_historical_holdings],
    llm=llm_reasoning,
    verbose=True,
    allow_delegation=False
)

trading_agent = Agent(
    role='Order Placing Agent',
    goal='Execute buy/sell orders and update records.',
    backstory="""You handle order placements and deletions precisely.""",
    tools=[place_order_tool, delete_transaction_tool],
    llm=llm_fast,
    verbose=True,
    allow_delegation=False
)

visual_agent = Agent(
    role='Chart Agent',
    goal='Format data for visual charts.',
    backstory="""You transform numbers into chart JSON.""",
    tools=[generate_chart_data],
    llm=llm_fast,
    verbose=True,
    allow_delegation=False
)

sql_agent = Agent(
    role='SQL Agent',
    goal='Execute SQL queries for complex data retrieval.',
    backstory="""You are a world-class SQL expert specializing in SQLite.
    CRITICAL: Before writing any query, you MUST refer to this schema:
    1. Table "transaction":
       - columns: [id, stock_name, symbol, isin, type (BUY/SELL), quantity, price, exchange, order_id, execution_time, geography, category, status]
       - Note: Always quote as `"transaction"` because it's a reserved keyword.
       - Note: execution_time is a timestamp. For monthly/yearly comparisons, use SQLite date functions like strftime('%m', execution_time) or strftime('%Y', execution_time).
    2. Table "holding":
       - columns: [symbol, stock_name, isin, quantity, avg_price, total_invested, geography, category, last_transaction_date]
    
    Your goal is to write highly efficient, read-only SELECT queries to answer user questions about their financial history and portfolio state.
    Always prioritize accuracy and double-check column names against the schema provided above.""",
    tools=[execute_sql_query],
    llm=llm_reasoning,
    verbose=True,
    allow_delegation=False
)

# --- Task Execution Logic ---

def get_ai_response(history: list):
    user_query = history[-1]['content'] if history else ""
    
    # In a hierarchical process, we do NOT assign a specific agent to the task.
    # The manager LLM decides which agent to delegate to.
    analysis_task = Task(
        description=f"""Process the user query: '{user_query}' while considering history context.
        
        CRITICAL RULES:
        1. If the user asks about holdings, portfolio, or investments, you MUST use the 'get_portfolio_analysis' tool. 
           - Do NOT provide a generic example or hallucinated data.
           - If the tool returns no holdings, state that the portfolio is empty.
        2. COMPARISON/HISTORICAL: If the user asks to compare dates or asks for state at a specific past date, you MUST use 'get_historical_holdings' with the appropriate date strings. 
           - For complex transaction comparisons (e.g., month over month), utilize the 'sql_agent' to query the "transaction" table directly for precise results.
           - Calculate differences in total value, top holdings, and diversification between the points.
        3. If you fetch market prices, you MUST explicitly state whether the data is from 'Live Market Data' or if it is 'mock_data'.
           - Do not omit this information. The user needs to know the data source.
        """,
        expected_output="A helpful response based ONLY on the actual database usage and tool outputs. It must EXPLICITLY mention the data source (Live Market Data or mock_data) if market prices were involved, and end with a follow-up question.",
        # agent=analytics_agent  <-- Removed to allow hierarchical delegation
    )

    crew = Crew(
        agents=[market_analyst, portfolio_specialist, data_ingester, analytics_agent, trading_agent, visual_agent, sql_agent],
        tasks=[analysis_task],
        process=Process.hierarchical, # Use hierarchical process for dynamic routing
        manager_llm=llm_fast, # Use fast model for routing
        verbose=True
    )

    try:
        result = crew.kickoff()
        return str(result)
    except Exception as e:
        print(f"CrewAI Error: {e}")
        return f"Error: {str(e)}"
