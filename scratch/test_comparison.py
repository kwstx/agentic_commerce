import asyncio
import json
from backend.agents.discovery import Product
from backend.agents.comparison import ComparisonAgent
from unittest.mock import MagicMock, AsyncMock, patch

# Mock LLM response
class MockJustification:
    def __init__(self):
        self.justifications = {
            "Pro Backpack": "Top ranked due to matching all feature requirements and high rating.",
            "Middle Pack": "Decent balance of price and features, though shipping takes longer.",
            "Budget Pack": "Most affordable option, but lacks waterproofing and fast delivery."
        }

async def test_comparison():
    with patch("backend.agents.comparison.ChatOpenAI") as mock_llm_class:
        mock_llm_instance = mock_llm_class.return_value
        
        # Mock structured output
        mock_structured = AsyncMock()
        mock_structured.ainvoke.return_value = MockJustification()
        mock_llm_instance.with_structured_output.return_value = mock_structured
        
        agent = ComparisonAgent()
        
        # Mock data
        products = [
            Product(
                id="1", source="amazon", name="Pro Backpack", price=150.0, 
                currency="USD", normalized_price=150.0, url="http://test.com/1",
                availability=True, rating=4.8, merchant="Amazon",
                delivery_estimate="Tomorrow", specifications={"Waterproof": "Yes", "Capacity": "30L"}
            ),
            Product(
                id="2", source="shopify", name="Budget Pack", price=50.0, 
                currency="USD", normalized_price=50.0, url="http://test.com/2",
                availability=True, rating=4.0, merchant="SmallShop",
                delivery_estimate="5 days", specifications={"Waterproof": "No", "Capacity": "20L"}
            ),
            Product(
                id="3", source="google_shopping", name="Middle Pack", price=100.0, 
                currency="USD", normalized_price=100.0, url="http://test.com/3",
                availability=True, rating=4.5, merchant="Backcountry",
                delivery_estimate="3 days", specifications={"Waterproof": "Yes", "Capacity": "25L"}
            )
        ]
        
        intent = {
            "search_query": "waterproof backpack",
            "must_have_features": ["Waterproof", "30L"]
        }
        
        print("--- Testing Comparison Engine ---")
        ranked = await agent.compare_and_rank(products, intent)
        
        for p in ranked:
            print(f"Rank {p.rank}: {p.name} - Score: {p.score}")
            print(f"  Price: ${p.price}, Rating: {p.rating}, Merchant: {p.merchant}")
            print(f"  Justification: {p.justification}")
            print("-" * 20)

        # Test weight refinement
        print("\n--- Testing Weight Refinement (Selecting Budget Pack) ---")
        initial_weights = agent.weights.dict()
        print(f"Initial weights: {initial_weights}")
        
        agent.refine_weights("2", ranked, intent)
        
        new_weights = agent.weights.dict()
        print(f"Refined weights: {new_weights}")

if __name__ == "__main__":
    asyncio.run(test_comparison())
