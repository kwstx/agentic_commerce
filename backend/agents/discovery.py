from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import asyncio
import hashlib
from backend.redis_client import redis_client
import httpx
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

# Unified Internal Schema
class Product(BaseModel):
    id: str
    source: str  # 'shopify', 'amazon', 'google_shopping', 'web_scrape'
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    url: str
    image_url: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    availability: bool
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    delivery_estimate: Optional[str] = None
    merchant: str

class DiscoveryQuery(BaseModel):
    query: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    category: Optional[str] = None
    limit: int = 10

class DiscoveryService:
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour

    def _generate_cache_key(self, query: DiscoveryQuery):
        query_str = json.dumps(query.dict(), sort_keys=True)
        return f"discovery:search:{hashlib.md5(query_str.encode()).hexdigest()}"

    async def search(self, query: DiscoveryQuery) -> List[Product]:
        cache_key = self._generate_cache_key(query)
        cached_results = redis_client.get(cache_key)
        if cached_results:
            print("--- Caching hit for discovery ---")
            return [Product(**p) for p in json.loads(cached_results)]

        print(f"--- Running discovery for: {query.query} ---")
        
        # Parallel execution of multiple discovery sources
        tasks = [
            self._search_shopify(query),
            self._search_amazon(query),
            self._search_google_shopping(query)
        ]
        
        # If no results from APIs, try fallback scraping (limited)
        results = await asyncio.gather(*tasks)
        flat_results = [item for sublist in results for item in sublist]

        if not flat_results:
            print("--- No API results, triggering fallback browser discovery ---")
            flat_results = await self._fallback_browser_discovery(query)

        # Store in cache
        redis_client.set(cache_key, json.dumps([p.dict() for p in flat_results]), ex=self.cache_ttl)
        
        return flat_results

    async def _search_shopify(self, query: DiscoveryQuery) -> List[Product]:
        """Shopify Storefront GraphQL Integration"""
        # MOCK Implementation - In reality, would fetch from configured Shopify stores
        try:
            # Example GraphQL query
            # { products(first: 10, query: "title:backpack") { edges { node { id title description ... } } } }
            await asyncio.sleep(0.5) # Simulate IO
            if "backpack" in query.query.lower():
                return [
                    Product(
                        id="sh-1", source="shopify", name="AquaShield Pro 30L", 
                        price=129.99, url="https://store.shopify.com/aqua-shield",
                        availability=True, rating=4.8, merchant="Outdoor Gear Co"
                    )
                ]
            return []
        except Exception as e:
            print(f"Shopify Error: {e}")
            return []

    async def _search_amazon(self, query: DiscoveryQuery) -> List[Product]:
        """Amazon PAAPI Integration"""
        # MOCK Implementation
        await asyncio.sleep(0.7)
        if "backpack" in query.query.lower():
            return [
                Product(
                    id="amz-1", source="amazon", name="Summit Trail Pack", 
                    price=145.00, url="https://amazon.com/summit-trail",
                    availability=True, rating=4.5, rating_count=1200, 
                    delivery_estimate="Tomorrow", merchant="Amazon"
                )
            ]
        return []

    async def _search_google_shopping(self, query: DiscoveryQuery) -> List[Product]:
        """Google Shopping Integration (via API or parsing)"""
        # MOCK Implementation
        await asyncio.sleep(0.6)
        if "backpack" in query.query.lower():
            return [
                Product(
                    id="gs-1", source="google_shopping", name="DryHike Elite", 
                    price=110.00, url="https://google.com/shopping/dryhike",
                    availability=True, rating=4.2, merchant="Backcountry"
                )
            ]
        return []

    async def _fallback_browser_discovery(self, query: DiscoveryQuery) -> List[Product]:
        """Ethical fallback using Playwright with robots.txt compliance"""
        results = []
        target_merchant = "https://example-merchant.com"
        
        # Check robots.txt (Simplified)
        if not await self._is_allowed_by_robots(target_merchant):
            print(f"--- ROBOTS.TXT: Access to {target_merchant} is restricted. Skipping. ---")
            return []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Implementation of rate limiting
            await asyncio.sleep(1.0) # Simple 1s delay
            
            search_url = f"{target_merchant}/search?q={query.query}"
            try:
                # Set a clear User-Agent identifying the agent
                await page.set_extra_http_headers({"User-Agent": "AntigravityCommerceBot/1.0 (Ethical Discovery Agent)"})
                
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                # ... extraction logic ...
                # results.append(Product(...))
                
                await browser.close()
            except Exception as e:
                print(f"Browser discovery error: {e}")
                await browser.close()
                
        return results

    async def _is_allowed_by_robots(self, url: str) -> bool:
        """Check robots.txt for the Given merchant URL"""
        parsed = urlparse(url)
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(robots_url, timeout=5)
                if resp.status_code == 200:
                    # In a production system, use a proper robots.txt parser like 'urllib.robotparser'
                    # For this implementation, we simulate checking for Disallow: /search
                    if "Disallow: /search" in resp.text:
                        return False
                return True
        except:
            return True # Default to conservative true or handle as preferred
