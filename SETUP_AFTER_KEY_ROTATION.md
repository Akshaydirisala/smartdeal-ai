# SmartDeal AI: safe configuration after credential exposure

## 1. Rotate exposed credentials first

- SerpApi dashboard: revoke/generate a new private API key.
- Supabase dashboard: revoke/rotate the exposed `sb_secret_...` server secret and create a new one. Check logs for unexpected requests; review other privileged keys if applicable.
- `SUPABASE_PUBLISHABLE_KEY` is intended for browser/public use, but this app does not require it. The `SUPABASE_JWKS_URL` is a public verification endpoint and is not a password.
- Never paste new credentials into a chat, GitHub issue, screenshot, README, or public code repository.

## 2. Set up database

Open Supabase Dashboard > SQL Editor, paste `sql/supabase.sql`, and run it once.
This is a manual step: the schema has not been deployed to your Supabase project.

## 3. Run locally

```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` on your own computer to set the newly rotated `SERPAPI_KEY`, `SUPABASE_URL`, and `SUPABASE_SECRET_KEY`.
Set `SUPABASE_URL` to your project's URL displayed in the Supabase dashboard.
Then run `streamlit run app.py`.

## 4. Deploy to Streamlit Community Cloud

Upload the repository to GitHub WITHOUT `.env` or `.streamlit/secrets.toml`.
On Streamlit Community Cloud, use App Settings > Secrets to provide the keys.
The current app loads named Streamlit secrets into its backend environment.
Keep the secret key server-side only. Never expose the API secret through browser Javascript or frontend source.

## 5. Deployment precautions

- Google Shopping results, store return policies and manufacturer warranties must be verified for the specific listing.
- Use API rate limits and ensure data-provider caching rights before public launch.
- Do not rely on free-host local SQLite for durable multi-user storage.
- Test the application and Supabase SQL schema before public sharing.
- This project has not been deployed or connected to your live Supabase project.
