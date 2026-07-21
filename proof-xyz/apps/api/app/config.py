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


@lru_cache
def get_settings() -> Settings:
    return Settings()
