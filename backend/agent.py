import os
import json
from groq import Groq
from dotenv import load_dotenv
from sqlmodel import Session, select, func
from .database import engine
from .models import Transaction, Holding
from datetime import datetime

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Tool Functions ---

def get_holdings_summary():
    """Returns a summary of current stock holdings."""
    with Session(engine) as session:
        statement = select(Holding)
        results = session.exec(statement).all()
        return [{"name": h.stock_name, "symbol": h.symbol, "qty": h.quantity, "avg_price": h.avg_price, "total": h.total_invested, "geo": h.geography, "cat": h.category} for h in results]

def get_transaction_stats(month: int = None, year: int = None):
    """Returns aggregated transaction stats (Total Buy/Sell) for a specific month and year."""
    with Session(engine) as session:
        statement = select(Transaction)
        if year:
            statement = statement.where(func.strftime('%Y', Transaction.execution_time) == str(year))
        if month:
            # Pad month with leading zero if needed
            month_str = f"{month:02d}"
            statement = statement.where(func.strftime('%m', Transaction.execution_time) == month_str)
        
        results = session.exec(statement).all()
        
        buys = sum(t.price for t in results if t.type.upper() == "BUY")
        sells = sum(t.price for t in results if t.type.upper() == "SELL")
        count = len(results)
        
        return {
            "period": f"{month if month else 'All'}/{year if year else 'All'}",
            "total_buy_value": buys,
            "total_sell_value": sells,
            "transaction_count": count,
            "transactions": [{"date": t.execution_time.strftime("%Y-%m-%d"), "name": t.stock_name, "type": t.type, "qty": t.quantity, "price": t.price} for t in results]
        }

# --- Tool Definitions for Groq ---

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_holdings_summary",
            "description": "Get a summary of current stock holdings, including quantity and total value.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transaction_stats",
            "description": "Get transaction statistics and a list of transactions for a specific month and year.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "integer", "description": "The month (1-12)"},
                    "year": {"type": "integer", "description": "The year (e.g., 2024)"},
                },
                "required": ["year"],
            },
        },
    }
]

def get_ai_response(history: list):
    """
    history is a list of dicts: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    system_prompt = {
        "role": "system",
        "content": (
            "You are a sophisticated Portfolio Assistant. Your goals are:\n"
            "1. PROVIDE DETAIL: Instead of brief answers, provide specific valuations, quantities, and breakdown percentages where relevant.\n"
            "2. DATA GROUNDING: Use the provided tools to fetch real data before answering. Never hallucinate.\n"
            "3. PROACTIVE FOLLOW-UP: ALWAYS end your response with a relevant, open-ended follow-up question that helps the user explore their portfolio deeper.\n"
            "4. CONVERSATIONAL: Maintain context from the previous chat history provided."
        )
    }
    
    # Start with system prompt and history
    messages = [system_prompt] + history

    try:
        # First call to see if tools are needed
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=4096,
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "get_holdings_summary":
                    function_response = get_holdings_summary()
                elif function_name == "get_transaction_stats":
                    function_response = get_transaction_stats(
                        month=function_args.get("month"),
                        year=function_args.get("year")
                    )
                else:
                    function_response = "Error: Tool not found"

                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response),
                    }
                )
            
            # Second call to get final answer
            final_response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
            )
            return final_response.choices[0].message.content
        
        return response_message.content

    except Exception as e:
        return f"Error communicating with AI: {str(e)}"
