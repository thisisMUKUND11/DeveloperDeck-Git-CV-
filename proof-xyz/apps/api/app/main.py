"""proof.xyz API — ingest GitHub, synthesize a swipeable proof-of-work deck.

Endpoints:
  GET  /api/health
  POST /api/generate              {username, theme?, token?} -> Profile
  GET  /api/profile/{username}    -> Profile
  POST /api/share                 {username, repos, theme?} -> {token}
  GET  /api/share/{token}         -> Profile (read-only snapshot)
  POST /api/share/{token}/view    -> {views}
  GET  /api/share/{token}/stats   -> {views}
  GET  /api/auth/github/login     -> 302 to GitHub OAuth
  GET  /api/auth/github/callback  -> exchanges code, ingests, 302 to web app
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import Cookie, FastAPI, HTTPException, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse

from . import coordination, github_client, store, synth
from .config import get_settings
from .coordination import client_ip
from .schemas import USERNAME_PATTERN, GenerateRequest, Profile, ShareRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proof.api")

settings = get_settings()
# Rate limits, cooldown and per-username locks: Redis when REDIS_URL is set
# (multi-instance / load balanced), otherwise process memory.
coord = coordination.create(settings.redis_url)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema + connection pool are set up once here, not on every request.
    await asyncio.to_thread(store.init)
    yield
    await asyncio.to_thread(store.close)
    await coord.close()


app = FastAPI(
    title="proof.xyz API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.web_origins,
    # The browser API calls carry no cookies; the OAuth state cookie is set and
    # read on top-level navigations to this origin, which CORS doesn't govern.
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
# A full profile is tens of KB of repetitive JSON; gzip shrinks it ~5x.
app.add_middleware(GZipMiddleware, minimum_size=1024)

UsernamePath = Annotated[str, Path(pattern=USERNAME_PATTERN)]
# secrets.token_urlsafe(9) yields 12 chars; leave headroom, reject junk.
TokenPath = Annotated[str, Path(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]

# Share links per IP per hour, and one counted view per visitor per link per
# 30 min (so refreshing doesn't inflate the count).
_SHARE_LIMIT, _SHARE_WINDOW = 20, 3600
_VIEW_LIMIT, _VIEW_WINDOW = 1, 1800

_OAUTH_STATE_COOKIE = "oauth_state"
_OAUTH_COOKIE_PATH = "/api/auth/github"


async def _generate(username: str, theme: str, token: str | None) -> Profile:
    try:
        data = await github_client.ingest(username, token=token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        detail = "GitHub API error"
        if status == 401:
            detail = "GitHub rejected the token — check it hasn't expired."
        elif status in (403, 429):
            # Most commonly the unauthenticated 60/hr rate limit.
            detail = "GitHub rate limit hit — add a token to raise the limit."
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.RequestError as exc:
        logger.warning("GitHub unreachable while ingesting %s", username, exc_info=True)
        raise HTTPException(
            status_code=504, detail="GitHub took too long to respond — try again."
        ) from exc

    # The LLM SDK calls are blocking; run them off the event loop so other
    # requests keep being served while a deck is being written.
    headline, pitch, cards, generated_with = await asyncio.to_thread(synth.synthesize, data)

    # Aggregate stats for the TL;DR intro card (from raw GitHub facts).
    public_repos = [r for r in data.repos if not r.private]
    total_stars = sum(r.stars for r in public_repos)
    languages = {lang for r in public_repos for lang in r.languages}

    profile = Profile(
        username=data.username,
        name=data.name,
        avatar_url=data.avatar_url,
        bio=data.bio,
        theme=theme,
        headline=headline,
        pitch=pitch,
        top_skills=data.all_skills[:5],
        total_stars=total_stars,
        language_count=len(languages),
        cards=cards,
        public_count=sum(1 for c in cards if not c.locked),
        private_count=sum(1 for c in cards if c.locked),
        private_access=data.private_access,
        generated_with=generated_with,
    )
    await asyncio.to_thread(store.save, profile)
    await coord.mark_generated(username.lower(), settings.regenerate_cooldown)
    return profile


async def _recent_profile(username: str, theme: str) -> Profile | None:
    """The stored profile if it was generated within the cooldown, re-themed."""
    if not await coord.recently_generated(username, settings.regenerate_cooldown):
        return None
    profile = await asyncio.to_thread(store.get, username)
    if profile and profile.theme != theme:
        profile.theme = theme
        await asyncio.to_thread(store.save, profile)
    return profile


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "generative_layer": synth.resolve_provider(settings),
        "oauth_configured": bool(settings.github_client_id and settings.github_client_secret),
        "coordination": coord.name,
        "coordination_ok": await coord.ping(),
    }


@app.post("/api/generate", response_model=Profile)
async def generate(req: GenerateRequest, request: Request):
    key = req.username.lower()
    # One in-flight ingest per username (across all instances with Redis), so
    # concurrent requests for the same user share one GitHub + LLM run.
    async with coord.generation_lock(key):
        # Token-carrying runs are the owner refreshing (possibly with private
        # repos), so they always re-ingest; anonymous repeats reuse the copy.
        if not req.token:
            recent = await _recent_profile(key, req.theme)
            if recent:
                return recent
        # Only real ingests count against the limit; cached hits are free.
        allowed = await coord.allow(
            "generate",
            client_ip(request),
            settings.generate_rate_limit,
            settings.generate_rate_window,
        )
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many decks generated from your network — try again in a few minutes.",
            )
        return await _generate(req.username, req.theme, req.token)


# Plain `def` endpoints do blocking DB work, so FastAPI runs them in its thread
# pool. Async ones that also await the coordinator push DB calls to a thread.


@app.get("/api/profile/{username}", response_model=Profile)
def get_profile(username: UsernamePath):
    profile = store.get(username)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — generate it first.")
    return profile


@app.post("/api/share")
async def create_share(req: ShareRequest, request: Request):
    """Create a unique, read-only share link showing only the chosen projects."""
    if not await coord.allow("share", client_ip(request), _SHARE_LIMIT, _SHARE_WINDOW):
        raise HTTPException(status_code=429, detail="Too many links created — try again later.")

    profile = await asyncio.to_thread(store.get, req.username)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — generate it first.")

    allowed = set(req.repos)
    selected = [c for c in profile.cards if c.repo in allowed and not c.locked]
    if not selected:
        raise HTTPException(status_code=400, detail="Select at least one public project to share.")

    # Recompute the hero stat from just the selected cards' languages.
    sel_languages = {lang for c in selected for lang in c.languages}

    snapshot = Profile(
        username=profile.username,
        name=profile.name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        theme=req.theme or profile.theme,
        headline=profile.headline,
        pitch=profile.pitch,
        top_skills=profile.top_skills,
        total_stars=profile.total_stars,
        language_count=len(sel_languages) or profile.language_count,
        cards=selected,
        public_count=len(selected),
        private_count=0,
        private_access=False,
        generated_with=profile.generated_with,
        shared=True,
    )
    # A fresh token every time → each shared link is unique.
    token = secrets.token_urlsafe(9)
    await asyncio.to_thread(store.save_share, token, snapshot)
    return {"token": token}


@app.get("/api/share/{token}", response_model=Profile)
def get_share(token: TokenPath, response: Response):
    # Read-only: does NOT count a view (page render + OG image both hit this).
    snapshot = store.get_share(token)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Share link not found or expired.")
    # Snapshots never change after creation, so browsers and CDNs may cache them.
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=86400"
    return snapshot


@app.post("/api/share/{token}/view")
async def record_view(token: TokenPath, request: Request):
    """Count one real browser open (fired client-side, not on prefetch/OG)."""
    visitor = f"{client_ip(request)}:{token}"
    if await coord.allow("view", visitor, _VIEW_LIMIT, _VIEW_WINDOW):
        views = await asyncio.to_thread(store.bump_share_view, token)
    else:
        # Same visitor again within the window: report, don't increment.
        views = await asyncio.to_thread(store.share_views, token)
    if views is None:
        raise HTTPException(status_code=404, detail="Share link not found.")
    return {"views": views}


@app.get("/api/share/{token}/stats")
def share_stats(token: TokenPath):
    views = store.share_views(token)
    if views is None:
        raise HTTPException(status_code=404, detail="Share link not found.")
    return {"views": views}


@app.get("/api/auth/github/login")
async def github_login():
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured.")
    # Random state, echoed back by GitHub and checked against this cookie in the
    # callback, so a forged callback link can't log a victim into an attacker's
    # GitHub session (login CSRF).
    state = secrets.token_urlsafe(32)
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": f"{settings.api_base_url}/api/auth/github/callback",
            "scope": "read:user public_repo",
            "state": state,
        }
    )
    response = RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        path=_OAUTH_COOKIE_PATH,
        httponly=True,
        secure=settings.api_base_url.startswith("https://"),
        samesite="lax",  # still sent on GitHub's top-level redirect back to us
    )
    return response


@app.get("/api/auth/github/callback")
async def github_callback(
    code: str,
    state: str = "",
    oauth_state: Annotated[str | None, Cookie()] = None,
):
    if not (settings.github_client_id and settings.github_client_secret):
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured.")
    if not (state and oauth_state and secrets.compare_digest(state, oauth_state)):
        raise HTTPException(status_code=400, detail="Login expired or invalid — please try again.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="OAuth token exchange failed.")

        me = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": "proof-xyz"},
        )
        me.raise_for_status()
        username = me.json()["login"]

    # Ingest immediately so the user lands on a ready profile.
    async with coord.generation_lock(username.lower()):
        await _generate(username, theme="midnight", token=access_token)
    response = RedirectResponse(f"{settings.web_redirect_url}/{username}")
    response.delete_cookie(_OAUTH_STATE_COOKIE, path=_OAUTH_COOKIE_PATH)
    return response
