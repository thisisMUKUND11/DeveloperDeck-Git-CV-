import pytest

from app import synth
from app.config import get_settings
from app.github_client import _manifest_paths
from app.schemas import GeneratedCard, GeneratedDeck

from .conftest import fake_ingest_result


def test_rejects_unsafe_usernames_and_unknown_themes(client):
    assert client.post("/api/generate", json={"username": "../repos/x"}).status_code == 422
    assert client.post("/api/generate", json={"username": "ok", "theme": "evil"}).status_code == 422
    assert client.get("/api/share/x").status_code == 422


def test_private_repos_are_masked(client):
    r = client.post("/api/generate", json={"username": "alice"})
    assert r.status_code == 200, r.text
    locked = [c for c in r.json()["cards"] if c["locked"]]
    assert len(locked) == 1
    assert locked[0]["repo"] == "Private project 1"
    assert locked[0]["url"] == ""
    assert "secret-plan" not in r.text


def test_cooldown_serves_stored_copy_and_rethemes(client, ingest_calls):
    client.post("/api/generate", json={"username": "alice"})
    r = client.post("/api/generate", json={"username": "Alice", "theme": "paper"})
    assert r.status_code == 200
    assert r.json()["theme"] == "paper"
    assert ingest_calls == ["alice"]


def test_generate_rate_limit_is_per_ip(client):
    assert client.post("/api/generate", json={"username": "bob"}).status_code == 200
    assert client.post("/api/generate", json={"username": "carol"}).status_code == 200
    assert client.post("/api/generate", json={"username": "dave"}).status_code == 429
    other_ip = {"x-forwarded-for": "9.9.9.9, 10.0.0.1"}
    r = client.post("/api/generate", json={"username": "dave"}, headers=other_ip)
    assert r.status_code == 200


def test_share_views_count_once_per_visitor(client):
    client.post("/api/generate", json={"username": "erin"})
    r = client.post("/api/share", json={"username": "erin", "repos": ["pub"]})
    token = r.json()["token"]
    assert client.post(f"/api/share/{token}/view").json()["views"] == 1
    assert client.post(f"/api/share/{token}/view").json()["views"] == 1
    other = {"x-forwarded-for": "8.8.8.8"}
    assert client.post(f"/api/share/{token}/view", headers=other).json()["views"] == 2
    assert client.get(f"/api/share/{token}/stats").json()["views"] == 2
    assert "max-age" in client.get(f"/api/share/{token}").headers["cache-control"]
    assert client.post("/api/share/zzzzzzzzzz/view").status_code == 404


def test_oauth_callback_requires_matching_state(client):
    r = client.get("/api/auth/github/login", follow_redirects=False)
    assert r.status_code == 307
    assert "state=" in r.headers["location"]
    assert "oauth_state" in r.headers["set-cookie"]
    client.cookies.clear()
    forged = client.get("/api/auth/github/callback?code=x&state=forged", follow_redirects=False)
    assert forged.status_code == 400


def test_health_reports_coordination_backend(client):
    body = client.get("/api/health").json()
    assert body["coordination"] in ("memory", "redis")
    assert body["coordination_ok"] is True


def test_manifest_paths_prefer_shallow_and_skip_vendored():
    paths = [
        "node_modules/x/package.json",
        "apps/web/package.json",
        "apps/api/requirements.txt",
        "README.md",
        "package.json",
        "vendor/go.mod",
        "x/pyproject.toml",
    ]
    tree = {"tree": [{"type": "blob", "path": p} for p in paths]}
    assert _manifest_paths(tree) == [
        "package.json",
        "x/pyproject.toml",
        "apps/api/requirements.txt",
        "apps/web/package.json",
    ]


@pytest.fixture
def batched_llm(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake")
    monkeypatch.setattr(settings, "llm_batch_size", 2)
    batches: list[list[str]] = []

    def fake_llm(data, public, settings):
        names = [r.name for r in public]
        batches.append(names)
        if "r3" in names:
            raise RuntimeError("quota exceeded")
        return GeneratedDeck(
            headline=f"headline for {names[0]}",
            pitch="pitch",
            cards=[GeneratedCard(repo=n, summary=f"llm {n}", stat="1 star") for n in names],
        )

    monkeypatch.setattr(synth, "_gemini_deck", fake_llm)
    return batches


def test_llm_runs_in_batches_and_falls_back_per_batch(batched_llm):
    data = fake_ingest_result("frank")
    template = data.repos[0]
    data.repos = [template.model_copy(update={"name": f"r{i}"}) for i in range(5)]

    headline, _, cards, used = synth.synthesize(data)

    assert sorted(batched_llm) == [["r0", "r1"], ["r2", "r3"], ["r4"]]
    assert used == "gemini"
    assert headline == "headline for r0"
    by_repo = {c.repo: c.summary for c in cards}
    assert by_repo["r0"] == "llm r0"
    assert by_repo["r4"] == "llm r4"
    # The failed batch got rules-based cards rather than nothing.
    assert by_repo["r2"] == "A thing"
    assert by_repo["r3"] == "A thing"
