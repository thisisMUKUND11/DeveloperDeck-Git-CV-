# proof.xyz

Turn a GitHub profile into a **swipeable, recruiter-ready proof-of-work portfolio**
in ~15 seconds. The platform ingests a user's top repos, reads the code's
dependency signatures to infer real skills, and synthesizes a Gen-Z-friendly
deck (hook / proof / stat per repo) rendered as a mobile-first, themed card stack.

This is the **GitHub vertical slice**: OAuth/username connect → ingest → parse →
generate (Gemini) → render at `/<username>`.

```
[ Next.js + Tailwind + Framer Motion ]  apps/web   ── REST/JSON ──┐
                                                                   ▼
[ FastAPI + httpx + Pydantic v2 + Gemini ]  apps/api  ── GitHub API
                                                                   │
[ SQLite (dev) / Postgres (prod) ]  ◄──────────────────────────────┘
```

## Repo layout

| Path | What it is |
|------|-----------|
| [apps/api](apps/api) | FastAPI ingestion + synthesis engine |
| [apps/api/app/github_client.py](apps/api/app/github_client.py) | Parallel GitHub ingestion (repos, languages, READMEs, manifests) |
| [apps/api/app/parser.py](apps/api/app/parser.py) | Dependency/import → skill inference (`spacy` → "NLP", etc.) |
| [apps/api/app/synth.py](apps/api/app/synth.py) | The generative layer — Gemini (`gemini-2.5-flash`), with a rules-based fallback |
| [apps/api/app/limits.py](apps/api/app/limits.py) | Sliding-window rate limiting for the unauthenticated generate endpoint |
| [apps/web](apps/web) | Next.js App Router frontend with the swipeable themed card stack |
| [apps/web/components/CardStack.tsx](apps/web/components/CardStack.tsx) | Framer Motion drag-to-swipe deck |
| [apps/web/lib/themes.ts](apps/web/lib/themes.ts) | Midnight / Paper / Sunset / Terminal theme containers |

## Run it

### 1. Backend (`apps/api`)

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp .env.example .env        # add GEMINI_API_KEY for AI synthesis (free, optional)
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

The API runs at `http://localhost:8000`. Check `GET /api/health` — it reports
whether the **gemini** or **rules** generative layer is active and whether OAuth
is configured.

> **No `GEMINI_API_KEY`?** The synthesizer falls back to a deterministic
> rules-based path so the slice still produces a full deck. Add the key (free,
> no card, at https://aistudio.google.com/apikey) to get AI-written cards.

> **GitHub rate limits:** unauthenticated requests are capped at 60/hr, and one
> profile costs ~9 calls per repo — not enough to finish even one ingest. Add a
> `GITHUB_TOKEN` to `.env` (raises it to 5000/hr and enables private repos).

### 2. Frontend (`apps/web`)

```bash
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev    # → http://localhost:3000
```

Open `http://localhost:3000`, enter a GitHub username (or use one-click OAuth if
configured), pick a theme, and you land on `/<username>` with the swipeable deck.

> On Windows paths containing spaces/`&`, npm's script shim can fail. Run Next
> directly instead: `node ./node_modules/next/dist/bin/next dev`.

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET`    | `/api/health` | Status + active generative layer |
| `POST`   | `/api/generate` | `{username, theme?, token?}` → cached `Profile`, or ingest + synthesize + store |
| `GET`    | `/api/profile/{username}` | Fetch a stored `Profile` |
| `DELETE` | `/api/profile/{username}` | `{token}` → delete the profile and its share links (owner only) |
| `POST`   | `/api/share` | `{username, repos, theme?}` → `{token}` for a read-only snapshot |
| `GET`    | `/api/share/{token}` | Fetch a share snapshot |
| `POST`   | `/api/share/{token}/view` | Count one real browser open |
| `GET`    | `/api/share/{token}/stats` | `{views}` for a share link |
| `GET`    | `/api/auth/github/login` | 302 → GitHub OAuth (if configured) |
| `GET`    | `/api/auth/github/callback` | State check → token exchange → ingest → 302 to web app |

## Generative layer

Selected via `LLM_PROVIDER` (`auto` | `gemini` | `rules`) in
[apps/api/app/synth.py](apps/api/app/synth.py). `auto` uses Gemini when its key
is configured, else the rules-based synthesizer.

- **Gemini (default, free):** `gemini-2.5-flash` via the `google-genai` SDK with
  native JSON-schema structured output bound to the Pydantic `GeneratedDeck`.
  Get a free key (no credit card) at https://aistudio.google.com/apikey and set
  `GEMINI_API_KEY` in `.env`. Calls are bounded by `GEMINI_TIMEOUT_SECONDS`.
- **Rules (fallback):** deterministic, offline — first README sentence +
  dependency-derived stats. Always available, no key. Also used automatically
  whenever the Gemini call fails or times out, so a provider outage degrades the
  copy rather than breaking the page.

The system prompt enforces grounded claims (no invented metrics) and a concrete,
builder-focused voice.

## Cost and abuse controls

`/api/generate` is unauthenticated and a cache miss is expensive — roughly 9
GitHub calls per repo plus one LLM call — so three bounds apply, all tunable via
env (see [.env.example](apps/api/.env.example)):

| Control | Default | Effect |
|---------|---------|--------|
| `PROFILE_CACHE_HOURS` | 24 | Repeat traffic to a shared link costs one DB read, not an ingest |
| `MAX_REPOS` | 15 | ~135 GitHub calls per cold generate |
| `GENERATE_RATE_LIMIT` | 10/hr | Per-caller sliding window ([limits.py](apps/api/app/limits.py)) |
| `GENERATE_GLOBAL_HOURLY_CAP` | 250/hr | Backstop when every request shares one proxy IP |

## Production notes / next steps

- **Database:** dev uses SQLite via `DATABASE_URL`; production requires a
  Postgres DSN. With `ENVIRONMENT=production` the app refuses to boot on SQLite
  or without a `GITHUB_TOKEN`, since both look fine locally and fail only under
  real traffic. See [DEPLOY.md](DEPLOY.md).
- **Deploy:** Vercel (web) + Render/Railway (api). Render's free tier sleeps on
  idle — keep `/api/health` warm or use a paid instance.
- **Privacy:** [/privacy](apps/web/app/privacy/page.tsx) documents what is read
  and stored, and the owner-authenticated deletion path.
- **Not yet built (future slices):** Notion/Figma ingestion, profile analytics,
  tests and CI.
