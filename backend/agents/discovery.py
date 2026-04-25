from typing import List, Optional, Dict, Any, Union, Literal
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
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Unified Internal Schema
class Product(BaseModel):
    id: str
    source: str  # 'shopify', 'amazon', 'google_shopping', 'web_scrape'
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    normalized_price: Optional[float] = None  # Price in user's preferred currency
    normalized_currency: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    availability: bool
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    delivery_estimate: Optional[str] = None
    merchant: str
    similarity_score: Optional[float] = 0.0

class UserPreferences(BaseModel):
    preferred_currency: str = "USD"
    min_rating: Optional[float] = None
    ethical_filtering: bool = False
    preferred_merchants: List[str] = []

class DiscoveryQuery(BaseModel):
    query: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    category: Optional[str] = None
    limit: int = 20
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    strategy: Literal["parallel", "sequential"] = "parallel"

class CurrencyService:
    def __init__(self):
        self.api_url = "https://api.exchangerate-api.com/v4/latest/" # Using a free API for demonstration
        self.cache_ttl = 86400  # 24 hours

    async def get_exchange_rate(self, from_curr: str, to_curr: str) -> float:
        if from_curr == to_curr:
            return 1.0
        
        cache_key = f"fx_rate:{from_curr}"
        cached_rates = redis_client.get(cache_key)
        
        if cached_rates:
            rates = json.loads(cached_rates)
        else:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{self.api_url}{from_curr}", timeout=5)
                    resp.raise_for_status()
                    data = resp.json()
                    rates = data.get("rates", {})
                    redis_client.set(cache_key, json.dumps(rates), ex=self.cache_ttl)
            except Exception as e:
                print(f"Currency conversion error: {e}")
                # Fallback to some common rates if API fails
                fallback_rates = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 150.0}
                return fallback_rates.get(to_curr, 1.0) / fallback_rates.get(from_curr, 1.0)

        return rates.get(to_curr, 1.0)

    async def convert_price(self, amount: float, from_curr: str, to_curr: str) -> float:
        rate = await self.get_exchange_rate(from_curr, to_curr)
        return round(amount * rate, 2)

class DeduplicationService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.threshold = 0.85 # Similarity threshold for merging

    def deduplicate(self, products: List[Product]) -> List[Product]:
        if not products:
            return []

        # 1. Exact match pass (Same merchant and ID/SKU or URL)
        unique_products = []
        seen_keys = set()
        
        for p in products:
            # Create a unique key for exact matches
            key = f"{p.merchant}:{p.id}" if p.id else p.url
            if key not in seen_keys:
                unique_products.append(p)
                seen_keys.add(key)
        
        if len(unique_products) < 2:
            return unique_products

        # 2. Semantic deduplication pass
        # Encode product identifying text (Name + Description)
        product_texts = [f"{p.name} {p.description or ''}" for p in unique_products]
        embeddings = self.model.encode(product_texts)
        
        similarity_matrix = cosine_similarity(embeddings)
        
        final_products = []
        merged_indices = set()
        
        for i in range(len(unique_products)):
            if i in merged_indices:
                continue
            
            current_product = unique_products[i]
            # Find similar products
            similar_indices = np.where(similarity_matrix[i] > self.threshold)[0]
            
            # Merge logic: if multiple sources have the same product, pick the best one or aggregate
            # For now, we pick the one with the lowest price or best rating
            best_p = current_product
            for idx in similar_indices:
                if idx == i: continue
                other_p = unique_products[idx]
                
                # Simple merge: prefer higher rating or lower price
                if (other_p.rating or 0) > (best_p.rating or 0):
                    best_p = other_p
                elif (other_p.rating or 0) == (best_p.rating or 0) and other_p.price < best_p.price:
                    best_p = other_p
                
                merged_indices.add(idx)
            
            final_products.append(best_p)
            merged_indices.add(i)
            
        return final_products

class DiscoveryService:
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour
        self.currency_service = CurrencyService()
        self.dedup_service = DeduplicationService()

    def _generate_cache_key(self, query: DiscoveryQuery):
        query_dict = query.dict()
        # Remove volatile pref if needed, but currency matters
        query_str = json.dumps(query_dict, sort_keys=True)
        return f"discovery:search:{hashlib.md5(query_str.encode()).hexdigest()}"

    async def search(self, query: DiscoveryQuery) -> List[Product]:
        cache_key = self._generate_cache_key(query)
        cached_results = redis_client.get(cache_key)
        if cached_results:
            print("--- Caching hit for discovery ---")
            return [Product(**p) for p in json.loads(cached_results)]

        print(f"--- Running discovery (Strategy: {query.strategy}) for: {query.query} ---")
        
        flat_results = []
        sources = [
            self._search_shopify(query),
            self._search_amazon(query),
            self._search_google_shopping(query)
        ]

        if query.strategy == "parallel":
            results = await asyncio.gather(*sources)
            flat_results = [item for sublist in results for item in sublist]
        else:
            # Sequential execution
            for source_task in sources:
                res = await source_task
                flat_results.extend(res)
                # If we have enough results, we could stop early in sequential mode
                if len(flat_results) >= query.limit:
                    break

        if not flat_results:
            print("--- No API results, triggering fallback browser discovery ---")
            flat_results = await self._fallback_browser_discovery(query)

        # 1. Cleaning and Enrichment (Currency, etc.)
        processed_results = await self._process_results(flat_results, query)

        # 2. Deduplication
        deduplicated_results = self.dedup_service.deduplicate(processed_results)

        # 3. Dynamic Filtering
        final_results = self._apply_dynamic_filters(deduplicated_results, query)

        # Limit results
        final_results = final_results[:query.limit]

        # Store in cache
        redis_client.set(cache_key, json.dumps([p.dict() for p in final_results]), ex=self.cache_ttl)
        
        return final_results

    async def _process_results(self, products: List[Product], query: DiscoveryQuery) -> List[Product]:
        """Cleans and enriches data, handles currency conversion."""
        target_currency = query.user_preferences.preferred_currency
        
        enriched = []
        for p in products:
            try:
                # Convert price to user currency
                p.normalized_price = await self.currency_service.convert_price(
                    p.price, p.currency, target_currency
                )
                p.normalized_currency = target_currency
                
                # Basic cleaning
                p.name = p.name.strip()
                if p.description:
                    p.description = p.description.strip()
                
                enriched.append(p)
            except Exception as e:
                print(f"Error processing product {p.id}: {e}")
                continue
        
        return enriched

    def _apply_dynamic_filters(self, products: List[Product], query: DiscoveryQuery) -> List[Product]:
        """Applies filters based on user preferences and query constraints."""
        filtered = []
        prefs = query.user_preferences
        
        for p in products:
            # 1. Price Filtering (using normalized price)
            if query.min_price and p.normalized_price < query.min_price:
                continue
            if query.max_price and p.normalized_price > query.max_price:
                continue
            
            # 2. Rating Filtering
            if prefs.min_rating and (p.rating or 0) < prefs.min_rating:
                continue
                
            filtered.append(p)
        
        # 4. Semantic Ranking
        if filtered:
            filtered = self._rank_semantically(filtered, query.query)
            
        # Sort by similarity first, then rating/price
        return sorted(filtered, key=lambda x: (x.similarity_score, x.rating or 0, -(x.normalized_price or 0)), reverse=True)

    def _rank_semantically(self, products: List[Product], search_query: str) -> List[Product]:
        """Ranks products based on semantic similarity to the search query."""
        if not products:
            return []
            
        product_texts = [f"{p.name} {p.description or ''}" for p in products]
        # Use dedup_service's model for efficiency
        query_embedding = self.dedup_service.model.encode([search_query])
        product_embeddings = self.dedup_service.model.encode(product_texts)
        
        similarities = cosine_similarity(query_embedding, product_embeddings)[0]
        
        for i, p in enumerate(products):
            p.similarity_score = float(similarities[i])
            
        return products

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
