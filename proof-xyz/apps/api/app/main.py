"""proof.xyz API — ingest GitHub, synthesize a swipeable proof-of-work deck.

Endpoints:
  GET    /api/health
  POST   /api/generate              {username, theme?, token?} -> Profile
  GET    /api/profile/{username}    -> Profile
  DELETE /api/profile/{username}    {token} -> removes profile + its shares
  POST   /api/share                 -> {token}
  GET    /api/share/{token}         -> Profile
  GET    /api/auth/github/login     -> 302 to GitHub OAuth
  GET    /api/auth/github/callback  -> exchanges code, ingests, 302 to web app
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import github_client, store, synth
from .config import get_settings
from .limits import SlidingWindowLimiter, client_key
from .schemas import DeleteRequest, GenerateRequest, Profile, ShareRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proof.api")

app = FastAPI(title="proof.xyz API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.web_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GitHub's own rule: alphanumerics and single inner hyphens, max 39 chars.
# Validating up front keeps junk out of the upstream URL and out of the cache.
_HANDLE_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}")

# Per-caller bound, and a global backstop for when X-Forwarded-For is spoofed
# or every request genuinely shares one proxy address.
_per_client = SlidingWindowLimiter(settings.generate_rate_limit)
_global = SlidingWindowLimiter(settings.generate_global_hourly_cap)

# Name of the cookie holding the OAuth CSRF nonce.
_STATE_COOKIE = "devreel_oauth_state"


def _clean_handle(raw: str) -> str:
    handle = raw.strip().lstrip("@")
    if not _HANDLE_RE.fullmatch(handle):
        raise HTTPException(status_code=400, detail="That isn't a valid GitHub username.")
    return handle


async def _generate(username: str, theme: str, token: str | None) -> Profile:
    try:
        data = await github_client.ingest(username, token=token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="GitHub took too long to respond — try again."
        )
    except httpx.HTTPStatusError as exc:
        # Most commonly an unauthenticated rate-limit (403) from GitHub.
        detail = "GitHub API error"
        if exc.response.status_code == 403:
            detail = "GitHub rate limit hit — add a token to raise the limit."
        raise HTTPException(status_code=502, detail=detail)

    # synthesize() makes a blocking Gemini call (up to GEMINI_TIMEOUT_SECONDS).
    # Left on the event loop it would stall every other in-flight request for
    # the whole duration, so it runs on a worker thread.
    headline, pitch, cards, generated_with = await asyncio.to_thread(
        synth.synthesize, data
    )

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
    return profile


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "generative_layer": synth.resolve_provider(settings),
        "oauth_configured": bool(settings.github_client_id and settings.github_client_secret),
    }


@app.post("/api/generate", response_model=Profile)
async def generate(req: GenerateRequest, request: Request):
    handle = _clean_handle(req.username)

    # 1. Serve a recent profile rather than re-ingesting. This is the main cost
    #    control: repeat traffic to the same handle (the common case for a
    #    résumé link) never touches GitHub or the LLM. A caller-supplied token
    #    is skipped, since it may unlock private repos the cache doesn't have.
    if not req.token:
        age = await asyncio.to_thread(store.get_age_hours, handle)
        if age is not None and age < settings.profile_cache_hours:
            cached = await asyncio.to_thread(store.get, handle)
            if cached:
                if req.theme and req.theme != cached.theme:
                    # Honour the newly picked vibe without resetting cache age.
                    cached.theme = req.theme
                    await asyncio.to_thread(store.save, cached, touch=False)
                return cached

    # 2. A cold generate costs real quota, so bound it.
    allowed, retry = _global.try_acquire("all")
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail="We're at capacity right now — please try again shortly.",
            headers={"Retry-After": str(retry)},
        )
    caller = client_key(request.headers, request.client.host if request.client else None)
    allowed, retry = _per_client.try_acquire(caller)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've generated a lot of reels in the last hour. "
                f"Try again in about {max(1, retry // 60)} minute(s)."
            ),
            headers={"Retry-After": str(retry)},
        )

    return await _generate(handle, req.theme, req.token)


@app.get("/api/profile/{username}", response_model=Profile)
async def get_profile(username: str):
    profile = await asyncio.to_thread(store.get, _clean_handle(username))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — generate it first.")
    return profile


@app.delete("/api/profile/{username}")
async def delete_profile(username: str, req: DeleteRequest):
    """Remove a profile and every share snapshot made from it.

    Requires a GitHub token belonging to that account. Without proof of
    ownership anyone could break someone else's shared résumé links.
    """
    handle = _clean_handle(username)
    if not await github_client.verify_owner(handle, req.token):
        raise HTTPException(
            status_code=403,
            detail="That GitHub token doesn't belong to this account.",
        )
    deleted = await asyncio.to_thread(store.delete, handle)
    if not deleted:
        raise HTTPException(status_code=404, detail="No stored profile for that account.")
    logger.info("Deleted profile and shares for %s at owner request.", handle)
    return {"deleted": True, "username": handle}


@app.post("/api/share")
async def create_share(req: ShareRequest):
    """Create a unique, read-only share link showing only the chosen projects."""
    profile = await asyncio.to_thread(store.get, _clean_handle(req.username))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — generate it first.")

    allowed = {r for r in req.repos}
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
async def get_share(token: str):
    # Read-only: does NOT count a view (page render + OG image both hit this).
    snapshot = await asyncio.to_thread(store.get_share, token)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Share link not found.")
    return snapshot


@app.post("/api/share/{token}/view")
async def record_view(token: str):
    """Count one real browser open (fired client-side, not on prefetch/OG)."""
    views = await asyncio.to_thread(store.bump_share_view, token)
    if views is None:
        raise HTTPException(status_code=404, detail="Share link not found.")
    return {"views": views}


@app.get("/api/share/{token}/stats")
async def share_stats(token: str):
    views = await asyncio.to_thread(store.share_views, token)
    if views is None:
        raise HTTPException(status_code=404, detail="Share link not found.")
    return {"views": views}


@app.get("/api/auth/github/login")
async def github_login():
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured.")
    redirect_uri = f"{settings.api_base_url}/api/auth/github/callback"
    # CSRF nonce: echoed by GitHub and checked on the way back, so a third
    # party can't feed us an authorization code they obtained themselves.
    state = secrets.token_urlsafe(24)
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        "&scope=read:user,public_repo"
    )
    response = RedirectResponse(url)
    # Lax still travels on the top-level GET redirect back from github.com.
    response.set_cookie(
        _STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/api/auth/github",
    )
    return response


@app.get("/api/auth/github/callback")
async def github_callback(request: Request, code: str, state: str = ""):
    if not (settings.github_client_id and settings.github_client_secret):
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured.")

    expected = request.cookies.get(_STATE_COOKIE)
    # compare_digest keeps the check constant-time; the empty-value guard stops
    # a missing cookie from matching a missing state parameter.
    if not expected or not state or not secrets.compare_digest(state, expected):
        raise HTTPException(
            status_code=400, detail="Login session expired or invalid — please try again."
        )

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
    await _generate(username, theme="midnight", token=access_token)
    response = RedirectResponse(f"{settings.web_redirect_url}/{username}")
    response.delete_cookie(_STATE_COOKIE, path="/api/auth/github")
    return response
