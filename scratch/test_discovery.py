import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Mock redis BEFORE importing discovery
mock_redis = MagicMock()
mock_redis.get.return_value = None
with patch('redis.Redis', return_value=mock_redis):
    # Add project root to path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from backend.agents.discovery import DiscoveryService, DiscoveryQuery, UserPreferences, Product

async def test_discovery():
    discovery = DiscoveryService()
    
    # Customize the mock search results for testing
    async def mock_shopify(query):
        return [
            Product(
                id="sh-1", source="shopify", name="AquaShield Pro 30L Waterproof Backpack", 
                description="The ultimate waterproof backpack for hikers.",
                price=120.00, currency="EUR", url="https://store.shopify.com/aqua",
                availability=True, rating=4.8, merchant="Outdoor Gear Co"
            )
        ]

    async def mock_amazon(query):
        return [
            Product(
                id="amz-1", source="amazon", name="Summit Trail Pack - 30L AquaShield", 
                description="Summit Trail waterproof pack with 30L capacity.",
                price=145.00, currency="USD", url="https://amazon.com/summit",
                availability=True, rating=4.5, merchant="Amazon"
            )
        ]

    async def mock_google(query):
        return [
            Product(
                id="gs-1", source="google_shopping", name="Cheap Basic Bag", 
                description="A very basic bag, not waterproof.",
                price=25.00, currency="USD", url="https://google.com/bag",
                availability=True, rating=3.1, merchant="Discounters"
            )
        ]

    discovery._search_shopify = mock_shopify
    discovery._search_amazon = mock_amazon
    discovery._search_google_shopping = mock_google

    # Test Query
    query = DiscoveryQuery(
        query="waterproof 30L backpack",
        user_preferences=UserPreferences(preferred_currency="USD", min_rating=4.0),
        limit=5
    )

    print(f"Searching for: {query.query}")
    results = await discovery.search(query)

    print(f"\n--- Found {len(results)} results ---")
    for p in results:
        print(f"Source: {p.source}")
        print(f"Name: {p.name}")
        print(f"Price: {p.price} {p.currency} -> {p.normalized_price} {p.normalized_currency}")
        print(f"Rating: {p.rating}")
        print(f"Similarity Score: {p.similarity_score:.4f}")
        print("-" * 20)

    # Verify Deduplication (the two 30L backpacks should merge)
    # Note: Depending on threshold, they might or might not merge. 
    # With "AquaShield" in both, they should be very similar.

if __name__ == "__main__":
    asyncio.run(test_discovery())
