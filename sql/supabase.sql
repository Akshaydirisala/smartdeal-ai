-- Run once in the Supabase SQL Editor. This app uses server-only secret key.
-- Data provider retention/redistribution permissions are your responsibility.
CREATE TABLE IF NOT EXISTS public.search_cache (
 query text NOT NULL, location text NOT NULL, fetched_at timestamptz NOT NULL,
 payload jsonb NOT NULL, PRIMARY KEY(query,location)
);
CREATE TABLE IF NOT EXISTS public.price_observations (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 checked_at timestamptz NOT NULL, product_id text, title text NOT NULL,
 merchant text NOT NULL, price numeric(12,2) NOT NULL, url text NOT NULL
);
CREATE INDEX IF NOT EXISTS price_lookup_idx ON public.price_observations(product_id,merchant,checked_at DESC);
CREATE TABLE IF NOT EXISTS public.policy_snapshots (
 store text NOT NULL, category text NOT NULL, reviewed_at timestamptz NOT NULL,
 payload jsonb NOT NULL, source_urls text[] NOT NULL DEFAULT '{}', status text NOT NULL,
 PRIMARY KEY(store,category)
);
ALTER TABLE public.search_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.policy_snapshots ENABLE ROW LEVEL SECURITY;
-- No browser-facing policies: only backend using server secret/service-role can read/write.
REVOKE ALL ON public.search_cache,public.price_observations,public.policy_snapshots FROM anon,authenticated;
REVOKE ALL ON SEQUENCE public.price_observations_id_seq FROM anon,authenticated;
