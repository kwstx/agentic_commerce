from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate

class IntentConstraints(BaseModel):
    category: Optional[str] = Field(None, description="The broad category of the product or service.")
    search_query: str = Field(..., description="An optimized search query for product discovery APIs.")
    budget_ceiling: Optional[float] = Field(None, description="The maximum price the user is willing to pay.")
    must_have_features: List[str] = Field(default_factory=list, description="A list of non-negotiable features.")
    preferred_brands: List[str] = Field(default_factory=list, description="Brands the user prefers or specifically mentioned.")
    service_specifics: Dict[str, Any] = Field(default_factory=dict, description="Specifics for bookings or services (date, time, location, etc.).")
    currency: str = Field("USD", description="The currency for the budget.")
    discovery_strategy: Literal["parallel", "sequential"] = Field("parallel", description="Whether to search merchants in parallel or sequentially.")

class ExecutionStep(BaseModel):
    phase: Literal["discovery", "comparison", "transaction", "clarification"]
    description: str
    status: Literal["pending", "active", "completed", "skipped"] = "pending"

class ExecutionPlan(BaseModel):
    steps: List[ExecutionStep]
    estimated_tokens: Optional[int] = None

class ParsedIntent(BaseModel):
    is_ambiguous: bool = Field(..., description="Whether the request needs clarification before proceeding.")
    clarification_question: Optional[str] = Field(None, description="The question to ask the user if the intent is ambiguous.")
    extracted_constraints: IntentConstraints
    plan: ExecutionPlan
    summary: str = Field(..., description="A concise summary of the parsed intent for the user.")

class IntentAgent:
    def __init__(self, model: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.structured_llm = self.llm.with_structured_output(ParsedIntent)

    async def parse(self, user_input: str, history: List[BaseMessage] = []) -> ParsedIntent:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Intent Parsing and Planning Agent for an advanced commerce platform.
Your task is to analyze the user's natural language request and:
1. Extract key constraints (category, budget, features, brands, service specifics).
2. Determine if the request is ambiguous or missing critical information to proceed.
3. If ambiguous, formulate a polite clarifying question.
4. If clear, generate a step-by-step execution plan consisting of discovery, comparison, and transaction phases.
5. Provide a friendly summary of what you understood and what you're going to do.

Current focus: Commerce (products and services)."""),
            ("placeholder", "{history}"),
            ("human", "{input}")
        ])
        
        chain = prompt | self.structured_llm
        
        result = await chain.ainvoke({
            "input": user_input,
            "history": history
        })
        
        return result
