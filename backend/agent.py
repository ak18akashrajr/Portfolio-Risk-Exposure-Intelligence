import os
import json
import yfinance as yf
from groq import Groq
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

# Configure LLM for CrewAI using the native LLM class
llm = LLM(
    model="groq/llama-3.3-70b-versatile", # Using 70b-versatile for higher limits
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.1
)

# --- Specialized Tool Functions ---

@tool("execute_sql_query")
def execute_sql_query(query: str):
    """
    Executes a read-only SQL query on the portfolio database.
    Useful for complex aggregations, filtering, and analysis.
    Only SELECT statements are allowed.
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
    llm=llm,
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
    llm=llm,
    verbose=True,
    allow_delegation=False
)

data_ingester = Agent(
    role='Data Agent',
    goal='Ensure data integrity and handle general data requests.',
    backstory="""You ensure data follows rules and schemas.""",
    tools=[get_portfolio_analysis],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

analytics_agent = Agent(
    role='Analytics Agent',
    goal='Perform complex analysis and risk assessment.',
    backstory="""You provide deep insights from portfolio data.
    CRITICAL: You MUST use the 'get_portfolio_analysis' or 'execute_sql_query' tools to fetch actual data.
    NEVER invent or hallucinate holdings, stock names, or values. check tables 'transaction' and 'holding' in database.
    If the user asks for analysis of their holdings, you must first GET the holdings using the tool. DO NOT assume what they are.
    IMPORTANT: You MUST ensure that the final response to the user includes the source of any market data used. 
    If a peer agent used 'mock_data', include that keyword. If they used 'Live Market Data', include that keyword.""",
    tools=[get_portfolio_analysis, execute_sql_query],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

trading_agent = Agent(
    role='Order Placing Agent',
    goal='Execute buy/sell orders and update records.',
    backstory="""You handle order placements and deletions precisely.""",
    tools=[place_order_tool, delete_transaction_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

visual_agent = Agent(
    role='Chart Agent',
    goal='Format data for visual charts.',
    backstory="""You transform numbers into chart JSON.""",
    tools=[generate_chart_data],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

sql_agent = Agent(
    role='SQL Agent',
    goal='Execute SQL queries for complex data retrieval.',
    backstory="""You are an SQL expert. 
    CRITICAL: You MUST check the database schema before answering. 
    The visible tables are 'transaction', 'holding' and others. 
    NEVER halluncinate table names. Always execute valid SQL.""",
    tools=[execute_sql_query],
    llm=llm,
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
        2. If you fetch market prices, you MUST explicitly state whether the data is from 'Live Market Data' or if it is 'mock_data'.
           - Do not omit this information. The user needs to know the data source.
        """,
        expected_output="A helpful response based ONLY on the actual database usage and tool outputs. It must EXPLICITLY mention the data source (Live Market Data or mock_data) if market prices were involved, and end with a follow-up question.",
        # agent=analytics_agent  <-- Removed to allow hierarchical delegation
    )

    crew = Crew(
        agents=[market_analyst, portfolio_specialist, data_ingester, analytics_agent, trading_agent, visual_agent, sql_agent],
        tasks=[analysis_task],
        process=Process.hierarchical, # Use hierarchical process for dynamic routing
        manager_llm=llm, # Use the same LLM for the manager
        verbose=True
    )

    try:
        result = crew.kickoff()
        return str(result)
    except Exception as e:
        print(f"CrewAI Error: {e}")
        return f"Error: {str(e)}"
