"""The generative layer.

Takes enriched ingestion data and produces a profile headline plus one card
per repo. Public repos get a model-authored what / why / how breakdown; private
repos are surfaced as locked cards (no detail). Languages, visibility and URL
are always taken from the raw GitHub facts, never invented.

Primary path uses Google Gemini (free tier) via structured output. If no key is
configured — or the call fails or times out — a deterministic rules-based
synthesizer keeps the flow working end-to-end.
"""

from __future__ import annotations

import logging

from .config import get_settings
from .schemas import Card, GeneratedCard, GeneratedDeck, IngestResult, Repo

logger = logging.getLogger("proof.synth")

SYSTEM = """You turn raw GitHub data into a clear, scannable proof-of-work \
portfolio for recruiters and collaborators.

Voice: concrete, builder-focused, plain English. No corporate filler, no \
buzzword soup, no emoji. Every claim must be grounded in the data provided — \
never invent metrics, users, adoption, or outcomes that aren't supported. If \
the data is thin, describe what the code plausibly does based on its \
language, dependencies, and README, and keep it modest.

For each repository produce:
- summary: ONE sentence naming what kind of project it is (e.g. "A Flutter \
  mobile app that...", "A Python CLI that...", "A web dashboard for...").
- why: 3-4 short, punchy bullet points (each a complete thought, ~8-16 words). \
  Cover the real-world problem it solves, who would use it, the pain point it \
  removes, and why that matters. Be concrete about the use case, not generic. \
  Do not number the bullets or add leading dashes — just the text of each point.
- how: 3-5 short bullet points (each ~8-18 words). Cover the overall \
  architecture, the main components and how they fit together, the key data \
  flow or algorithm, and the notable libraries/frameworks and what each does. \
  Ground every claim in the languages, dependencies, and README — if a detail \
  isn't supported, describe the plausible approach modestly rather than \
  inventing specifics. No numbering or leading dashes — just each point's text.
- stat: ONE clean micro-metric from the data (stars, forks, or language count).
- skills: up to 4 of the most relevant inferred skill tags.

Also write, for the whole profile:
- headline: a single identity statement, max ~10 words.
- pitch: one punchy elevator-pitch sentence (~12-22 words) capturing what this \
  person builds and is good at, grounded in their actual repositories."""


def _repo_block(repo: Repo) -> str:
    lines = [
        f"## {repo.name}",
        f"description: {repo.description or '(none)'}",
        f"stars: {repo.stars} | forks: {repo.forks} | primary_language: {repo.primary_language or 'n/a'}",
        f"languages: {', '.join(repo.languages) or 'n/a'}",
        f"inferred_skills: {', '.join(repo.skills) or 'n/a'}",
        f"topics: {', '.join(repo.topics) or 'n/a'}",
    ]
    if repo.readme_excerpt:
        lines.append(f"readme_excerpt:\n{repo.readme_excerpt[:1500]}")
    return "\n".join(lines)


def _build_prompt(data: IngestResult, public_repos: list[Repo]) -> str:
    header = (
        f"GitHub user: {data.username}"
        + (f" ({data.name})" if data.name else "")
        + f"\nbio: {data.bio or '(none)'}"
        f"\nfollowers: {data.followers} | public_repos: {data.public_repos}"
        f"\noverall_skills: {', '.join(data.all_skills) or 'n/a'}\n"
    )
    repos = "\n\n".join(_repo_block(r) for r in public_repos)
    return (
        header
        + "\n--- PUBLIC REPOSITORIES (ranked) ---\n\n"
        + repos
        + "\n\nGenerate the headline and one card per repository above."
    )


# --- public API -----------------------------------------------------------


def resolve_provider(settings) -> str:
    if settings.llm_provider != "auto":
        return settings.llm_provider
    return "gemini" if settings.gemini_api_key else "rules"


def synthesize(data: IngestResult) -> tuple[str, str, list[Card], str]:
    """Return (headline, pitch, cards, generated_with).

    Private repos always become locked cards; only public repos go to the LLM.
    """
    settings = get_settings()
    provider = resolve_provider(settings)
    public = [r for r in data.repos if not r.private]

    headline = ""
    pitch = ""
    generated: dict[str, GeneratedCard] = {}
    used = "rules"

    if public:
        deck: GeneratedDeck | None = None
        if provider == "gemini" and settings.gemini_api_key:
            try:
                deck = _gemini_deck(data, public, settings)
                used = "gemini"
            except Exception as exc:  # pragma: no cover
                logger.warning("Gemini synthesis failed (%s); using rules.", exc)

        if deck is None:
            deck = _rules_deck(data, public)
            used = "rules"

        headline, pitch, generated = deck.headline, deck.pitch, _by_repo(deck)
    else:
        headline = f"{data.name or data.username} — builder"

    cards = _assemble(data, generated)
    return headline, pitch, cards, used


# --- assembly -------------------------------------------------------------


def _by_repo(deck: GeneratedDeck) -> dict[str, GeneratedCard]:
    return {c.repo: c for c in deck.cards}


def _assemble(data: IngestResult, generated: dict[str, GeneratedCard]) -> list[Card]:
    """Merge model output with hard GitHub facts; build locked cards for private."""
    cards: list[Card] = []
    for repo in data.repos:
        if repo.private:
            cards.append(
                Card(
                    repo=repo.name,
                    visibility="private",
                    locked=True,
                    summary="This repository is private — details are not shown.",
                    url=repo.html_url,
                )
            )
            continue
        g = generated.get(repo.name)
        cards.append(
            Card(
                repo=repo.name,
                visibility="public",
                locked=False,
                languages=repo.languages,
                summary=(g.summary if g else (repo.description or repo.name)),
                why=(g.why if g else []),
                how=(g.how if g else []),
                stat=(g.stat if g else _default_stat(repo)),
                skills=(g.skills[:4] if g else repo.skills[:4]),
                url=repo.html_url,
            )
        )
    return cards


# --- providers ------------------------------------------------------------


def _gemini_deck(data: IngestResult, public: list[Repo], settings) -> GeneratedDeck:
    from google import genai
    from google.genai import types

    # HttpOptions.timeout is in milliseconds. Without it a hung provider would
    # hold the request open indefinitely; on expiry we fall back to rules.
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=int(settings.gemini_timeout_seconds * 1000)
        ),
    )
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=_build_prompt(data, public),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=GeneratedDeck,
            temperature=0.6,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    deck = response.parsed
    if deck is None:
        if not response.text:
            raise ValueError("Gemini returned no output")
        deck = GeneratedDeck.model_validate_json(response.text)
    if not isinstance(deck, GeneratedDeck):
        deck = GeneratedDeck.model_validate(deck)
    return deck


# --- rules-based fallback -------------------------------------------------


def _rules_deck(data: IngestResult, public: list[Repo]) -> GeneratedDeck:
    cards: list[GeneratedCard] = []
    for repo in public:
        summary = (repo.description or _first_sentence(repo.readme_excerpt) or repo.name).strip()[:120]

        why: list[str] = []
        if repo.description:
            why.append(repo.description.strip()[:120])
        if repo.topics:
            why.append("Relevant to " + ", ".join(repo.topics[:3]) + ".")
        why.append(
            f"Useful to anyone working with {repo.primary_language}."
            if repo.primary_language
            else "A public project on GitHub."
        )

        how: list[str] = []
        if repo.primary_language:
            how.append(f"Written primarily in {repo.primary_language}.")
        if repo.languages:
            how.append("Spans " + ", ".join(repo.languages[:4]) + ".")
        if repo.skills:
            how.append("Applies " + ", ".join(repo.skills[:3]) + ".")
        if not how:
            how.append("See the repository for implementation details.")

        cards.append(
            GeneratedCard(
                repo=repo.name,
                summary=summary,
                why=why[:4],
                how=how[:5],
                stat=_default_stat(repo),
                skills=repo.skills[:4],
            )
        )
    name = data.name or data.username
    tail = ", ".join(data.all_skills[:3])
    headline = (f"{name} — builder shipping {tail}" if tail else f"{name} — builder")[:80]
    pitch = (
        f"{name} ships across {len(public)} public projects"
        + (f", working with {tail}." if tail else ".")
    )
    return GeneratedDeck(headline=headline, pitch=pitch, cards=cards)


def _default_stat(repo: Repo) -> str:
    if repo.stars:
        return f"{_compact(repo.stars)} stars"
    if repo.languages:
        return f"{len(repo.languages)} languages"
    return f"{repo.forks} forks"


def _first_sentence(text: str | None) -> str | None:
    if not text:
        return None
    for line in text.splitlines():
        s = line.strip().lstrip("#").strip()
        if len(s) > 15:
            return s.split(". ")[0]
    return None


def _compact(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)
