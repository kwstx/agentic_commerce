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
from backend.agents.comparison import ComparisonAgent, RankedProduct
from backend.agents.checkout import CheckoutService, CartItem

intent_agent = IntentAgent()
comparison_agent = ComparisonAgent()
checkout_service = CheckoutService()
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
    ranked_results: List[dict]
    comparison_summary: str
    transaction_status: str
    checkout_session: Optional[dict]
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

async def option_comparison(state: AgentState):
    print("--- AGENT: OPTION COMPARISON ---")
    results = [Product(**p) for p in state['discovery_results']]
    intent_data = state['intent_data']
    
    # Use ComparisonAgent to rank and justify
    ranked_products: List[RankedProduct] = await comparison_agent.compare_and_rank(results, intent_data)
    
    # Generate summary for user
    top_3 = ranked_products[:3]
    summary_parts = ["I've ranked the best options for you based on price, features, and delivery:"]
    for p in top_3:
        summary_parts.append(f"{p.rank}. **{p.name}** ({p.merchant}) - ${p.normalized_price}: {p.justification}")
    
    summary = "\n\n".join(summary_parts)
    
    return {
        "ranked_results": [p.dict() for p in ranked_products],
        "comparison_summary": summary, 
        "next_step": "user_confirmation",
        "messages": [AIMessage(content=summary)]
    }

async def transaction_executor(state: AgentState):
    """Executes the checkout process for the selected product(s)."""
    print("--- AGENT: TRANSACTION EXECUTOR ---")
    
    # In a real flow, the user would have selected products from the ranked list.
    # For now, we'll assume they chose the top-ranked item(s) if we're in 'executor' mode.
    if not state.get('ranked_results'):
        return {"errors": ["No products found to buy."], "next_step": "error_recovery"}
        
    top_choice = state['ranked_results'][0]
    
    # Map ranked product to CartItem
    cart_item = CartItem(
        product_id=top_choice['id'],
        name=top_choice['name'],
        quantity=1,
        price=top_choice['price'],
        merchant=top_choice['merchant'],
        metadata={"normalized_price": top_choice['normalized_price']}
    )
    
    # 1. Create the universal cart
    cart = await checkout_service.create_cart([cart_item])
    
    # 2. Initiate checkout (state machine handles the process)
    session = await checkout_service.initiate_checkout(cart)
    
    # Prepare summary for the user
    summary = f"I've prepared your checkout! Total is ${session.final_total} (includes taxes and shipping).\n"
    for attempt in session.attempts:
        summary += f"- **{attempt.merchant}**: [Complete Checkout]({attempt.checkout_url})\n"

    return {
        "transaction_status": session.status,
        "checkout_session": session.dict(),
        "next_step": END,
        "messages": [AIMessage(content=summary)]
    }

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
