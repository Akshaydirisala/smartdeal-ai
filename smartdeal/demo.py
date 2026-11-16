"""Entirely SYNTHETIC offers; real store names are illustrative only."""
from datetime import datetime, timezone
from .engine import Offer

def sample_offers(query='65 inch smart TV'):
    now=datetime.now(timezone.utc).isoformat()
    q=query.lower()
    if any(x in q for x in ('trash','garbage','bin')):
        product='DEMO-EXACT-13G-TRASHCAN'; title='DEMO 13-gallon stainless steel step trash can'
        items=[('Walmart',49.99,4.5,1400),('Costco',54.99,4.6,1200),('Target',59.99,4.4,1000),('Amazon',52.99,4.6,1500),('Best Buy',64.99,4.5,700)]
    else:
        product='DEMO-EXACT-65TV'; title='DEMO 65-inch 4K smart television (identical model)'
        items=[('Walmart',449,4.5,1400),('Costco',479,4.6,1200),('Best Buy',469,4.7,800),('Target',489,4.5,900),('Amazon',459,4.6,2300)]
    return [Offer(title=title,merchant=merchant,price=price,rating=rating,reviews=reviews,
                   shipping=None,shipping_note='Unknown even in demo',product_id=product,
                   url='https://example.com/',checked_at=now,source='SYNTHETIC DEMO — NOT REAL OFFERS')
            for merchant,price,rating,reviews in items]
