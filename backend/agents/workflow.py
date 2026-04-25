from typing import TypedDict, List, Annotated, Sequence, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_core.utils.function_calling import convert_to_openai_function
from backend.agents.discovery import DiscoveryService, DiscoveryQuery, Product
import operator
import os

# Initialize Services
discovery_service = DiscoveryService()
from backend.agents.intent import IntentAgent
intent_agent = IntentAgent()
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Removed mock tools as they are replaced by DiscoveryService logic

# Define the state of our workflow
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_step: str
    intent_data: dict # Extracted constraints
    execution_plan: List[dict]
    is_ambiguous: bool
    discovery_results: List[dict]
    comparison_summary: str
    transaction_status: str
    errors: List[str]

# --- Nodes ---

async def intent_parser(state: AgentState):
    print("--- AGENT: INTENT PARSER ---")
    user_input = state['messages'][-1].content
    history = state['messages'][:-1]
    
    # Use IntentAgent for deep analysis and planning
    parsed_intent = await intent_agent.parse(user_input, history)
    
    if parsed_intent.is_ambiguous:
        return {
            "is_ambiguous": True,
            "next_step": "ask_clarification",
            "messages": [AIMessage(content=parsed_intent.clarification_question)]
        }

    return {
        "intent_data": parsed_intent.extracted_constraints.dict(),
        "execution_plan": [step.dict() for step in parsed_intent.plan.steps],
        "is_ambiguous": False,
        "next_step": "discovery",
        "messages": [AIMessage(content=parsed_intent.summary)]
    }

async def product_discovery(state: AgentState):
    print("--- AGENT: PRODUCT DISCOVERY ---")
    constraints = state['intent_data']
    
    # Map constraints to DiscoveryQuery
    query = DiscoveryQuery(
        query=constraints.get('search_query', 'product'),
        max_price=constraints.get('budget_ceiling'),
        category=constraints.get('category'),
        # Add more mappings as needed
    )
    
    # Call the DiscoveryService (which handles caching and multi-source)
    results: List[Product] = await discovery_service.search(query)
    
    # Convert results to dicts for state
    results_dict = [p.dict() for p in results]
    
    return {
        "discovery_results": results_dict, 
        "next_step": "comparison" if results else "error_recovery",
        "messages": [AIMessage(content=f"Found {len(results)} matches across Shopify, Amazon, and Google Shopping.")]
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
    {"discovery": "discovery", "ask_clarification": END, "error_recovery": "error_recovery"}
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
