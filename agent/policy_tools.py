"""Grounded policy summaries with optional web evidence (unverified search excerpts)."""
from dataclasses import asdict
from datetime import datetime, timezone
from smartdeal.policies import get_policy, category_for, AS_OF


def research_policies(query, offers, web_research=False):
    category=category_for(query + ' ' + (offers[0].title if offers else ''))
    result=[]
    for store in sorted({o.merchant for o in offers}):
        p=get_policy(store,category)
        if p:
            result.append({'store':p.store,'category':category,'reviewed_at':AS_OF+'T00:00:00+00:00',
                           'payload':asdict(p),'source_urls':list(p.urls),'status':'category-level; listing unverified'})
    web_evidence=[]
    if web_research:
        try:
            from langchain_keenable import KeenableSearch
            tool=KeenableSearch()
            # Query only official-looking policy pages; raw web results remain UNVERIFIED.
            for p in result[:3]:
                q=f"{p['store']} official return warranty policy {category} site:{p['source_urls'][0].split('/')[2]}"
                response=tool.invoke({"query": q, "site": p["source_urls"][0].split("/")[2]})
                web_evidence.append({'store':p['store'],'query':q,'search_excerpt':str(response)[:1200],
                                     'status':'Search evidence only, not verified product coverage'})
        except Exception as exc:
            web_evidence.append({'error':f'Optional web policy research unavailable: {type(exc).__name__}'})
    return result,web_evidence
