from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, sourced from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Generative layer ---
    # Which LLM provider synthesizes the cards. "auto" uses Gemini when its key
    # is present, else the deterministic rules-based fallback.
    llm_provider: str = "auto"  # auto | gemini | rules

    # Google Gemini — free tier, no credit card. Get a key at
    # https://aistudio.google.com/apikey
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    # Hard ceiling on a single synthesis call, so a hung provider can't pin a
    # request open for the whole GitHub+LLM budget.
    gemini_timeout_seconds: float = 45.0

    # --- GitHub OAuth (optional — public ingestion works without it) ---
    github_client_id: str | None = None
    github_client_secret: str | None = None
    # A personal access token bumps the public API rate limit from 60 to
    # 5000 req/hr and lets us read private repos. Optional.
    github_token: str | None = None

    # --- URLs ---
    # Where the browser is sent back to after OAuth completes. Also the primary
    # CORS origin. Accepts a comma-separated list to allow extra origins (e.g.
    # Vercel preview deploys); the first entry is used for OAuth redirects.
    web_base_url: str = "http://localhost:3000"
    # Public base of this API, used to build the OAuth callback URL.
    api_base_url: str = "http://localhost:8000"

    @property
    def web_origins(self) -> list[str]:
        """CORS allow-list, parsed from the comma-separated web_base_url."""
        return [o.strip() for o in self.web_base_url.split(",") if o.strip()]

    @property
    def web_redirect_url(self) -> str:
        """Primary web origin the browser is redirected to after OAuth."""
        return self.web_origins[0] if self.web_origins else "http://localhost:3000"

    # --- Storage ---
    # Default to a local SQLite file for zero-setup runs. Point this at a
    # Postgres DSN in production (the store layer treats it as opaque).
    database_url: str = "sqlite:///./proof.db"

    # Upper bound on repos to ingest, ranked by stars then recency. Each repo
    # costs ~9 GitHub calls (languages + README + 7 manifests), so this is the
    # main lever on both latency and rate-limit burn: 15 repos ≈ 135 calls,
    # i.e. ~35 cold generates per hour against a token's 5000/hr budget.
    max_repos: int = 15

    # --- Abuse / cost control ---
    # `/api/generate` is unauthenticated and each miss costs a GitHub fan-out
    # plus an LLM call, so both are bounded.
    # Serve a stored profile instead of regenerating when it's younger than this.
    profile_cache_hours: int = 24
    # Sliding-window cap on cache-missing generates per client per hour.
    generate_rate_limit: int = 10
    # Belt-and-braces cap on total cold generates per hour across all clients,
    # so a distributed hammering can't run up an unbounded LLM bill.
    generate_global_hourly_cap: int = 250

    # --- Environment ---
    # "production" turns silent, expensive-to-discover misconfigurations into
    # hard startup failures. Render sets this via render.yaml.
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


def _validate(settings: Settings) -> Settings:
    """Fail fast on config that "works" locally but silently breaks in prod."""
    if not settings.is_production:
        return settings

    problems: list[str] = []
    # SQLite on an ephemeral container looks healthy, then loses every share
    # link on the next redeploy. Refuse to start instead.
    if not settings.database_url.startswith(("postgres://", "postgresql://")):
        problems.append(
            "DATABASE_URL must be a Postgres DSN in production "
            f"(got {settings.database_url.split(':', 1)[0]!r}); SQLite storage is "
            "wiped on every redeploy."
        )
    # Without a token GitHub allows 60 req/hr — not enough for even one profile.
    if not settings.github_token:
        problems.append(
            "GITHUB_TOKEN is required in production; the unauthenticated GitHub "
            "limit of 60 req/hr cannot complete a single profile ingest."
        )
    if problems:
        raise RuntimeError(
            "Invalid production configuration:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )
    return settings


@lru_cache
def get_settings() -> Settings:
    return _validate(Settings())
