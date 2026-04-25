import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.workflow import intent_parser, AgentState
from langchain_core.messages import HumanMessage

@pytest.mark.asyncio
async def test_intent_parser_node():
    state: AgentState = {
        "messages": [HumanMessage(content="Find me a red dress under $50")],
        "next_step": "",
        "user_id": "test_user",
        "intent_data": {},
        "execution_plan": [],
        "is_ambiguous": False,
        "discovery_results": [],
        "ranked_results": [],
        "comparison_summary": "",
        "transaction_status": "",
        "checkout_session": None,
        "errors": []
    }
    
    with patch("backend.agents.workflow.intent_agent.parse", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value.is_ambiguous = False
        mock_parse.return_value.extracted_constraints.dict.return_value = {"category": "dress", "budget_ceiling": 50}
        mock_parse.return_value.plan.steps = []
        mock_parse.return_value.summary = "Parsed intent for red dress"
        
        result = await intent_parser(state)
        
        assert result["next_step"] == "discovery"
        assert result["intent_data"]["category"] == "dress"
        assert not result["is_ambiguous"]
