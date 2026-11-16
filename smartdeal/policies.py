"""Conservative US retailer policy reference, checked 2026-11-15.

These are category-level reference facts, NOT verification for individual product
listings or marketplace sellers. Unknowns stay unknown. Policy citations are
stored with each rule and exposed in the UI.
"""
from __future__ import annotations
from dataclasses import dataclass

AS_OF = '2026-11-15'

@dataclass(frozen=True)
class StorePolicy:
    store: str
    category: str
    return_days: int | None
    warranty_months: int | None
    returns_description: str
    warranty_description: str
    exclusions: str
    urls: tuple[str, ...]
    confidence: str = 'Category-level policy only — check the listing and seller'

COSTCO_RET = 'https://customerservice.costco.com/app/answers/detail/a_id/1191'
COSTCO_WARR = 'https://customerservice.costco.com/app/answers/detail/a_id/8662/kw/delivery'
BESTBUY = 'https://www.bestbuy.com/site/help-topics/return-exchange-policy/pcmcat260800050014.c'
WALMART = 'https://corporate.walmart.com/policies'
TARGET = 'https://www.target.com/returns'
TARGET_ELEC = 'https://www.target.com/help/articles/returns-exchanges/returns'
AMAZON = 'https://digprjsurvey.amazon.com/csad/help/node/GKM69DUUYKQWKWX7'


def category_for(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ('refrigerator','fridge','washing machine','washer','dryer','dishwasher','oven range','major appliance','freezer')):
        return 'major_appliance'
    if any(k in t for k in ('television','smart tv',' tv ','65-inch tv','55-inch tv','oled tv','qled tv')) or t.endswith(' tv'):
        return 'tv'
    if any(k in t for k in ('laptop','computer','tablet','headphones','camera','monitor','console','smartphone','iphone','electronics','projector')):
        return 'electronics'
    return 'general'


def canonical_store(merchant: str) -> str | None:
    """Avoid treating 'Best Buy Marketplace' as first-party Best Buy."""
    s = merchant.lower().strip()
    if 'marketplace' in s or 'third party' in s or '3rd party' in s:
        return None
    for match, name in [('costco','Costco'),('best buy','Best Buy'),('walmart','Walmart'),('target','Target'),('amazon','Amazon')]:
        if match in s:
            return name
    return None


def get_policy(store_name: str, category: str, member: bool=False) -> StorePolicy | None:
    store = canonical_store(store_name)
    if not store:
        return None
    if store == 'Costco':
        is_covered = category in ('tv','major_appliance')
        is_90 = category in ('tv','major_appliance','electronics')
        return StorePolicy(store,category,90 if is_90 else None,24 if is_covered else None,
            '90-day electronics/major-appliance exception' if is_90 else 'Satisfaction guarantee; category exceptions apply (no fixed duration asserted)',
            'Manufacturer warranty extended up to 2 years total for eligible televisions and major appliances' if is_covered else 'Not verified for this product category',
            'Membership required for most purchases; product exclusions, original manufacturer terms, delivery and seller details apply. Electronics includes other categories with 90-day limits.',
            (COSTCO_RET,COSTCO_WARR))
    if store == 'Best Buy':
        return StorePolicy(store,category,60 if member else 15,None,
            'Most products: 60 days for eligible paid Plus/Total members' if member else 'Most products: standard 15 days',
            'Manufacturer warranty / optional protection plans vary by item; not verified',
            'Activatable devices and Marketplace sales can have different rules. Premium 60-day benefit excludes Marketplace purchases.',(BESTBUY,))
    if store == 'Walmart':
        days = 2 if category=='major_appliance' else 30 if category in ('tv','electronics') else 90
        return StorePolicy(store,category,days,None,
            f'General published window for this category: {days} days',
            'Manufacturer warranty / optional plans vary; not verified',
            'Marketplace sellers, category exceptions and item conditions can change coverage.',(WALMART,))
    if store == 'Target':
        days = 30 if category in ('tv','electronics') else 90
        return StorePolicy(store,category,days,None,
            f'General published window for this category: {days} days',
            'Manufacturer warranty / optional plans vary; not verified',
            'Target Plus, Apple/Beats, holiday promotions and category exceptions can alter the window.',(TARGET,TARGET_ELEC))
    if store == 'Amazon':
        return StorePolicy(store,category,30,None,
            'Most eligible items: 30 days (holiday extensions may apply)',
            'Manufacturer / seller warranty varies and is unverified',
            'Third-party sellers, product exceptions, seasonal windows, and return fees can differ.',(AMAZON,))
    return None
