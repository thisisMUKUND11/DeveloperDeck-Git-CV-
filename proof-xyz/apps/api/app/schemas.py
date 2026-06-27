from __future__ import annotations

from pydantic import BaseModel, Field


# --- Raw ingestion shapes -------------------------------------------------


class Repo(BaseModel):
    """A single repository pulled from GitHub, post-enrichment."""

    name: str
    full_name: str
    description: str | None = None
    html_url: str
    private: bool = False
    stars: int = 0
    forks: int = 0
    primary_language: str | None = None
    languages: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    readme_excerpt: str | None = None
    # Human-readable skills inferred from deps/manifests, e.g. "NLP", "Data Viz".
    skills: list[str] = Field(default_factory=list)


class IngestResult(BaseModel):
    username: str
    name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    followers: int = 0
    public_repos: int = 0
    repos: list[Repo] = Field(default_factory=list)
    # Union of every inferred skill across repos, deduped.
    all_skills: list[str] = Field(default_factory=list)
    # True only if we could actually read private repos (token owner + 'repo' scope).
    private_access: bool = False


# --- LLM output shapes (what the model generates) -------------------------


class GeneratedCard(BaseModel):
    """The model-authored description of one PUBLIC repo."""

    repo: str = Field(description="The repository name this describes (must match input).")
    summary: str = Field(
        description="One sentence: what kind of project this is (e.g. 'A mobile app for...', 'A CLI tool that...')."
    )
    why: list[str] = Field(
        default_factory=list,
        description="3-4 short bullet points (each a complete thought, ~8-16 words): the real-world problem it solves, who uses it, the pain point removed, and why it matters. Concrete, not generic.",
    )
    how: list[str] = Field(
        default_factory=list,
        description="3-5 short bullet points (each ~8-18 words): the architecture, the main components and how they fit, the key data flow/algorithm, and notable libraries/frameworks and their role. Grounded in the data.",
    )
    stat: str = Field(
        description="One clean micro-metric drawn from the data, e.g. '1.2k stars' or '8 languages'."
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Up to 4 of the most impressive inferred skill tags.",
    )


class GeneratedDeck(BaseModel):
    headline: str = Field(
        description="A 1-line identity statement for the whole profile. Confident, builder-focused, no fluff."
    )
    cards: list[GeneratedCard]


# --- Stored / served card (LLM output + raw GitHub facts merged) ----------


class Card(BaseModel):
    """One repo card as rendered. Private repos are 'locked' (no detail)."""

    repo: str
    visibility: str = "public"  # "public" | "private"
    locked: bool = False  # true for private repos — details intentionally hidden
    languages: list[str] = Field(default_factory=list)
    summary: str = ""
    why: list[str] = Field(default_factory=list)
    how: list[str] = Field(default_factory=list)
    stat: str = ""
    skills: list[str] = Field(default_factory=list)
    url: str = ""


# --- Stored / served profile ----------------------------------------------


class Profile(BaseModel):
    username: str
    name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    theme: str = "neo-brutalist"
    headline: str = ""
    cards: list[Card] = Field(default_factory=list)
    public_count: int = 0
    private_count: int = 0
    # False when private repos couldn't be read (so the UI can say so).
    private_access: bool = False
    generated_with: str = "rules"  # "gemini" | "claude" | "rules"
    # Set on shared snapshots (read-only recruiter views).
    shared: bool = False


class GenerateRequest(BaseModel):
    username: str
    theme: str = "neo-brutalist"
    # Optional token to lift rate limits / read private repos for this run.
    token: str | None = None


class ShareRequest(BaseModel):
    username: str
    # Repo names the owner chose to include in this shared link.
    repos: list[str] = Field(default_factory=list)
    theme: str = "neo-brutalist"
