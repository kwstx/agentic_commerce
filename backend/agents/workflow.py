from typing import TypedDict, List, Annotated, Sequence, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
import operator
from langchain_core.tools import tool

@tool
def search_products(query: str, max_price: float):
    """Search for products matching the query and within the price range."""
    # MOCK tool implementation
    return [
        {"id": "p1", "name": "AquaShield Pro 30L", "price": 129.99, "rating": 4.8},
        {"id": "p2", "name": "Summit Trail Pack", "price": 145.00, "rating": 4.5}
    ]

@tool
def get_user_preferences(user_id: str):
    """Retrieve user preferences from the database."""
    return {"favorite_colors": ["blue", "black"], "size": "L"}

# Define the state of our workflow
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_step: str
    intent_data: dict
    discovery_results: List[dict]
    comparison_summary: str
    transaction_status: str
    errors: List[str]

# --- Nodes ---

def intent_parser(state: AgentState):
    print("--- AGENT: INTENT PARSER ---")
    # In reality: model.invoke([system_msg, HumanMessage(user_input)])
    user_input = state['messages'][-1].content
    # MOCK: Extracting from "Find me a waterproof hiking backpack under $150"
    intent = {
        "item": "backpack",
        "specs": ["waterproof", "hiking"],
        "max_price": 150
    }
    return {
        "intent_data": intent, 
        "next_step": "discovery",
        "messages": [AIMessage(content=f"Parsed intent: {intent['item']} with budget ${intent['max_price']}")]
    }

def product_discovery(state: AgentState):
    print("--- AGENT: PRODUCT DISCOVERY ---")
    intent = state['intent_data']
    # MOCK: Search results based on intent
    results = [
        {"id": "p1", "name": "AquaShield Pro 30L", "price": 129.99, "rating": 4.8, "shipping": "Free"},
        {"id": "p2", "name": "Summit Trail Pack", "price": 145.00, "rating": 4.5, "shipping": "$10"},
        {"id": "p3", "name": "DryHike Elite", "price": 110.00, "rating": 4.2, "shipping": "Free"}
    ]
    return {
        "discovery_results": results, 
        "next_step": "comparison",
        "messages": [AIMessage(content=f"Found {len(results)} matches for your search.")]
    }

def option_comparison(state: AgentState):
    print("--- AGENT: OPTION COMPARISON ---")
    results = state['discovery_results']
    # MOCK: Ranking and comparison
    summary = "I found 3 great options. The 'AquaShield Pro 30L' is the best value at $129.99 with top reviews, while 'DryHike Elite' is the most budget-friendly at $110."
    return {
        "comparison_summary": summary, 
        "next_step": "user_confirmation",
        "messages": [AIMessage(content=summary)]
    }

def transaction_executor(state: AgentState):
    # Logic to execute transaction
    print("--- TRANSACTION EXECUTOR ---")
    return {"transaction_status": "success", "next_step": END}

def error_recovery(state: AgentState):
    # Logic to handle errors
    print("--- ERROR RECOVERY ---")
    return {"next_step": "intent_parser"} # Try again or ask for clarification

# --- Supervisor ---

def supervisor(state: AgentState):
    # Logic to decide the next agent based on state and message history
    return state.get("next_step", "intent_parser")

# --- Workflow Definition ---

workflow = StateGraph(AgentState)

workflow.add_node("intent_parser", intent_parser)
workflow.add_node("discovery", product_discovery)
workflow.add_node("comparison", option_comparison)
workflow.add_node("executor", transaction_executor)
workflow.add_node("error_recovery", error_recovery)

workflow.set_entry_point("intent_parser")

# Router logic
workflow.add_conditional_edges(
    "intent_parser",
    lambda x: x["next_step"],
    {"discovery": "discovery", "error_recovery": "error_recovery"}
)
workflow.add_conditional_edges(
    "discovery",
    lambda x: x["next_step"],
    {"comparison": "comparison", "error_recovery": "error_recovery"}
)
workflow.add_conditional_edges(
    "comparison",
    lambda x: x["next_step"],
    {"user_confirmation": END, "executor": "executor", "error_recovery": "error_recovery"}
)
workflow.add_edge("executor", END)
workflow.add_edge("error_recovery", "intent_parser")

app_workflow = workflow.compile()
