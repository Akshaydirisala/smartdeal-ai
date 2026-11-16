"""Learn LangGraph: each node consumes shared state and returns a partial update.

Graph structure:
START -> validate -> cache -> [search OR use_cache] -> policies -> matching ->
ranking -> persistence -> explanation -> END
"""
from __future__ import annotations
import os
import re
from typing import TypedDict, NotRequired
from langgraph.graph import StateGraph, START, END
from smartdeal.engine import Offer, score_offers, exact_product_groups
from smartdeal.decision import compare_stores, incremental_cost
from smartdeal.services import shopping_search, ollama_explain
from smartdeal.demo import sample_offers
from agent.repository import get_store
from agent.policy_tools import research_policies

class ShoppingState(TypedDict, total=False):
    query: str
    location: str
    mode: str
    priority: str
    budget: float | None
    min_rating: float
    use_ollama: bool
    use_keenable: bool
    refresh: bool
    offers: list[Offer]
    ranked: list[Offer]
    policy_records: list[dict]
    web_policy_evidence: list[dict]
    comparison: dict
    product_groups: dict
    selected_id: str | None
    explanation: str
    notes: list[str]
    cached_hit: bool
    error: str

def validate(state:ShoppingState)->dict:
    q=state.get('query','').strip()
    if not q or len(q)>160:return {'error':'Enter a product query of 1–160 characters.'}
    if state.get('mode','demo')=='live' and not os.getenv('SERPAPI_KEY'):
        return {'error':'SERPAPI_KEY is required for live offers.'}
    return {'query':q,'location':state.get('location','United States').strip()[:100] or 'United States', 'notes':[]}

def after_validate(state):return 'finish' if state.get('error') else 'cache'

def cache(state):
    if state.get('mode','demo')=='demo' or state.get('refresh'):return {'cached_hit':False}
    try:
        got=get_store().cached(state['query'].lower(),state['location'],float(os.getenv('CACHE_HOURS','3')))
        if got:return {'offers':got,'cached_hit':True}
    except Exception as exc:
        return {'cached_hit':False,'notes':[f'Cache unavailable ({type(exc).__name__}); attempting live search.']}
    return {'cached_hit':False}

def cache_route(state):return 'use_cache' if state.get('cached_hit') else 'search'

def use_cache(state):return {'notes':state.get('notes',[])+['Reused cached price results (check last-checked timestamps).']}

def search(state):
    try:
        if state.get('mode','demo')=='demo':
            offers=sample_offers(state['query'])
            return {'offers':offers,'notes':state.get('notes',[])+['SYNTHETIC DEMO: all prices and listings are fictional.']}
        offers=shopping_search(state['query'],state['location'])
        return {'offers':offers}
    except Exception as exc:
        return {'offers':[],'error':f'Product search failed: {exc}'}

def policies(state):
    records,web=research_policies(state['query'],state.get('offers',[]),bool(state.get('use_keenable')))
    return {'policy_records':records,'web_policy_evidence':web}

def matching(state):
    ranked=score_offers(state.get('offers',[]),state['query'],state.get('budget'),state.get('min_rating',0),False)
    groups=exact_product_groups(ranked)
    selected=state.get('selected_id')
    if selected not in groups:
        selected=next(iter(groups)) if len(groups)==1 else None
    return {'ranked':ranked,'product_groups':groups,'selected_id':selected}

def ranking(state):
    result=compare_stores(state.get('ranked',[]),state['query'],priority=state.get('priority','balanced'),selected_product_id=state.get('selected_id'))
    return {'comparison':result}

def persistence(state):
    if state.get('cached_hit') or state.get('mode')=='demo' or not state.get('offers'):return {}
    try:
        get_store().save(state['query'].lower(),state['location'],state.get('offers',[]),state.get('policy_records',[]))
    except Exception as exc:
        return {'notes':state.get('notes',[])+[f'Unable to save results ({type(exc).__name__}); current comparison is still available.']}
    return {}

def explain(state):
    c=state.get('comparison',{})
    if c.get('warning'):
        explanation='Cannot recommend a cheapest store for the exact same product: '+c['warning']
    else:
        cheap=c['cheapest'];overall=c['overall'];protect=c.get('protection')
        explanation=(f"Cheapest listed price: {cheap.offer.merchant} ${cheap.offer.price:.2f}. "
                     f"Best for '{state.get('priority','balanced')}': {overall.offer.merchant} at ${overall.offer.price:.2f}. "
                     + (f"Most documented category-level protection: {protect.offer.merchant}. " if protect else '')
                     + 'Shipping, taxes, memberships and listing-specific warranty coverage may change the decision.')
        delta=incremental_cost(c)
        if delta:explanation+=' '+delta['note']
    if state.get('use_ollama') and state.get('ranked'):
        llm=ollama_explain(state['query'],state['ranked'][:6])
        if llm: explanation+='\n\nOptional local AI explanation (verify independently): '+llm
    return {'explanation':explanation}

def build_graph():
    b=StateGraph(ShoppingState)
    for name,func in [('validate',validate),('cache',cache),('search',search),('use_cache',use_cache),('policies',policies),('matching',matching),('ranking',ranking),('persistence',persistence),('explain',explain)]:b.add_node(name,func)
    b.add_edge(START,'validate')
    b.add_conditional_edges('validate',after_validate,{'finish':END,'cache':'cache'})
    b.add_conditional_edges('cache',cache_route,{'search':'search','use_cache':'use_cache'})
    b.add_edge('search','policies');b.add_edge('use_cache','policies')
    b.add_edge('policies','matching');b.add_edge('matching','ranking');b.add_edge('ranking','persistence');b.add_edge('persistence','explain');b.add_edge('explain',END)
    return b.compile()

graph=build_graph()
