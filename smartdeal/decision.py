"""Evidence-first decision engine; no dollar valuation assigned to warranties."""
from __future__ import annotations
from dataclasses import dataclass
from .engine import Offer
from .policies import StorePolicy, get_policy, category_for

@dataclass
class Decision:
    offer: Offer
    policy: StorePolicy | None
    score: float
    explanation: str


def compare_stores(offers: list[Offer], query: str, priority: str='balanced', bestbuy_member: bool=False,
                   exact_only: bool=True, selected_product_id: str | None=None) -> dict:
    """Never identify a cheapest *store* unless comparing the same product ID.

    Demo uses a declared synthetic product ID. Real results with missing IDs
    produce an abstention rather than pretending unrelated models are equal.
    """
    if not offers:
        return {'rows':[], 'cheapest':None, 'overall':None, 'protection':None, 'warning':'No offers to compare.'}
    if exact_only:
        pid = selected_product_id
        if not pid:
            # Only automatically pick a cross-store group if unambiguous.
            ids = {x.product_id for x in offers if x.product_id}
            if len(ids)==1 and len({x.merchant.lower() for x in offers if x.product_id in ids})>1:
                pid=next(iter(ids))
        eligible=[x for x in offers if pid and x.product_id==pid]
        if len({o.merchant.lower() for o in eligible})<2:
            return {'rows':[], 'cheapest':None, 'overall':None, 'protection':None,
                    'warning':'No verified same-product cross-store group. Choose a product ID group or search an exact model. Retailer rankings are intentionally withheld.'}
    else:
        eligible=list(offers)
    category=category_for(query+' '+eligible[0].title)
    cheapest_item=min(eligible,key=lambda o: o.known_total if o.shipping is not None else o.price)
    lowest=min(o.price for o in eligible)
    rows=[]
    for o in eligible:
        p=get_policy(o.merchant,category,member=bestbuy_member)
        price_score=100*lowest/o.price
        # Never assume unknown warranty equals zero or a retailer's generic warranty is certain.
        return_component=(min(p.return_days,90)/90*100) if p and p.return_days is not None else 35
        warranty_component=100 if p and p.warranty_months is not None else 35
        if priority=='price':
            score=price_score
        elif priority=='protection':
            score=.15*price_score+.35*return_component+.50*warranty_component
        elif priority=='returns':
            score=.3*price_score+.7*return_component
        else:
            score=.55*price_score+.25*return_component+.20*warranty_component
        explanation=(p.returns_description+'; '+p.warranty_description) if p else 'Store-specific return/warranty policy not available; inspect seller terms.'
        rows.append(Decision(o,p,round(score,1),explanation))
    rows.sort(key=lambda x:(-x.score,x.offer.price))
    # Return cheapest is explicitly listed price only, unless ALL shipping amounts are known.
    cheapest=min(rows,key=lambda x: x.offer.price)
    overall=max(rows,key=lambda x:x.score)
    # Protection only among policies with evidence; unknown warranties not treated as positive facts.
    documented=[x for x in rows if x.policy and (x.policy.return_days is not None or x.policy.warranty_months is not None)]
    protection=max(documented,key=lambda x:((x.policy.warranty_months or 0), (x.policy.return_days or 0))) if documented else None
    return {'rows':rows,'cheapest':cheapest,'overall':overall,'protection':protection,'warning':None,
            'category':category,'full_shipping_known':all(x.offer.shipping is not None for x in rows),
            'synthetic':all('SYNTHETIC' in x.offer.source for x in rows)}


def incremental_cost(comparison:dict) -> dict | None:
    cheap=comparison.get('cheapest'); overall=comparison.get('overall')
    if not cheap or not overall or cheap.offer is overall.offer:
        return None
    delta=round(overall.offer.price-cheap.offer.price,2)
    if delta <= 0:
        return None
    return {'amount':delta,'store':overall.offer.merchant,'compared_to':cheap.offer.merchant,
            'note':f'{overall.offer.merchant} is ${delta:.2f} more in listed item price. '+
                   'Compare actual checkout totals and product-specific protection before deciding.'}
