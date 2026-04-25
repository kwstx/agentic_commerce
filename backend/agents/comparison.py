from typing import List, Dict, Any, Optional
import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.discovery import Product
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
import os

class ScoringWeights(BaseModel):
    price: float = 0.4
    feature_match: float = 0.2
    rating: float = 0.15  # Using rating as organic proxy for sentiment/quality
    delivery_speed: float = 0.15
    return_policy: float = 0.1

class RankedProduct(Product):
    score: float = 0.0
    rank: int = 0
    justification: str = ""

class ComparisonAgent:
    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.2)
        self.weights_file = "backend/data/user_weights.json"
        self._ensure_data_dir()
        self.weights = self._load_weights()

    def _ensure_data_dir(self):
        os.makedirs("backend/data", exist_ok=True)

    def _load_weights(self) -> ScoringWeights:
        if os.path.exists(self.weights_file):
            try:
                with open(self.weights_file, 'r') as f:
                    data = json.load(f)
                    return ScoringWeights(**data)
            except Exception as e:
                print(f"Error loading weights: {e}")
        return ScoringWeights()

    def _save_weights(self):
        with open(self.weights_file, 'w') as f:
            json.dump(self.weights.dict(), f)

    def refine_weights(self, selected_id: str, candidates: List[RankedProduct], user_intent: Dict[str, Any]):
        """
        ML refinement: Trains a LinearRegression model on the user's choice to adjust weights.
        The selected product is treated as a positive sample, others as negatives.
        """
        if len(candidates) < 2:
            return

        # 1. Prepare Features (normalized data)
        norm_data = self._prepare_scoring_matrix(candidates, user_intent)
        
        X = []
        y = []
        
        feature_keys = ["price", "feature_match", "rating", "delivery", "return"]
        
        for i, p in enumerate(candidates):
            row = [norm_data[key][i] for key in feature_keys]
            X.append(row)
            y.append(1.0 if p.id == selected_id else 0.0)
            
        # 2. Fit small model
        model = LinearRegression()
        model.fit(X, y)
        
        # 3. Extract and normalize coefficients as new weights
        # We want to blend them with current weights to avoid drastic shifts (learning rate)
        lr = 0.2
        coeffs = model.coef_
        
        # Ensure non-negative and normalize
        coeffs = np.maximum(coeffs, 0.01) # Minimum weight to keep it functional
        if coeffs.sum() > 0:
            coeffs /= coeffs.sum()
            
            # Blend
            self.weights.price = (1 - lr) * self.weights.price + lr * coeffs[0]
            self.weights.feature_match = (1 - lr) * self.weights.feature_match + lr * coeffs[1]
            self.weights.rating = (1 - lr) * self.weights.rating + lr * coeffs[2]
            self.weights.delivery_speed = (1 - lr) * self.weights.delivery_speed + lr * coeffs[3]
            self.weights.return_policy = (1 - lr) * self.weights.return_policy + lr * coeffs[4]
            
            self._save_weights()
            print(f"Weights refined: {self.weights}")

    async def compare_and_rank(self, products: List[Product], user_intent: Dict[str, Any]) -> List[RankedProduct]:
        if not products:
            return []

        # 1. Normalize Attributes
        normalized_data = self._prepare_scoring_matrix(products, user_intent)
        
        # 2. Apply Multi-Criteria Scoring
        scored_products = self._apply_scoring(products, normalized_data)
        
        # 3. Generate Natural Language Explanations
        ranked_products = await self._generate_justifications(scored_products, user_intent)
        
        # Sort by score descending
        ranked_products.sort(key=lambda x: x.score, reverse=True)
        
        # Assign ranks
        for i, p in enumerate(ranked_products):
            p.rank = i + 1
            
        return ranked_products

    def _prepare_scoring_matrix(self, products: List[Product], user_intent: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """Maps product attributes to a 0-1 scale for scoring."""
        count = len(products)
        raw_scores = {
            "price": np.zeros(count),
            "feature_match": np.zeros(count),
            "rating": np.zeros(count),
            "delivery": np.zeros(count),
            "return": np.zeros(count)
        }

        must_haves = user_intent.get("must_have_features", [])

        for i, p in enumerate(products):
            # Price: Lower is better, but we normalize it. Use 1/price or similar.
            # We'll use actual price and then invert the normalization.
            raw_scores["price"][i] = p.normalized_price or p.price
            
            # Feature Match: Percentage of must-have features found in description/specs
            if must_haves:
                matches = 0
                desc = (p.name + " " + (p.description or "")).lower()
                for feat in must_haves:
                    if feat.lower() in desc:
                        matches += 1
                raw_scores["feature_match"][i] = matches / len(must_haves)
            else:
                raw_scores["feature_match"][i] = 1.0 # No constraints is a match

            # Rating: 0-5 scale usually
            raw_scores["rating"][i] = p.rating or 0.0

            # Delivery Speed: Estimate logic
            # Mocking: 'Tomorrow'=10, '2-3 days'=7, '1 week'=3, None=0
            delivery = (p.delivery_estimate or "").lower()
            if "tomorrow" in delivery or "today" in delivery:
                raw_scores["delivery"][i] = 10
            elif "2" in delivery or "3" in delivery:
                raw_scores["delivery"][i] = 7
            elif "4" in delivery or "5" in delivery:
                raw_scores["delivery"][i] = 5
            else:
                raw_scores["delivery"][i] = 2

            # Return Policy Quality: Mocking based on source
            # Amazon/Big retailers usually better: 10, smaller: 5
            if p.source == "amazon":
                raw_scores["return"][i] = 10
            elif p.source == "shopify":
                raw_scores["return"][i] = 7
            else:
                raw_scores["return"][i] = 5

        # Normalize all to 0-1
        scaler = MinMaxScaler()
        
        # Price needs inversion: higher price -> lower score
        # We handle this by taking (max - val) / (max - min)
        prices = raw_scores["price"].reshape(-1, 1)
        if count > 1:
            p_min, p_max = prices.min(), prices.max()
            if p_max != p_min:
                raw_scores["price"] = (p_max - raw_scores["price"]) / (p_max - p_min)
            else:
                raw_scores["price"] = np.ones(count)
        else:
            raw_scores["price"] = np.ones(count)

        # Others are higher is better
        for key in ["feature_match", "rating", "delivery", "return"]:
            vals = raw_scores[key].reshape(-1, 1)
            if count > 1 and vals.max() != vals.min():
                raw_scores[key] = scaler.fit_transform(vals).flatten()
            else:
                raw_scores[key] = np.ones(count) if vals.max() > 0 else np.zeros(count)

        return raw_scores

    def _apply_scoring(self, products: List[Product], normalized_data: Dict[str, np.ndarray]) -> List[RankedProduct]:
        ranked = []
        for i, p in enumerate(products):
            score = (
                normalized_data["price"][i] * self.weights.price +
                normalized_data["feature_match"][i] * self.weights.feature_match +
                normalized_data["rating"][i] * self.weights.rating +
                normalized_data["delivery"][i] * self.weights.delivery_speed +
                normalized_data["return"][i] * self.weights.return_policy
            )
            
            # Score is 0-1, let's scale to 0-100 for better display
            final_score = round(score * 100, 2)
            
            ranked_p = RankedProduct(
                **p.dict(),
                score=final_score
            )
            ranked.append(ranked_p)
            
        return ranked

    async def _generate_justifications(self, products: List[RankedProduct], user_intent: Dict[str, Any]) -> List[RankedProduct]:
        """Uses LLM to explain why each product is ranked the way it is."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a comparison expert for a commerce agent. 
Given a set of products that have been scored based on:
1. Price (normalized, lower is better)
2. Feature Match (against user must-haves: {must_haves})
3. Rating
4. Delivery Speed
5. Return Policy Quality

Your job is to provide a concise, persuasive, and transparent justification for the ranking of EACH product.
Explain WHY it got its score. Be specific about strengths and trade-offs.
Keep each justification to 2 sentences max."""),
            ("human", "Products and their scores: {product_data}")
        ])
        
        # Prepare data for LLM
        llm_input_data = []
        for p in products:
            llm_input_data.append({
                "name": p.name,
                "price": f"{p.normalized_price} {p.normalized_currency}",
                "score": p.score,
                "merchant": p.merchant,
                "features": p.specifications,
                "delivery": p.delivery_estimate
            })
            
        chain = prompt | self.llm
        
        response = await chain.ainvoke({
            "must_haves": user_intent.get("must_have_features", []),
            "product_data": json.dumps(llm_input_data, indent=2)
        })
        
        # Parse justifications from response
        # Since it's a list, we'll ask for a specific format or just split if simple.
        # Let's use structured output for reliability.
        
        class Justifications(BaseModel):
            justifications: Dict[str, str] # Name to justification mapping

        structured_llm = self.llm.with_structured_output(Justifications)
        justification_chain = prompt | structured_llm
        
        results = await justification_chain.ainvoke({
            "must_haves": user_intent.get("must_have_features", []),
            "product_data": json.dumps(llm_input_data, indent=2)
        })
        
        for p in products:
            p.justification = results.justifications.get(p.name, "Recommended based on overall score and criteria match.")
            
        return products
