"""Live shopping lookup and optional local open-weight model explanation."""
import os
import requests
from datetime import datetime, timezone
from .engine import normalize_item
from .policies import get_policy, category_for

class ShoppingAPIError(Exception):
    pass


def shopping_search(query: str, location: str = "United States") -> list:
    key = os.getenv("SERPAPI_KEY", "").strip()
    if not key:
        raise ShoppingAPIError("Add SERPAPI_KEY to .env to enable live offers.")
    try:
        response = requests.get("https://serpapi.com/search.json", params={
            "engine": "google_shopping", "q": query, "api_key": key,
            "gl": "us", "hl": "en", "location": location or "United States"
        }, timeout=25)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        # Requests exceptions can include the full URL, including the API key.
        raise ShoppingAPIError("Shopping lookup failed. Check your SerpApi key, account and network connection.") from exc
    if payload.get("error"):
        raise ShoppingAPIError(str(payload["error"]))
    checked_at = datetime.now(timezone.utc).isoformat()
    offers = [normalize_item(item, checked_at) for item in payload.get("shopping_results", [])]
    return [item for item in offers if item is not None]


def ollama_explain(query: str, offers: list, timeout: int = 20) -> str | None:
    """Local inference is OPTIONAL. Model can only explain existing evidence.
    To avoid invoking it on remote deployment, leave it off in UI.
    """
    if not offers:
        return None
    model = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    endpoint = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    evidence = [dict(title=o.title, merchant=o.merchant, price=o.price,
                     rating=o.rating, reviews=o.reviews, shipping=o.shipping,
                     score=o.value_score) for o in offers[:5]]
    category = category_for(query)
    policy_evidence = []
    for o in offers[:5]:
        p = get_policy(o.merchant, category)
        if p:
            policy_evidence.append(dict(store=p.store, returns=p.returns_description,
                                        warranty=p.warranty_description, exceptions=p.exclusions,
                                        sources=list(p.urls)))
    prompt = ("You are a careful, independent shopping analyst. Use ONLY the product and policy facts provided. "
              "No invented prices, reviews, discounts, availability or warranties. "
              "Store policies are only category-level clues, NOT proof of eligibility for a specific listing. "
              "Mention shipping and tax are unverified when applicable. "
              "The items may be different products and must not be called identical without proof. "
              "Give both cheapest listed offer and potential benefits with caveats in at most 140 words. User request: " + query + "\nOffers: " + repr(evidence) + "\nGeneral retailer policy evidence: " + repr(policy_evidence))
    try:
        resp = requests.post(f"{endpoint}/api/chat", json={"model": model, "stream": False,
            "messages": [{"role":"user", "content":prompt}], "options":{"temperature": 0.2, "num_predict": 180}}, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content") or None
    except (requests.RequestException, ValueError):
        return None
