from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, sourced from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Generative layer ---
    # Which LLM provider synthesizes the cards. "auto" picks whichever key is
    # present (Gemini first, then Claude), else the rules-based fallback.
    llm_provider: str = "auto"  # auto | gemini | claude | rules

    # Google Gemini — free tier, no credit card. Get a key at
    # https://aistudio.google.com/apikey
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # Anthropic Claude — optional alternate (paid). Get a key at
    # https://console.anthropic.com/
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"

    # Hard cap on a single LLM call. Past this we fall back to the rules deck
    # rather than leaving the request hanging.
    llm_timeout: int = 90
    # Repos per LLM request. Batches run in parallel, so a 50-repo profile is
    # ~5 concurrent short calls instead of one long one (which also overflowed
    # the output-token cap and fell back to rules). Lower = faster but more
    # requests against the provider's per-minute quota.
    llm_batch_size: int = 12

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

    # Upper bound on repos to ingest, ranked by stars then recency. Set high
    # enough to mean "all" for typical accounts; bounds runtime on huge ones.
    max_repos: int = 50

    # --- Scaling ---
    # Shared Redis for rate limits, cooldowns and generation locks. Required
    # when running more than one worker or instance behind a load balancer;
    # unset = process-local memory (fine for a single instance).
    redis_url: str | None = None

    # --- Abuse protection ---
    # Fresh generations allowed per client IP per window. Each one costs ~200
    # GitHub calls and an LLM call, so this is what protects both quotas.
    generate_rate_limit: int = 5
    generate_rate_window: int = 600  # seconds
    # A username regenerated within this many seconds is served from the
    # stored copy instead of re-ingesting (token-carrying requests bypass it).
    regenerate_cooldown: int = 600

    # Serve the interactive /docs and /openapi.json. Turn off in production.
    enable_docs: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
