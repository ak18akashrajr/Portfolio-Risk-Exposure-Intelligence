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

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Specialized Tool Functions ---

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
            # Convert results to list of dicts
            rows = [dict(row._mapping) for row in result]
            return {
                "status": "success",
                "data": rows,
                "count": len(rows),
                "query": query
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

def get_market_data(symbol: str):
    """
    Fetches live market data for a given symbol using yfinance.
    Falls back to mock data if the network is restricted.
    """
    try:
        ticker = yf.Ticker(symbol)
        # Attempt to fetch fast info
        info = ticker.fast_info
        price = info.last_price
        
        if price is None or price == 0:
            raise ValueError("Price not found")

        return {
            "symbol": symbol,
            "price": price,
            "currency": "INR" if ".NS" in symbol or ".BO" in symbol else "USD",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": f"real-time-data from yfinance",
            "status": "success"
        }
    except Exception as e:
        # Fallback to mock data
        mock_data = get_market_data_mock(symbol)
        return mock_data

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
        
        # Simple aggregated stats
        total_invested = sum(h.total_invested for h in holdings)
        
        return {
            "holdings": holdings_list,
            "total_invested_value": total_invested,
            "transaction_count": len(transactions),
            "source": "internal-db"
        }

def place_order_tool(symbol: str, tx_type: str, quantity: int, price: float, exchange: str = "NSE"):
    """
    Places a manual transaction order in the database and updates holdings.
    """
    with Session(engine) as session:
        try:
            print(f"Executing manual transaction for {symbol}...")
            transaction = add_manual_transaction(
                session=session,
                symbol=symbol.upper(),
                tx_type=tx_type.upper(),
                quantity=quantity,
                price=price,
                exchange=exchange.upper()
            )
            
            # Explicitly verify the transaction was saved
            verify_tx = session.exec(select(Transaction).where(Transaction.order_id == transaction.order_id)).first()
            if not verify_tx:
                raise Exception("Transaction failed to persist in database.")
            
            return {
                "status": "success",
                "message": f"Successfully placed {tx_type} order for {quantity} shares of {symbol} at INR {price}. Portfolio updated.",
                "order_id": transaction.order_id,
                "action_required": "Please refresh the dashboard to see changes."
            }
        except Exception as e:
            print(f"Error in place_order_tool: {e}")
            return {"status": "error", "message": f"Database update failed: {str(e)}"}

def delete_transaction_tool(order_id: str = None, symbol: str = None):
    """
    Deletes transactions by order ID or all transactions for a specific symbol.
    At least one parameter must be provided.
    """
    with Session(engine) as session:
        try:
            if order_id:
                transaction = session.exec(select(Transaction).where(Transaction.order_id == order_id)).first()
                if not transaction:
                    return {"status": "error", "message": f"Transaction with order ID {order_id} not found."}
                session.delete(transaction)
                msg = f"Transaction {order_id} deleted."
            elif symbol:
                transactions = session.exec(select(Transaction).where(Transaction.symbol == symbol.upper())).all()
                if not transactions:
                    return {"status": "error", "message": f"No transactions found for symbol {symbol}."}
                for tx in transactions:
                    session.delete(tx)
                msg = f"All {len(transactions)} transactions for {symbol} deleted."
            else:
                return {"status": "error", "message": "Either order_id or symbol must be provided."}
            
            session.commit()
            update_holdings(session)
            
            return {
                "status": "success",
                "message": f"{msg} Holdings have been recalculated and synced.",
                "action_required": "Refresh your dashboard."
            }
        except Exception as e:
            return {"status": "error", "message": f"Deletion failed: {str(e)}"}

def generate_chart_data(chart_type: str, data_points: list):
    """
    Formats data for chart generation on the frontend.
    data_points should be a list of objects with label and value.
    """
    return {
        "chart_type": chart_type,
        "data": data_points,
        "message": "Chart data generated successfully. Please render this visually."
    }

# --- Tool Definitions ---

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql_query",
            "description": "Execute a read-only SQL SELECT query to answer complex data questions about transactions and holdings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The SQL SELECT statement to execute."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_data",
            "description": "Get live market price and details for a stock symbol (e.g., RELIANCE.NS, AAPL).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The stock ticker symbol."}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_analysis",
            "description": "Get a comprehensive analysis of the user's current holdings and transactions.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "place_order_tool",
            "description": "Place a buy or sell order for a stock. This will update the user's portfolio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The stock ticker symbol."},
                    "tx_type": {"type": "string", "enum": ["BUY", "SELL"], "description": "The type of transaction."},
                    "quantity": {"type": "integer", "description": "The number of shares."},
                    "price": {"type": "number", "description": "The price per share or total value depending on context."},
                    "exchange": {"type": "string", "default": "NSE", "description": "The stock exchange."}
                },
                "required": ["symbol", "tx_type", "quantity", "price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_transaction_tool",
            "description": "Delete a transaction by its order ID OR delete all transactions for a specific symbol. This will automatically update the portfolio holdings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The unique exchange order ID to delete (for single deletion)."},
                    "symbol": {"type": "string", "description": "The stock ticker symbol to delete all transactions for (for bulk deletion)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart_data",
            "description": "Generate data for visual charts (bar, line, pie).",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie"]},
                    "data_points": {
                        "type": "array", 
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["chart_type", "data_points"]
            }
        }
    }
]

def get_ai_response(history: list):
    """
    Supervisor Agent that orchestrates multi-agent tasks via specialized tools.
    """
    prompt_context = (
        "DATABASE SCHEMA:\n"
        "- Table `transaction`: columns [id, stock_name, symbol, isin, type (BUY/SELL), quantity, price (Total Value), exchange, order_id, execution_time (YYYY-MM-DD HH:MM:SS), geography, category, status]. IMPORTANT: Always wrap 'transaction' in double quotes like \"transaction\" in SQL queries as it is a reserved word.\n"
        "- Table `holding`: columns [symbol (PK), stock_name, isin, quantity, avg_price, total_invested, geography, category, last_transaction_date]\n\n"
        "SPECIALIZED AGENTS:\n"
        "1. Data Analyst (SQL Agent): Use `execute_sql_query` for complex filtering, date-based queries (e.g., 'buyings for Jan 2026'), or aggregations.\n"
        "2. Live Market Data Agent: Use `get_market_data` for price queries.\n"
        "3. Transaction & Holdings Agent: Use `get_portfolio_analysis` for high-level summary.\n"
        "4. Order Placing Agent: Use `place_order_tool` for NEW transactions. This persist to DB.\n"
        "5. Deletion Agent: Use `delete_transaction_tool` to remove specific transactions by order ID. This automatically syncs holdings.\n"
        "6. Chart Agent: Use `generate_chart_data` for visuals.\n\n"
        "STRICT RULES:\n"
        "- For date queries like 'Jan 2026', use execution_time BETWEEN '2026-01-01' AND '2026-01-31' in SQL.\n"
        "- If a tool indicates 'stale-data only', inform the user it's mock data.\n"
        "- If an order is placed or deleted, inform the user clearly that the DB was updated and suggest a refresh.\n"
        "- ALWAYS use 'INR' or '₹' for Indian stocks (.NS or .BO). Prefer 'INR' in text for compatibility.\n"
        "- ALWAYS end with a follow-up question."
    )
    
    system_prompt = {
        "role": "system",
        "content": f"You are the Portfolio Intelligence Orchestrator. {prompt_context}"
    }
    
    messages = [system_prompt] + history

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"Calling tool: {function_name} with args: {function_args}")
                
                if function_name == "execute_sql_query":
                    function_response = execute_sql_query(function_args.get("query"))
                elif function_name == "get_market_data":
                    function_response = get_market_data(function_args.get("symbol"))
                elif function_name == "get_portfolio_analysis":
                    function_response = get_portfolio_analysis()
                elif function_name == "place_order_tool":
                    function_response = place_order_tool(
                        symbol=function_args.get("symbol"),
                        tx_type=function_args.get("tx_type"),
                        quantity=function_args.get("quantity"),
                        price=function_args.get("price"),
                        exchange=function_args.get("exchange", "NSE")
                    )
                elif function_name == "delete_transaction_tool":
                    function_response = delete_transaction_tool(
                        order_id=function_args.get("order_id"),
                        symbol=function_args.get("symbol")
                    )
                elif function_name == "generate_chart_data":
                    function_response = generate_chart_data(
                        chart_type=function_args.get("chart_type"),
                        data_points=function_args.get("data_points")
                    )
                else:
                    function_response = {"error": "Tool not found"}

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(function_response),
                })
            
            final_response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
            )
            return final_response.choices[0].message.content
        
        return response_message.content

    except Exception as e:
        return f"Error communicating with AI: {str(e)}"
