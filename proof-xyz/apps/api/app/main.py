"""proof.xyz API — ingest GitHub, synthesize a swipeable proof-of-work deck.

Endpoints:
  GET  /api/health
  POST /api/generate              {username, theme?, token?} -> Profile
  GET  /api/profile/{username}    -> Profile
  GET  /api/auth/github/login     -> 302 to GitHub OAuth
  GET  /api/auth/github/callback  -> exchanges code, ingests, 302 to web app
"""

from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import secrets

from . import github_client, store, synth
from .config import get_settings
from .schemas import GenerateRequest, Profile, ShareRequest

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="proof.xyz API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _generate(username: str, theme: str, token: str | None) -> Profile:
    try:
        data = await github_client.ingest(username, token=token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        # Most commonly an unauthenticated rate-limit (403) from GitHub.
        detail = "GitHub API error"
        if exc.response.status_code == 403:
            detail = "GitHub rate limit hit — add a token to raise the limit."
        raise HTTPException(status_code=502, detail=detail)

    headline, cards, generated_with = synth.synthesize(data)
    profile = Profile(
        username=data.username,
        name=data.name,
        avatar_url=data.avatar_url,
        bio=data.bio,
        theme=theme,
        headline=headline,
        cards=cards,
        public_count=sum(1 for c in cards if not c.locked),
        private_count=sum(1 for c in cards if c.locked),
        private_access=data.private_access,
        generated_with=generated_with,
    )
    store.save(profile)
    return profile


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "generative_layer": synth.resolve_provider(settings),
        "oauth_configured": bool(settings.github_client_id and settings.github_client_secret),
    }


@app.post("/api/generate", response_model=Profile)
async def generate(req: GenerateRequest):
    return await _generate(req.username, req.theme, req.token)


@app.get("/api/profile/{username}", response_model=Profile)
async def get_profile(username: str):
    profile = store.get(username)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — generate it first.")
    return profile


@app.post("/api/share")
async def create_share(req: ShareRequest):
    """Create a unique, read-only share link showing only the chosen projects."""
    profile = store.get(req.username)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found — generate it first.")

    allowed = {r for r in req.repos}
    selected = [c for c in profile.cards if c.repo in allowed and not c.locked]
    if not selected:
        raise HTTPException(status_code=400, detail="Select at least one public project to share.")

    snapshot = Profile(
        username=profile.username,
        name=profile.name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        theme=req.theme or profile.theme,
        headline=profile.headline,
        cards=selected,
        public_count=len(selected),
        private_count=0,
        private_access=False,
        generated_with=profile.generated_with,
        shared=True,
    )
    # A fresh token every time → each shared link is unique.
    token = secrets.token_urlsafe(9)
    store.save_share(token, snapshot)
    return {"token": token}


@app.get("/api/share/{token}", response_model=Profile)
async def get_share(token: str):
    snapshot = store.get_share(token)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Share link not found or expired.")
    return snapshot


@app.get("/api/auth/github/login")
async def github_login():
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured.")
    redirect_uri = f"{settings.api_base_url}/api/auth/github/callback"
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={redirect_uri}"
        "&scope=read:user,public_repo"
    )
    return RedirectResponse(url)


@app.get("/api/auth/github/callback")
async def github_callback(code: str):
    if not (settings.github_client_id and settings.github_client_secret):
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured.")

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
    await _generate(username, theme="neo-brutalist", token=access_token)
    return RedirectResponse(f"{settings.web_base_url}/{username}")
