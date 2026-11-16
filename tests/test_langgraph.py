import os
import tempfile
import unittest
from agent.graph import graph
from agent.repository import SQLiteStore
from smartdeal.engine import Offer, normalize_item, thanksgiving_deals

class AgentTests(unittest.TestCase):
    def test_demo_graph(self):
        state=graph.invoke({'query':'65 inch smart TV','mode':'demo','location':'United States','priority':'balanced'})
        self.assertTrue(state['offers']);self.assertIn('explanation',state)
        self.assertTrue(state['policy_records'])
        self.assertFalse(state['cached_hit'])
    def test_empty_query(self):
        state=graph.invoke({'query':'','mode':'demo'})
        self.assertIn('error',state)
    def test_live_requires_key(self):
        if not os.environ.get('SERPAPI_KEY'):
            state=graph.invoke({'query':'trash can','mode':'live'})
            self.assertIn('error',state)
    def test_sqlite_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            db=SQLiteStore(d+'/test.db')
            o=Offer(title='Test TV',merchant='Costco',price=99,url='https://example.com/test',product_id='abc',checked_at='2026-11-15T00:00:00+00:00')
            db.save('test','US',[o],[])
            self.assertEqual(len(db.history('abc','Costco')),1)
            self.assertIsNotNone(db.cached('test','US',2))
    def test_result_without_link_and_extracted_price(self):
        offer=normalize_item({'title':'Coffee','price':'$12.99','source':'Store'})
        self.assertEqual(offer.price,12.99)
        self.assertEqual(offer.url,'')
    def test_merchant_link_preferred_and_unsafe_link_ignored(self):
        offer=normalize_item({'extracted_price':10,'link':'https://store.example/item','product_link':'https://google.com/shopping/item'})
        self.assertEqual(offer.url,'https://store.example/item')
        offer=normalize_item({'extracted_price':10,'link':'javascript:alert(1)'})
        self.assertEqual(offer.url,'')
    def test_empty_live_results_not_saved(self):
        from unittest.mock import patch
        from agent.graph import persistence
        with patch('agent.graph.get_store') as store:
            persistence({'mode':'live','offers':[]})
            store.assert_not_called()
    def test_thanksgiving_deals_require_reported_reduction(self):
        raw={'title':'TV','extracted_price':50,'old_price':'$100.00'}
        discounted=normalize_item(raw)
        self.assertEqual(discounted.discount_pct,50)
        other=Offer(title='Other',merchant='Store',price=10,url='')
        self.assertEqual(thanksgiving_deals([other,discounted]),[discounted])
        self.assertEqual(thanksgiving_deals([other]),[])

if __name__=='__main__':unittest.main()
