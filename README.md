# SmartDeal AI v3 — LangGraph Learning Edition

An educational, runnable **shopping decision agent** that compares **listed prices, category-level returns and warranty coverage**, using live Google Shopping results. The app requires a SerpApi key and does not automatically buy anything.

### Deploy on Streamlit Community Cloud

1. Upload the project to a GitHub repository; never upload `.env` or secrets.
2. Create an app at https://share.streamlit.io/, select the repository and branch, and set the main file to `app.py`.
3. In the app's settings, add the following under **Secrets**, replacing the placeholder with a new private key:
   ```toml
   SERPAPI_KEY = "your-new-serpapi-key"
   ```
4. Deploy or restart the app, then search for a product. Live searches use SerpApi credits.

SQLite on hosted platforms may be reset; configure Supabase as described below if persistent shared storage is needed. This is a beta, not a payment or checkout application.

## 1. API keys and databases

| Service | Needed? | Configuration | Get it |
|---|---|---|---|
| SerpApi Google Shopping | **Yes for live prices**; demo needs none | `SERPAPI_KEY` | https://serpapi.com/ |
| Supabase PostgreSQL | **Recommended for a shared hosted app**, optional for local runs | `SUPABASE_URL` and **server-only** `SUPABASE_SECRET_KEY` | https://supabase.com/dashboard/projects |
| Keenable AI | **Optional** for exploratory policy-page search | `KEENABLE_API_KEY` (integration also offers keyless access) | https://keenable.ai/ |
| Ollama / Qwen3 | **Optional** local LLM explanation; no API key | `OLLAMA_URL`, `OLLAMA_MODEL` | https://ollama.com/ |

**Not needed:** OpenAI API key, Pinecone, a vector database, paid LangSmith, Stripe, or separate retailer accounts for the MVP. Real per-product warranty checks, taxes, live local stock, affiliate payouts and coupon eligibility are *not* yet supported.

### Database choice

- **SQLite** for learning and local testing: automatically created; no account needed.
- **Supabase** for an externally hosted shared app: create a project and run `sql/supabase.sql` in SQL Editor. Put `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in **server secrets only**, never JavaScript/browser code or Git. SQL enables RLS and revokes client roles; backend uses privileged secret key. Use a dedicated server-side data access layer before adding users.
- Note: host platform local disks may reset. Use Supabase for production-like deployments. Query history is *observed from now forward*, not a purchased historical dataset.

### Where to obtain keys

1. **SerpApi**: sign up, open dashboard, copy your private API key. Set `SERPAPI_KEY`.
2. **Supabase**: create project, copy Project URL and project secret/service-role key from dashboard API settings. Put them in backend environment only. Run SQL script to create tables before search.
3. **Keenable**: sign up or use official keyless integration; API key is optional but recommended for predictable usage. Set `KEENABLE_API_KEY` and `pip install langchain-keenable` if using policy web research.
4. **Ollama**: install locally, run `ollama pull qwen3:4b`. No API key required.

## 2. Run on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env; demo works with all keys empty
streamlit run app.py
```

Open http://localhost:8501. For optional Keenable: `pip install langchain-keenable`. For tests: `python -m unittest discover -s tests -v`.

## 3. Learning LangGraph, node by node

```
START
  |
validate -> if error END
  |
cache ---------------------> if cache hit use_cache
  |                                      |
search <--- if no cache                  |
  |                                      |
  +---------------- policies <-----------+
                       |
                   matching
                       |
                    ranking
                       |
                  persistence
                       |
                    explain
                       |
                      END
```

Read `agent/graph.py` in this order:

1. **State**: `ShoppingState` is the shared TypedDict for all agents/tools.
2. **Nodes**: Each function reads `state`, returns partial updates (`dict`).
3. **Conditional edges**: `after_validate` and `cache_route` implement decision paths.
4. **Search**: `shopping_search` uses SerpApi only if live mode is selected; demo avoids network.
5. **Matching**: `exact_product_groups()` requires shared product IDs to make exact-product retailer comparisons. *Titles alone are not proof of identical products.*
6. **Policies**: predefined references plus optional Keenable search excerpts. Search excerpts **are not verified facts** and are displayed separately. Avoid dynamically trusting search-page instructions.
7. **Ranking**: deterministic Python calculations from source offers; the LLM cannot invent prices or manipulate ranking.
8. **Persistence**: SQLite locally or Supabase via server-to-server PostgREST (same interface).
9. **Explanation**: grounded deterministic decision, plus optional Ollama narrative (must be verified independently).

## 4. Stored tables

The actual v3 schema has **three tables** to keep the MVP small:

- `search_cache`: the latest permitted offers for a query/location, with expiry governed by `CACHE_HOURS`.
- `price_observations`: timestamped historical observations, one row per observed offer.
- `policy_snapshots`: category-level retailer policy references, **not verified product-specific promises**.

You can add `products`, `users`, `user_watchlists`, or `alerts` after validating usage. Do not store personal shopper histories before implementing appropriate user authentication, access controls and privacy policies.

## 5. Deploy and operational limits

For early testers, use Streamlit Community Cloud with a GitHub repository and application entrypoint `app.py`. Add env keys as server secrets (do **not** commit `.env`). The `app.py` entrypoint reads known keys from `st.secrets` into the server environment, so you can configure them in the Streamlit deployment Secrets editor. A separate service is needed for Ollama when hosting publicly. Free hosting may sleep; SQLite there is not durable.

For public traffic, add request quotas and per-user limits, log search expenses, verify API licensing/retention policies, and test against real products. **Never automatically treat prices, return windows, or warranty claims as confirmed at checkout.** This app is a beta, not ready to collect payment details.

## 6. Limitations to address next

- Google Shopping search results can list unlike products; automatic comparisons abstain if exact shared product IDs cannot be found.
- Merchant field does not guarantee who fulfills an order or whether policies apply.
- Shipping fees often missing and never silently assumed $0. Membership fees, tax, installation, coupons and promotional terms are not included in scores.
- Store policies are category-level references and should be manually revisited. Keenable adds *research excerpts*, not final verification.
- Provider caching and long-term storage are permitted only where your API agreements allow it.
- Price history captures only observations collected through searches, not historical deals before deployment.
- A custom production frontend, user accounts and email alerts require additional work.

## 7. Testing status

- Source compiled with `python -m compileall`.
- Local SQLite store and sample decision logic passed direct smoke tests.
- **End-to-end LangGraph test has not run in this build environment** because the LangGraph package could not be installed due to package-index network restrictions. Install `requirements.txt` on your machine, then run `python -m unittest discover -s tests -v` and the app before sharing with real users.
- No live SerpApi, Supabase, Keenable or Ollama credentials were used in this build.
