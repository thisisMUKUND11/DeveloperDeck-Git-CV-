"""Test setup: env must be configured before `app` is imported (settings are
read once at import time), and GitHub/LLM calls are replaced with fakes."""

import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    LLM_PROVIDER="rules",
    GENERATE_RATE_LIMIT="2",
    GITHUB_CLIENT_ID="cid",
    GITHUB_CLIENT_SECRET="secret",
    API_BASE_URL="http://testserver",
    REDIS_URL="",
)

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import coordination, github_client, main  # noqa: E402
from app.schemas import IngestResult, Repo  # noqa: E402


def fake_ingest_result(username: str) -> IngestResult:
    return IngestResult(
        username=username,
        name="Test User",
        repos=[
            Repo(
                name="pub",
                full_name=f"{username}/pub",
                html_url="https://github.com/x/pub",
                stars=3,
                languages=["Python"],
                skills=["Python"],
                description="A thing",
            ),
            Repo(
                name="secret-plan",
                full_name=f"{username}/secret-plan",
                html_url="https://github.com/x/secret-plan",
                private=True,
            ),
        ],
        all_skills=["Python"],
    )


@pytest.fixture
def ingest_calls(monkeypatch):
    calls: list[str] = []

    async def fake_ingest(username, token=None):
        calls.append(username)
        return fake_ingest_result(username)

    monkeypatch.setattr(github_client, "ingest", fake_ingest)
    return calls


@pytest.fixture(params=["memory", "redis"])
def client(request, monkeypatch, ingest_calls):
    """A TestClient against each coordination backend, with fresh state."""
    if request.param == "redis":
        coord = coordination.RedisCoordinator.__new__(coordination.RedisCoordinator)
        coord._redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    else:
        coord = coordination.MemoryCoordinator()
    monkeypatch.setattr(main, "coord", coord)
    with TestClient(main.app) as c:
        yield c
