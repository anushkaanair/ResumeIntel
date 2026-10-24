"""Shared JD keyword extraction.

Replaces the earlier "any 3+ letter word, most frequent first" approach, which
treated generic filler ("experience", "team", "ability") as skills and, in the
Weak Detection agent, returned the alphabetically-first missing words rather
than the important ones.

Approach: match a curated vocabulary of technical terms (with aliases) against
the text, then rank what was found by how much the JD emphasises it —
frequency, and whether it appears under a "requirements" style heading versus a
"nice to have" one. It is deliberately a vocabulary match, not an NLP model:
it is deterministic, explainable, and never invents a term that is not in the
JD. Extend ``TERMS`` when a role family needs terms that are missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

# canonical term -> (case-insensitive aliases, case-sensitive aliases)
# Case-sensitive aliases exist for tokens that are ambiguous when lowercased
# ("ML", "Go", "R").
_T = tuple[tuple[str, ...], tuple[str, ...]]

TERMS: dict[str, _T] = {
    # ── languages ─────────────────────────────────────────────────────────
    "python": ((), ()),
    "java": ((), ()),
    "javascript": (("js", "ecmascript"), ()),
    "typescript": (("ts",), ()),
    "c++": (("cpp",), ()),
    "c#": (("csharp",), ()),
    "go": (("golang", "go language"), ()),
    "rust": ((), ()),
    "kotlin": ((), ()),
    "swift": ((), ()),
    "scala": ((), ()),
    "ruby": ((), ()),
    "php": ((), ()),
    "sql": ((), ()),
    "bash": (("shell scripting",), ()),
    "r": (("r programming", "rstudio"), ()),
    "matlab": ((), ()),
    "dart": ((), ()),
    "haskell": ((), ()),
    "julia": ((), ()),
    "objective-c": ((), ()),
    # ── web / backend frameworks ──────────────────────────────────────────
    "react": (("react.js", "reactjs"), ()),
    "next.js": (("nextjs",), ()),
    "vue": (("vue.js", "vuejs"), ()),
    "angular": ((), ()),
    "svelte": ((), ()),
    "node.js": (("nodejs", "node js"), ()),
    "express": (("express.js", "expressjs", "express js"), ()),
    "django": ((), ()),
    "flask": ((), ()),
    "fastapi": ((), ()),
    "spring": (("spring boot", "springboot", "spring framework", "spring mvc"), ()),
    ".net": (("dotnet", "asp.net"), ()),
    "ruby on rails": (("rails",), ()),
    "flutter": ((), ()),
    "react native": ((), ()),
    "tailwind": (("tailwind css",), ()),
    "redux": ((), ()),
    "graphql": ((), ()),
    "grpc": ((), ()),
    "rest": (("restful", "rest api", "rest apis", "restful api", "restful apis"), ()),
    "websocket": (("websockets",), ()),
    "html": (("html5",), ()),
    "css": (("css3",), ()),
    # ── data / ML libraries & tooling ─────────────────────────────────────
    "pytorch": ((), ()),
    "tensorflow": ((), ()),
    "keras": ((), ()),
    "jax": ((), ()),
    "scikit-learn": (("sklearn", "scikit learn"), ()),
    "pandas": ((), ()),
    "numpy": ((), ()),
    "scipy": ((), ()),
    "spark": (("pyspark", "apache spark", "spark sql", "spark streaming"), ()),
    "hadoop": ((), ()),
    "kafka": (("apache kafka",), ()),
    "airflow": (("apache airflow",), ()),
    "dbt": ((), ()),
    "flink": ((), ()),
    "ray": ((), ()),
    "langchain": ((), ()),
    "langgraph": ((), ()),
    "llamaindex": (("llama index",), ()),
    "hugging face": (("huggingface",), ()),
    "transformers": ((), ()),
    "onnx": ((), ()),
    "cuda": ((), ()),
    "mlflow": ((), ()),
    "kubeflow": ((), ()),
    "opencv": ((), ()),
    "xgboost": (("lightgbm", "gradient boosting"), ()),
    # ── infra / cloud / devops ────────────────────────────────────────────
    "aws": (("amazon web services",), ()),
    "gcp": (("google cloud", "google cloud platform"), ()),
    "azure": ((), ()),
    "docker": ((), ()),
    "kubernetes": (("k8s",), ()),
    "terraform": ((), ()),
    "ansible": ((), ()),
    "helm": ((), ()),
    "jenkins": ((), ()),
    "github actions": ((), ()),
    "ci/cd": (("ci cd", "continuous integration", "continuous delivery", "continuous deployment"), ()),
    "linux": (("unix",), ()),
    "nginx": ((), ()),
    "prometheus": ((), ()),
    "grafana": ((), ()),
    "opentelemetry": (("otel",), ()),
    "serverless": (("lambda",), ()),
    "git": (("github", "gitlab"), ()),
    # ── data stores ───────────────────────────────────────────────────────
    "postgresql": (("postgres",), ()),
    "mysql": ((), ()),
    "mongodb": (("mongo",), ()),
    "redis": ((), ()),
    "cassandra": ((), ()),
    "dynamodb": ((), ()),
    "elasticsearch": (("opensearch",), ()),
    "snowflake": ((), ()),
    "bigquery": ((), ()),
    "redshift": ((), ()),
    "clickhouse": ((), ()),
    "sqlite": ((), ()),
    "neo4j": (("graph database",), ()),
    "faiss": ((), ()),
    "pgvector": ((), ()),
    "pinecone": ((), ()),
    "vector database": (("vector db", "vector store"), ()),
    # ── ML / AI concepts ──────────────────────────────────────────────────
    "machine learning": ((), ("ML",)),
    "deep learning": ((), ()),
    "nlp": (("natural language processing",), ()),
    "computer vision": ((), ("CV",)),
    "llm": (("llms", "large language model", "large language models"), ()),
    "generative ai": (("genai", "gen ai", "generative models"), ()),
    "rag": (("retrieval-augmented generation", "retrieval augmented generation"), ()),
    "fine-tuning": (("fine tuning", "finetuning"), ()),
    "rlhf": (("reinforcement learning from human feedback",), ()),
    "reinforcement learning": ((), ()),
    "recommendation systems": (("recommender systems", "recommendation system", "recommender"), ()),
    "ranking": (("learning to rank", "search ranking"), ()),
    "embeddings": (("embedding",), ()),
    "agents": (("agentic", "ai agents", "multi-agent"), ()),
    "mlops": (("ml ops",), ()),
    "feature engineering": ((), ()),
    "a/b testing": (("ab testing", "a/b test", "experimentation"), ()),
    "statistics": (("statistical",), ()),
    "time series": (("time-series",), ()),
    "data science": ((), ()),
    "data engineering": (("data pipelines", "data pipeline", "etl"), ()),
    "prompt engineering": ((), ()),
    "evaluation": (("evals",), ()),
    # ── engineering concepts ──────────────────────────────────────────────
    "distributed systems": (("distributed computing",), ()),
    "microservices": (("microservice",), ()),
    "system design": (("systems design",), ()),
    "data structures": (("algorithms",), ()),
    "api": (("apis", "api design"), ()),
    "event-driven": (("event driven", "message queue", "message queues", "pub/sub"), ()),
    "concurrency": (("multithreading", "multi-threading", "parallel programming"), ()),
    "low latency": (("low-latency", "high performance"), ()),
    "scalability": (("scalable", "high availability", "large scale", "large-scale"), ()),
    "observability": (("monitoring", "logging"), ()),
    "testing": (("unit testing", "unit tests", "integration testing", "tdd", "test-driven"), ()),
    "security": (("cybersecurity", "application security", "red teaming", "red-teaming"), ()),
    "oauth": (("jwt",), ()),
    "agile": (("scrum",), ()),
    "code review": (("code reviews",), ()),
    "oop": (("object-oriented", "object oriented"), ()),
    "networking": (("tcp/ip",), ()),
    "databases": (("database", "rdbms"), ()),
    # ── domain: finance / quant / payments ────────────────────────────────
    "trading": (("quantitative", "quant", "market data", "algorithmic trading"), ()),
    "derivatives": (("options pricing", "fixed income"), ()),
    "payments": (("fintech", "payment systems"), ()),
    "fraud": (("fraud detection", "anti-money laundering"), ()),
    "risk": (("risk management",), ()),
    # ── mobile / front-end craft ──────────────────────────────────────────
    "ios": ((), ()),
    "android": ((), ()),
    "accessibility": (("a11y", "wcag"), ()),
    "ui/ux": (("ux", "user experience", "design systems"), ()),
}

# Canonical strings that are ordinary English words or single letters. The bare
# word is NOT matched; only the (more specific) aliases are.
_NO_BARE_CANON = {"go", "r", "rest", "express", "spring", "spark"}
# Real terms that are also names/words when lowercased. Matched only in their
# Capitalised form ("Swift", "Helm"), never mid-sentence lowercase.
_CAPITALISED_ONLY = {"swift", "helm", "ray", "julia", "dart"}

# Broad concepts that ordinary rewording introduces ("Designed APIs", "improved
# testing"). Useful for ranking JD keywords, but NOT evidence that a rewrite
# invented a skill, so the grounding check ignores them.
CONCEPT_TERMS = {
    "api", "testing", "security", "databases", "scalability", "observability", "agile",
    "networking", "system design", "data structures", "oop", "code review", "evaluation",
    "statistics", "ranking", "agents", "risk", "payments", "trading", "accessibility",
    "ui/ux", "concurrency", "low latency", "event-driven", "distributed systems",
    "microservices", "embeddings", "oauth", "data engineering", "data science",
    "derivatives", "fraud", "rest",
}

_REQ_HEADINGS = re.compile(
    r"(?im)^\s*(?:what you(?:'ll| will)? (?:need|bring|have)|requirements?|"
    r"(?:basic|minimum|required|key) qualifications?|qualifications?|must[- ]have|"
    r"you have|you are|about you|skills?(?: required)?|who you are)\b"
)
_PREF_HEADINGS = re.compile(
    r"(?im)^\s*(?:nice[- ]to[- ]have|preferred(?: qualifications?)?|bonus|"
    r"good to have|plus(?:es)?|desirable|extra credit)\b"
)


@dataclass(frozen=True)
class JDKeyword:
    term: str
    count: int
    first_pos: int
    in_requirements: bool
    score: float


@lru_cache(maxsize=1)
def _compiled() -> dict[str, re.Pattern[str]]:
    def lit(a: str) -> str:
        # Spaces in a phrase may be any whitespace run (JDs wrap lines).
        return re.escape(a).replace(r"\ ", r"[ \t\r\n]+")

    out: dict[str, re.Pattern[str]] = {}
    for canon, (ci_aliases, cs_aliases) in TERMS.items():
        parts: list[str] = []
        if canon in _CAPITALISED_ONLY:
            parts.append(lit(canon.capitalize()))
        else:
            names = list(ci_aliases) if canon in _NO_BARE_CANON else [canon, *ci_aliases]
            alts = [lit(a) + ("s?" if a[-1:].isalpha() else "") for a in names]
            if alts:
                parts.append(f"(?i:{'|'.join(alts)})")
        parts += [lit(a) for a in cs_aliases]
        if not parts:
            continue
        # Boundaries stop partial hits ("java" in "javascript", "c" in "c++");
        # "R&D" and a trailing sentence period are handled explicitly.
        out[canon] = re.compile(rf"(?<![\w.#+-])(?:{'|'.join(parts)})(?![\w#+&-])(?!\.\w)")
    return out


def _section_offsets(text: str) -> tuple[int | None, int | None]:
    req = _REQ_HEADINGS.search(text)
    pref = _PREF_HEADINGS.search(text)
    return (req.start() if req else None, pref.start() if pref else None)


def terms_in(text: str, specific_only: bool = False) -> set[str]:
    """Canonical vocabulary terms present anywhere in ``text`` (aliases fold in).

    ``specific_only`` drops broad concepts, leaving hard skills (languages,
    frameworks, tools, data stores).
    """
    if not text:
        return set()
    found = {canon for canon, pat in _compiled().items() if pat.search(text)}
    return found - CONCEPT_TERMS if specific_only else found


def extract_jd_keywords(jd_text: str, limit: int = 25) -> list[JDKeyword]:
    """Vocabulary terms found in the JD, ranked by how much the JD stresses them.

    Ranking: occurrences, +1.5 if a match sits under a requirements-style
    heading, -0.75 if every match sits under a nice-to-have heading, and a
    small earlier-is-better tiebreak. Fully deterministic.
    """
    if not jd_text:
        return []
    req_at, pref_at = _section_offsets(jd_text)
    found: list[JDKeyword] = []
    for canon, pat in _compiled().items():
        hits = [m.start() for m in pat.finditer(jd_text)]
        if not hits:
            continue
        in_req = req_at is not None and any(
            h >= req_at and (pref_at is None or pref_at < req_at or h < pref_at) for h in hits
        )
        only_pref = pref_at is not None and all(h >= pref_at for h in hits) and not in_req
        score = float(len(hits)) + (1.5 if in_req else 0.0) - (0.75 if only_pref else 0.0)
        score += max(0.0, 0.5 - hits[0] / max(len(jd_text), 1) * 0.5)
        found.append(JDKeyword(canon, len(hits), hits[0], in_req, round(score, 3)))
    found.sort(key=lambda k: (-k.score, k.first_pos, k.term))
    return found[:limit]


def missing_keywords(resume_text: str, jd_text: str, limit: int = 15) -> list[JDKeyword]:
    """JD keywords (ranked) that the resume does not mention at all."""
    have = terms_in(resume_text)
    return [k for k in extract_jd_keywords(jd_text, limit=60) if k.term not in have][:limit]


def term_counts(text: str) -> dict[str, int]:
    """How many times each vocabulary term occurs in ``text``."""
    if not text:
        return {}
    out = {}
    for canon, pat in _compiled().items():
        n = len(pat.findall(text))
        if n:
            out[canon] = n
    return out
