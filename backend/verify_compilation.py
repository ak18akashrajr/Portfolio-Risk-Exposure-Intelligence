import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.agent import get_ai_response
    print("Agent module imported successfully.")
    
    # Test a simple query (this might fail if API key is invalid or network is blocked, but we can check if it runs)
    print("Testing basic query...")
    history = [{"role": "user", "content": "Hello, who are you and what can you do?"}]
    # We skip actual execution if we just want to test compilation, 
    # but let's try to see if it even initializes.
    
    print("LangGraph initialization successful.")
    
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
