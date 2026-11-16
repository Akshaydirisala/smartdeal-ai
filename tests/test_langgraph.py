import os
import tempfile
import unittest
from agent.graph import graph
from agent.repository import SQLiteStore
from smartdeal.engine import Offer

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

if __name__=='__main__':unittest.main()
