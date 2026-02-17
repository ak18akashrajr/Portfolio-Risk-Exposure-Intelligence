
import os
import sys

# Ensure the parent directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.agent import get_ai_response, llm_fast, llm_reasoning

def verify_optimization():
    print("Verifying Optimization...")
    
    # Check Environment Variable
    if os.environ.get("OTEL_SDK_DISABLED") != "true":
        print("FAIL: OTEL_SDK_DISABLED is not set to 'true'")
    else:
        print("PASS: OTEL_SDK_DISABLED is set to 'true'")

    # Check Model Configs
    print(f"Fast Model: {llm_fast.model}")
    print(f"Reasoning Model: {llm_reasoning.model}")
    
    if llm_fast.model != "gemini/gemini-1.5-flash":
        print("FAIL: Fast model is not gemini-1.5-flash")
    else:
        print("PASS: Fast model is gemini-1.5-flash")

    if llm_reasoning.model != "gemini/gemini-1.5-pro":
        print("FAIL: Reasoning model is not gemini-1.5-pro")
    else:
        print("PASS: Reasoning model is gemini-1.5-pro")

    # Run a simple query to ensure the system works
    print("\nRunning Test Query...")
    try:
        history = [{"role": "user", "content": "What is the price of RELIANCE.NS?"}]
        response = get_ai_response(history)
        print(f"Response: {response}")
        print("PASS: Query executed successfully (Rate Limits likely respected)")
    except Exception as e:
        print(f"FAIL: Query failed with error: {e}")

if __name__ == "__main__":
    verify_optimization()
