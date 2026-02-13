
import os
import sys

# Ensure the parent directory is in the path so we can import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.agent import get_market_data, get_portfolio_analysis, place_order_tool, execute_sql_query, delete_transaction_tool
from backend.utils import get_market_data_mock
from backend.ingestion import add_manual_transaction
from backend.models import Holding, Transaction
from sqlmodel import Session, text, select
from backend.database import engine, create_db_and_tables

def test_mock_fallback():
    print("Testing Mock Fallback...")
    # This should return mock data since we expect yfinance to fail or be slow in certain environments,
    # or we can force it by testing get_market_data_mock directly.
    mock_data = get_market_data_mock("RELIANCE.NS")
    print(f"Mock Data: {mock_data}")
    assert mock_data["status"] == "stale-data only"
    print("Mock Fallback Test Passed")

def test_sql_query():
    print("Testing SQL Query Tool...")
    # Test a simple count query
    result = execute_sql_query('SELECT COUNT(*) as count FROM "transaction"')
    print(f"SQL Result: {result}")
    assert result["status"] == "success"
    assert "count" in result["data"][0]
    print("SQL Query Tool Test Passed")

def test_place_order():
    print("Testing Order Placement...")
    # Test placing an order
    result = place_order_tool(
        symbol="TEST.NS",
        tx_type="BUY",
        quantity=5,
        price=500.0,
        exchange="NSE"
    )
    print(f"Order Result: {result}")
    assert result["status"] == "success"
    assert "order_id" in result
    print("Order Placement Test Passed")

def test_portfolio_analysis():
    print("Testing Portfolio Analysis...")
    analysis = get_portfolio_analysis()
    print(f"Analysis Summary: {analysis}")
    assert "holdings" in analysis
    assert "total_invested_value" in analysis
    print("Portfolio Analysis Test Passed")

def test_deletion_sync():
    print("Testing Deletion Sync...")
    
    # Pre-cleanup: Delete any existing SYNC_TEST data
    with Session(engine) as session:
        session.exec(text('DELETE FROM "transaction" WHERE symbol = "SYNC_TEST"'))
        session.exec(text('DELETE FROM holding WHERE symbol = "SYNC_TEST"'))
        session.commit()

    # 1. Add a transaction in one session
    with Session(engine) as session:
        tx = add_manual_transaction(
            session=session,
            symbol="SYNC_TEST",
            tx_type="BUY",
            quantity=10,
            price=1000.0,
            exchange="NSE"
        )
        order_id = tx.order_id
        session.commit() # Ensure it's persisted
        
        # Verify holding exists
        holding = session.get(Holding, "SYNC_TEST")
        assert holding is not None, "Holding should exist after purchase"
        assert holding.quantity == 10
    
    # 2. Delete the transaction via tool (has its own session)
    delete_result = delete_transaction_tool(order_id=order_id)
    assert delete_result["status"] == "success"
    
    # 3. Verify holding is gone in a NEW session
    with Session(engine) as session:
        holding_after = session.get(Holding, "SYNC_TEST")
        assert holding_after is None, "Holding should be deleted when quantity reaches zero"
        
    print("Deletion Sync Test Passed")

def test_bulk_deletion():
    print("Testing Bulk Deletion...")
    symbol = "BULK_TEST"
    
    # Pre-cleanup
    with Session(engine) as session:
        session.exec(text(f'DELETE FROM "transaction" WHERE symbol = "{symbol}"'))
        session.exec(text(f'DELETE FROM holding WHERE symbol = "{symbol}"'))
        session.commit()

    # 1. Add multiple transactions
    with Session(engine) as session:
        add_manual_transaction(session, symbol, "BUY", 10, 100.0, "NSE")
        add_manual_transaction(session, symbol, "BUY", 20, 200.0, "NSE")
        session.commit()
    
    # 2. Verify holding exists
    with Session(engine) as session:
        holding = session.get(Holding, symbol)
        assert holding is not None
        assert holding.quantity == 30
    
    # 3. Bulk delete via tool
    result = delete_transaction_tool(symbol=symbol)
    assert result["status"] == "success"
    assert "All 2 transactions" in result["message"]
    
    # 4. Verify everything is gone
    with Session(engine) as session:
        txs = session.exec(select(Transaction).where(Transaction.symbol == symbol)).all()
        assert len(txs) == 0
        holding = session.get(Holding, symbol)
        assert holding is None

    print("Bulk Deletion Test Passed")

if __name__ == "__main__":
    create_db_and_tables()
    try:
        test_mock_fallback()
        test_sql_query()
        test_place_order()
        test_portfolio_analysis()
        test_deletion_sync()
        test_bulk_deletion()
        print("\nAll backend logic tests passed!")
    except Exception as e:
        print(f"\nTests Failed: {e}")
        sys.exit(1)
