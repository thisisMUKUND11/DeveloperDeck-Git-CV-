# Deploying DevReel

Two apps ship separately:

- **`apps/web`** (Next.js) → **Vercel** (auto-detected, zero config beyond env vars)
- **`apps/api`** (FastAPI) → any Docker host. Steps below use **Render** (free tier), but the `Dockerfile` is portable to Railway / Fly.io / a VPS.

The browser only ever talks to the Vercel app. Vercel proxies `/api/*` to the
backend server-side (see [apps/web/next.config.mjs](apps/web/next.config.mjs)),
so there's one public URL for visitors and no CORS to worry about in the common
path.

> **Storage:** the store ([apps/api/app/store.py](apps/api/app/store.py)) picks
> its backend from `DATABASE_URL` — SQLite for local dev, **Postgres in
> production**. Point `DATABASE_URL` at a free Neon/Supabase Postgres (Step 0)
> so generated profiles and shared résumé links persist across restarts and
> redeploys. Without it, SQLite on the container's ephemeral disk is wiped on
> every restart and share links break.

---

## 0. Create the free Postgres (Neon or Supabase)

1. Sign up at [neon.tech](https://neon.tech) (or [supabase.com](https://supabase.com)) — free tier, no card.
2. Create a project/database and copy the **connection string**. It looks like:
   `postgresql://user:pass@host/dbname?sslmode=require`
3. Keep it handy — it becomes `DATABASE_URL` on the API in Step 1. The app
   creates its own tables on first boot; no manual SQL needed.

---

## 1. Deploy the API (Render)

1. Push this repo to GitHub (if not already).
2. Render → **New → Web Service** → connect the repo.
3. Settings:
   - **Root Directory:** `proof-xyz/apps/api`
   - **Runtime:** `Docker` (Render auto-detects the `Dockerfile`)
   - **Instance type:** Free is fine to start.
4. **Environment variables** (Render dashboard → Environment):

   | Key | Value | Notes |
   |-----|-------|-------|
   | `LLM_PROVIDER` | `gemini` | or `claude` / `rules` |
   | `GEMINI_API_KEY` | *your key* | free at https://aistudio.google.com/apikey |
   | `WEB_BASE_URL` | `https://<your-vercel-domain>` | your Vercel URL; comma-separate extras |
   | `API_BASE_URL` | `https://<your-render-service>.onrender.com` | this service's own URL |
   | `DATABASE_URL` | *Neon/Supabase connection string* | from Step 0 — makes share links durable |

   OAuth is optional — skip `GITHUB_CLIENT_ID/SECRET` unless you want one-click
   GitHub login. A `GITHUB_TOKEN` is recommended to raise GitHub's 60/hr limit.
5. Deploy. Verify: open `https://<your-render-service>.onrender.com/api/health`
   — it should report the active `generative_layer`.

> **Tip:** you can skip the manual setup above and deploy via the included
> [apps/api/render.yaml](apps/api/render.yaml) Blueprint (Render → New →
> Blueprint). It declares the free web service and the env vars; you just paste
> the secret values (including `DATABASE_URL`) in the dashboard.

---

## 2. Deploy the web app (Vercel)

1. Vercel → **Add New → Project** → import the repo.
2. Settings:
   - **Root Directory:** `proof-xyz/apps/web`
   - Framework preset: **Next.js** (auto-detected).
3. **Environment variables:**

   | Key | Value | Notes |
   |-----|-------|-------|
   | `BACKEND_INTERNAL_URL` | `https://<your-render-service>.onrender.com` | where Vercel proxies `/api/*` |
   | `NEXT_PUBLIC_PUBLIC_BASE_URL` | `https://<your-vercel-domain>` | used to build shareable links |

   Leave `NEXT_PUBLIC_API_BASE_URL` **empty** so the browser uses same-origin
   `/api/*` (proxied via Vercel).
4. Deploy. Open your Vercel URL, enter a GitHub username, pick a theme.

---

## 3. (Optional) GitHub OAuth for one-click login

1. github.com/settings/developers → **New OAuth App**.
2. **Authorization callback URL:** `https://<your-render-service>.onrender.com/api/auth/github/callback`
3. Add `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` to the **API** env vars and redeploy.

---

## Local production sanity check (Docker)

```bash
cd proof-xyz/apps/api
docker build -t devreel-api .
docker run -p 8000:8000 --env-file .env devreel-api
# → http://localhost:8000/api/health
```
