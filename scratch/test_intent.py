import asyncio
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from backend.agents.workflow import app_workflow

load_dotenv()

async def test_intent_parsing():
    print("--- Testing Intent Parsing and Planning ---")
    
    # Test Case 1: Specific Request
    user_request = "I need a waterproof hiking backpack for under $150. I prefer North Face or Osprey, and it must have a hydration sleeve."
    print(f"\nUser Input: {user_request}")
    
    state = {
        "messages": [HumanMessage(content=user_request)],
        "next_step": "intent_parser"
    }
    
    # Run only one step (intent_parser)
    # We can use astream to see what happens or just invoke
    result = await app_workflow.ainvoke(state)
    
    print("\nParsed Intent Constraints:")
    print(result.get('intent_data'))
    
    print("\nExecution Plan:")
    for i, step in enumerate(result.get('execution_plan', [])):
        print(f"{i+1}. [{step['phase'].upper()}] - {step['description']}")
        
    print("\nSummary for User:")
    # The last message from intent_parsing node
    print(result['messages'][-1].content)

    # Test Case 2: Ambiguous Request
    user_request_2 = "I want to buy something for my trip."
    print(f"\nUser Input 2: {user_request_2}")
    
    state_2 = {
        "messages": [HumanMessage(content=user_request_2)],
        "next_step": "intent_parser"
    }
    
    result_2 = await app_workflow.ainvoke(state_2)
    
    if result_2.get('is_ambiguous'):
        print("\nClarification Needed:")
        print(result_2['messages'][-1].content)
    else:
        print("\nParsed Intent Constraints (unexpectedly clear):")
        print(result_2.get('intent_data'))

if __name__ == "__main__":
    asyncio.run(test_intent_parsing())
