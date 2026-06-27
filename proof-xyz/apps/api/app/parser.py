"""Infer human-readable skills from a repo's languages, topics, and manifests.

This is the "ingestion & analysis" step: it doesn't just read names — it
matches import/dependency signatures to capability labels a recruiter
understands. `import spacy` -> "NLP"; `matplotlib` -> "Data Visualization".
"""

from __future__ import annotations

import re

# Dependency / import token -> skill label. Tokens are matched case-insensitively
# against manifest contents (requirements.txt, package.json, pyproject.toml, etc.).
DEP_SIGNATURES: dict[str, str] = {
    # ML / data science
    "spacy": "Natural Language Processing",
    "nltk": "Natural Language Processing",
    "transformers": "LLMs & Transformers",
    "torch": "Deep Learning",
    "pytorch": "Deep Learning",
    "tensorflow": "Deep Learning",
    "keras": "Deep Learning",
    "scikit-learn": "Machine Learning",
    "sklearn": "Machine Learning",
    "xgboost": "Machine Learning",
    "pandas": "Data Engineering",
    "numpy": "Numerical Computing",
    "matplotlib": "Data Visualization",
    "seaborn": "Data Visualization",
    "plotly": "Data Visualization",
    "d3": "Data Visualization",
    "opencv": "Computer Vision",
    "cv2": "Computer Vision",
    "pillow": "Image Processing",
    "anthropic": "LLM Applications",
    "openai": "LLM Applications",
    "langchain": "LLM Applications",
    # web / backend
    "fastapi": "API Engineering",
    "flask": "Backend (Python)",
    "django": "Backend (Django)",
    "express": "Backend (Node)",
    "next": "Frontend (Next.js)",
    "react": "Frontend (React)",
    "vue": "Frontend (Vue)",
    "svelte": "Frontend (Svelte)",
    "tailwindcss": "UI / Design Systems",
    "framer-motion": "Motion & Interaction",
    "three": "3D / WebGL",
    # data / infra
    "redis": "Caching & Queues",
    "postgres": "Databases",
    "psycopg2": "Databases",
    "sqlalchemy": "Databases",
    "prisma": "Databases",
    "mongodb": "Databases (NoSQL)",
    "mongoose": "Databases (NoSQL)",
    "kafka": "Event Streaming",
    "docker": "Containerization",
    "kubernetes": "Orchestration",
    "terraform": "Infrastructure as Code",
    "boto3": "Cloud (AWS)",
    # mobile
    "flutter": "Mobile (Flutter)",
    "react-native": "Mobile (React Native)",
    "swift": "Mobile (iOS)",
}

# Language name -> skill label, used as a fallback signal.
LANGUAGE_SKILLS: dict[str, str] = {
    "Python": "Python",
    "TypeScript": "TypeScript",
    "JavaScript": "JavaScript",
    "Go": "Go",
    "Rust": "Rust",
    "Java": "Java",
    "Kotlin": "Kotlin",
    "Swift": "Swift",
    "C++": "C++",
    "Solidity": "Smart Contracts",
    "Dart": "Dart",
}

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_\-]+")


def skills_from_manifest(text: str) -> list[str]:
    """Scan a dependency manifest's raw text for known signatures."""
    if not text:
        return []
    tokens = {t.lower() for t in _TOKEN_RE.findall(text)}
    found: list[str] = []
    for dep, label in DEP_SIGNATURES.items():
        if dep in tokens and label not in found:
            found.append(label)
    return found


def skills_from_languages(languages: list[str]) -> list[str]:
    out: list[str] = []
    for lang in languages:
        label = LANGUAGE_SKILLS.get(lang)
        if label and label not in out:
            out.append(label)
    return out


def skills_from_topics(topics: list[str]) -> list[str]:
    """GitHub topics are author-curated and often the cleanest signal."""
    out: list[str] = []
    for topic in topics:
        normalized = topic.replace("-", " ").title()
        if normalized not in out:
            out.append(normalized)
    return out


def merge_skills(*groups: list[str], limit: int = 8) -> list[str]:
    seen: list[str] = []
    for group in groups:
        for s in group:
            if s not in seen:
                seen.append(s)
    return seen[:limit]
