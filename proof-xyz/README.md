# proof.xyz

Turn a GitHub profile into a **swipeable, recruiter-ready proof-of-work portfolio**
in ~15 seconds. The platform ingests a user's top repos, reads the code's
dependency signatures to infer real skills, and synthesizes a Gen-Z-friendly
deck (hook / proof / stat per repo) rendered as a mobile-first, themed card stack.

This is the **GitHub vertical slice**: OAuth/username connect → ingest → parse →
generate (Claude) → render at `/<username>`.

```
[ Next.js + Tailwind + Framer Motion ]  apps/web   ── REST/JSON ──┐
                                                                   ▼
[ FastAPI + httpx + Pydantic v2 + Claude ]  apps/api  ── GitHub API
                                                                   │
[ SQLite (dev) / Postgres (prod) ]  ◄──────────────────────────────┘
```

## Repo layout

| Path | What it is |
|------|-----------|
| [apps/api](apps/api) | FastAPI ingestion + synthesis engine |
| [apps/api/app/github_client.py](apps/api/app/github_client.py) | Parallel GitHub ingestion (repos, languages, READMEs, manifests) |
| [apps/api/app/parser.py](apps/api/app/parser.py) | Dependency/import → skill inference (`spacy` → "NLP", etc.) |
| [apps/api/app/synth.py](apps/api/app/synth.py) | The generative layer — Claude (`claude-opus-4-8`), with a rules-based fallback |
| [apps/web](apps/web) | Next.js App Router frontend with the swipeable themed card stack |
| [apps/web/components/CardStack.tsx](apps/web/components/CardStack.tsx) | Framer Motion drag-to-swipe deck |
| [apps/web/lib/themes.ts](apps/web/lib/themes.ts) | Neo-Brutalist / 90s Cinematic Dark / Ghibli Pastel theme containers |

## Run it

### 1. Backend (`apps/api`)

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp .env.example .env        # add ANTHROPIC_API_KEY for Claude synthesis (optional)
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

The API runs at `http://localhost:8000`. Check `GET /api/health` — it reports
whether the **Claude** or **rules** generative layer is active and whether OAuth
is configured.

> **No `ANTHROPIC_API_KEY`?** The synthesizer falls back to a deterministic
> rules-based path so the slice still produces a full deck. Add the key to get
> the Claude-generated hooks/proof/stats.

> **GitHub rate limits:** unauthenticated requests are capped at 60/hr. Add a
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
| `GET`  | `/api/health` | Status + active generative layer |
| `POST` | `/api/generate` | `{username, theme?, token?}` → ingest, synthesize, store, return `Profile` |
| `GET`  | `/api/profile/{username}` | Fetch a stored `Profile` |
| `GET`  | `/api/auth/github/login` | 302 → GitHub OAuth (if configured) |
| `GET`  | `/api/auth/github/callback` | Token exchange → ingest → 302 to web app |

## Generative layer

Provider-agnostic ([apps/api/app/synth.py](apps/api/app/synth.py)), selected via
`LLM_PROVIDER` (`auto` | `gemini` | `claude` | `rules`). `auto` uses whichever
key is configured, falling back to the rules-based synthesizer if none is.

- **Gemini (default, free):** `gemini-2.5-flash` via the `google-genai` SDK with
  native JSON-schema structured output bound to the Pydantic `CardSet`. Get a
  free key (no credit card) at https://aistudio.google.com/apikey and set
  `GEMINI_API_KEY` in `.env`.
- **Claude (optional, paid):** `claude-opus-4-8` via `messages.parse()`. Set
  `ANTHROPIC_API_KEY`.
- **Rules (fallback):** deterministic, offline — first README sentence +
  dependency-derived stats. Always available, no key.

Either LLM path uses the same system prompt enforcing grounded claims (no
invented metrics) and the Gen-Z, builder-focused voice.

## Production notes / next steps

- **Database:** dev uses SQLite via `DATABASE_URL`; swap the DSN + connection
  layer in [store.py](apps/api/app/store.py) for Postgres (`jsonb` profiles).
- **Deploy:** Vercel (web) + Render/Railway (api), per the original spec.
- **Not yet built (future slices):** Notion/Figma ingestion, OG-image
  generation for link unfurls, profile analytics.
