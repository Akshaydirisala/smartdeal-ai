"""Simple interchangeable local SQLite / Supabase REST storage.

SUPABASE_SECRET_KEY is server-only. Never expose it in a client or Git.
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from smartdeal.engine import Offer

UTC = lambda: datetime.now(timezone.utc)

class StoreError(RuntimeError):
    pass

class SQLiteStore:
    def __init__(self, path=None):
        self.path = path or os.getenv('SQLITE_PATH','smartdeal.db')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS search_cache (query TEXT, location TEXT, fetched_at TEXT, payload TEXT, PRIMARY KEY(query,location))')
            c.execute('CREATE TABLE IF NOT EXISTS price_observations (id INTEGER PRIMARY KEY, checked_at TEXT, product_id TEXT, title TEXT, merchant TEXT, price REAL, url TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS policy_snapshots (store TEXT, category TEXT, reviewed_at TEXT, payload TEXT, PRIMARY KEY(store,category))')
    def connect(self):
        return sqlite3.connect(self.path, timeout=20)
    def cached(self, query, location, hours):
        with self.connect() as c:
            row=c.execute('SELECT fetched_at,payload FROM search_cache WHERE query=? AND location=?',(query,location)).fetchone()
        if not row or UTC()-datetime.fromisoformat(row[0])>timedelta(hours=hours): return None
        return [Offer(**x) for x in json.loads(row[1])]
    def save(self, query, location, offers, policies):
        now=UTC().isoformat()
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO search_cache VALUES (?,?,?,?)',(query,location,now,json.dumps([o.serialize() for o in offers])))
            c.executemany('INSERT INTO price_observations(checked_at,product_id,title,merchant,price,url) VALUES (?,?,?,?,?,?)',[(o.checked_at or now,o.product_id,o.title,o.merchant,o.price,o.url) for o in offers])
            for p in policies:
                c.execute('INSERT OR REPLACE INTO policy_snapshots VALUES (?,?,?,?)',(p['store'],p['category'],p['reviewed_at'],json.dumps(p)))
    def history(self, product_id, merchant):
        if not product_id: return []
        with self.connect() as c:
            return c.execute('SELECT checked_at,price FROM price_observations WHERE product_id=? AND merchant=? ORDER BY checked_at DESC LIMIT 100',(product_id,merchant)).fetchall()[::-1]

class SupabaseStore:
    """Server-to-server PostgREST; restricted private tables in SQL setup."""
    def __init__(self):
        self.url=os.environ['SUPABASE_URL'].rstrip('/')+'/rest/v1'
        self.key=os.environ['SUPABASE_SECRET_KEY']
        self.session=requests.Session()
        self.session.headers.update({'apikey':self.key,'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
    def _request(self, method, table, **kwargs):
        try:
            response=self.session.request(method,self.url+'/'+table,timeout=15,**kwargs)
            response.raise_for_status()
            return response.json() if response.content else []
        except (requests.RequestException,ValueError) as exc:
            raise StoreError(f'Database request failed: {exc}') from exc
    def cached(self, query, location, hours):
        rows=self._request('GET','search_cache',params={'select':'fetched_at,payload','query':'eq.'+query,'location':'eq.'+location,'limit':1})
        if not rows or UTC()-datetime.fromisoformat(rows[0]['fetched_at'].replace('Z','+00:00'))>timedelta(hours=hours):return None
        return [Offer(**o) for o in rows[0]['payload']]
    def save(self, query, location, offers, policies):
        now=UTC().isoformat()
        self._request('POST','search_cache',params={'on_conflict':'query,location'},headers={'Prefer':'resolution=merge-duplicates,return=minimal'},json=[{'query':query,'location':location,'fetched_at':now,'payload':[o.serialize() for o in offers]}])
        if offers:
            self._request('POST','price_observations',headers={'Prefer':'return=minimal'},json=[{'checked_at':o.checked_at or now,'product_id':o.product_id,'title':o.title,'merchant':o.merchant,'price':o.price,'url':o.url} for o in offers])
        if policies:
            self._request('POST','policy_snapshots',params={'on_conflict':'store,category'},headers={'Prefer':'resolution=merge-duplicates,return=minimal'},json=policies)
    def history(self,product_id,merchant):
        if not product_id:return []
        rows=self._request('GET','price_observations',params={'select':'checked_at,price','product_id':'eq.'+product_id,'merchant':'eq.'+merchant,'order':'checked_at.desc','limit':100})
        return [(r['checked_at'],r['price']) for r in reversed(rows)]

def get_store():
    if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SECRET_KEY'):
        return SupabaseStore()
    return SQLiteStore()
