"""Async GitHub ingestion.

Works against the public REST API with no auth (rate-limited to 60 req/hr).
Pass a token (from OAuth or a PAT) to lift the limit; when the token's owner
matches the requested username, private repos are included too (and surfaced
as locked cards). Fetches are parallelized (bounded by a semaphore) so a full
profile ingests well within a ~60s budget.
"""

from __future__ import annotations

import asyncio
import base64
from urllib.parse import quote

import httpx

from .config import get_settings
from .parser import (
    merge_skills,
    skills_from_languages,
    skills_from_manifest,
    skills_from_topics,
)
from .schemas import IngestResult, Repo

GITHUB_API = "https://api.github.com"

# Bound concurrent GitHub calls so large accounts don't fan out to hundreds of
# in-flight requests (keeps us polite and within the time budget).
_CONCURRENCY = 8

# Dependency manifest filenames worth reading, in priority order. They're
# located via one recursive tree listing per repo, so a manifest in a subfolder
# (e.g. apps/api/requirements.txt) is found, and absent ones cost no request.
MANIFEST_NAMES = [
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "Pipfile",
    "go.mod",
    "Cargo.toml",
    "pubspec.yaml",
]
# Vendored / generated folders whose manifests describe someone else's code.
_SKIP_DIRS = {"node_modules", "vendor", ".venv", "venv", "dist", "build", "site-packages"}
# Most repos have 1-2 manifests; the cap bounds monorepos.
_MAX_MANIFESTS = 4
# Lockfile-sized manifests add nothing past this point for skill matching.
_MAX_MANIFEST_CHARS = 20_000


def _headers(token: str | None) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "proof-xyz",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _get_json(client: httpx.AsyncClient, url: str, **kwargs):
    resp = await client.get(url, **kwargs)
    # 404: missing. 409: empty repository (no commits, so no tree/contents).
    if resp.status_code in (404, 409):
        return None
    resp.raise_for_status()
    return resp.json()


async def _token_identity(
    client: httpx.AsyncClient, headers: dict[str, str]
) -> tuple[str | None, bool]:
    """Return (token owner login, has_private_scope).

    `has_private_scope` is True when the classic token carries the `repo` scope
    (the only way GitHub will list private repositories)."""
    if "Authorization" not in headers:
        return None, False
    try:
        resp = await client.get(f"{GITHUB_API}/user", headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError:
        return None, False
    scopes = resp.headers.get("x-oauth-scopes", "")
    has_repo = "repo" in [s.strip() for s in scopes.split(",")]
    login = resp.json().get("login")
    return login, has_repo


async def _fetch_all_repos(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    own: bool,
    username: str,
    page_cap: int,
) -> list[dict]:
    """Page through a user's repos. `own` uses the authenticated endpoint so
    private repos are included."""
    repos: list[dict] = []
    for page in range(1, page_cap + 1):
        if own:
            url = f"{GITHUB_API}/user/repos"
            params = {"per_page": 100, "page": page, "affiliation": "owner", "visibility": "all"}
        else:
            url = f"{GITHUB_API}/users/{username}/repos"
            params = {"per_page": 100, "page": page, "type": "owner", "sort": "updated"}
        batch = await _get_json(client, url, headers=headers, params=params)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
    return repos


async def _fetch_readme_excerpt(
    client: httpx.AsyncClient, full_name: str, headers: dict[str, str]
) -> str | None:
    data = await _get_json(client, f"{GITHUB_API}/repos/{full_name}/readme", headers=headers)
    if not data or "content" not in data:
        return None
    try:
        raw = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    except Exception:
        return None
    cleaned = "\n".join(
        line for line in raw.splitlines() if not line.strip().startswith(("![", "<img", "[!["))
    )
    return cleaned[:4000].strip() or None


def _manifest_paths(tree: dict) -> list[str]:
    """Pick the manifests to read from a recursive tree listing: shallowest
    first, then by MANIFEST_NAMES priority, skipping vendored folders."""
    found: list[str] = []
    for entry in tree.get("tree", []):
        if entry.get("type") != "blob":
            continue
        parts = entry["path"].split("/")
        if parts[-1] in MANIFEST_NAMES and not _SKIP_DIRS.intersection(parts[:-1]):
            found.append(entry["path"])
    found.sort(key=lambda p: (p.count("/"), MANIFEST_NAMES.index(p.rsplit("/", 1)[-1])))
    return found[:_MAX_MANIFESTS]


async def _fetch_manifests_text(
    client: httpx.AsyncClient, raw: dict, headers: dict[str, str]
) -> str:
    full_name = raw["full_name"]
    branch = quote(raw.get("default_branch") or "HEAD", safe="")
    tree = await _get_json(
        client,
        f"{GITHUB_API}/repos/{full_name}/git/trees/{branch}",
        headers=headers,
        params={"recursive": "1"},
    )
    if not tree:
        return ""

    async def one(path: str) -> str:
        data = await _get_json(
            client,
            f"{GITHUB_API}/repos/{full_name}/contents/{quote(path)}",
            headers=headers,
        )
        if data and isinstance(data, dict) and data.get("content"):
            try:
                text = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            except Exception:
                return ""
            return text[:_MAX_MANIFEST_CHARS]
        return ""

    chunks = await asyncio.gather(*(one(p) for p in _manifest_paths(tree)))
    return "\n".join(c for c in chunks if c)


def _locked_repo(raw: dict) -> Repo:
    """Private repos are surfaced but never enriched — details stay hidden."""
    return Repo(
        name=raw["name"],
        full_name=raw["full_name"],
        description=None,
        html_url=raw["html_url"],
        private=True,
        stars=raw.get("stargazers_count", 0),
        forks=raw.get("forks_count", 0),
        primary_language=None,
        languages=[],
        topics=[],
        readme_excerpt=None,
        skills=[],
    )


async def _enrich_public_repo(
    client: httpx.AsyncClient, raw: dict, headers: dict[str, str], sem: asyncio.Semaphore
) -> Repo:
    full_name = raw["full_name"]
    async with sem:
        languages_data, readme, manifests = await asyncio.gather(
            _get_json(client, f"{GITHUB_API}/repos/{full_name}/languages", headers=headers),
            _fetch_readme_excerpt(client, full_name, headers),
            _fetch_manifests_text(client, raw, headers),
        )
    languages = list(languages_data.keys()) if languages_data else []
    topics = raw.get("topics", []) or []
    skills = merge_skills(
        skills_from_manifest(manifests),
        skills_from_topics(topics),
        skills_from_languages(languages),
    )
    return Repo(
        name=raw["name"],
        full_name=full_name,
        description=raw.get("description"),
        html_url=raw["html_url"],
        private=False,
        stars=raw.get("stargazers_count", 0),
        forks=raw.get("forks_count", 0),
        primary_language=raw.get("language"),
        languages=languages,
        topics=topics,
        readme_excerpt=readme,
        skills=skills,
    )


async def ingest(username: str, token: str | None = None) -> IngestResult:
    """Pull a user's profile + repos. Public repos are enriched; private repos
    (own account only) are listed as locked."""
    settings = get_settings()
    token = token or settings.github_token
    headers = _headers(token)

    async with httpx.AsyncClient(timeout=25.0) as client:
        user = await _get_json(client, f"{GITHUB_API}/users/{username}", headers=headers)
        if user is None:
            raise ValueError(f"GitHub user '{username}' not found")

        login, has_repo_scope = await _token_identity(client, headers)
        own = bool(login and login.lower() == username.lower())
        # We can only surface private repos when it's the owner's own profile
        # AND the token carries the `repo` scope.
        private_access = own and has_repo_scope

        # Roughly cap total repos so very large accounts stay within budget.
        page_cap = max(1, (settings.max_repos + 99) // 100)
        repos_raw = await _fetch_all_repos(
            client, headers, own=own, username=user["login"], page_cap=page_cap
        )

        # Drop forks and archived; rank by stars then most-recently pushed.
        candidates = [r for r in repos_raw if not r.get("fork") and not r.get("archived")]
        candidates.sort(
            key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")),
            reverse=True,
        )
        candidates = candidates[: settings.max_repos]

        sem = asyncio.Semaphore(_CONCURRENCY)
        enriched: list[Repo] = []
        public_raw = [r for r in candidates if not r.get("private")]
        private_raw = [r for r in candidates if r.get("private")]

        public_repos = await asyncio.gather(
            *(_enrich_public_repo(client, r, headers, sem) for r in public_raw)
        )
        enriched.extend(public_repos)
        enriched.extend(_locked_repo(r) for r in private_raw)

    # Preserve ranked order (gather keeps input order for public; append private).
    name_order = {r["name"]: i for i, r in enumerate(candidates)}
    enriched.sort(key=lambda r: name_order.get(r.name, 1_000_000))

    all_skills = merge_skills(*(r.skills for r in enriched if not r.private), limit=12)

    return IngestResult(
        username=user["login"],
        name=user.get("name"),
        avatar_url=user.get("avatar_url"),
        bio=user.get("bio"),
        followers=user.get("followers", 0),
        public_repos=user.get("public_repos", 0),
        repos=list(enriched),
        all_skills=all_skills,
        private_access=private_access,
    )
