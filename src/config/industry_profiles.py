"""Industry-specific optimization profiles.

Each profile controls scoring weights, tone instructions, FAISS index path,
and format rules. TailoringAgent classifies the JD into a profile via GPT
(zero-shot), then applies the matching profile's weights and tone.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FormatRules:
    max_pages: int = 1
    prefer_bullets: bool = True


@dataclass
class IndustryProfile:
    name: str
    display_name: str
    scoring_weights: dict[str, float]
    faiss_index: str
    tone: str
    format_rules: FormatRules
    jd_classifier_keywords: list[str] = field(default_factory=list)


PROFILES: dict[str, IndustryProfile] = {
    "tech_swe": IndustryProfile(
        name="tech_swe",
        display_name="Software Engineering",
        scoring_weights={"impact": 0.4, "alignment": 0.3, "coverage": 0.2, "ats": 0.1},
        faiss_index="indices/tech_swe.index",
        tone="impact-driven, concise, metric-heavy",
        format_rules=FormatRules(max_pages=1, prefer_bullets=True),
        jd_classifier_keywords=[
            "software engineer", "swe", "backend", "frontend", "fullstack",
            "developer", "programming", "code", "typescript", "python", "java",
        ],
    ),
    "finance": IndustryProfile(
        name="finance",
        display_name="Finance & Banking",
        scoring_weights={"impact": 0.5, "alignment": 0.25, "coverage": 0.15, "ats": 0.1},
        faiss_index="indices/finance.index",
        tone="formal, quantified, compliance-aware",
        format_rules=FormatRules(max_pages=2, prefer_bullets=True),
        jd_classifier_keywords=[
            "finance", "banking", "investment", "equity", "portfolio", "trading",
            "analyst", "hedge fund", "asset management", "fintech", "quantitative",
        ],
    ),
    "academia": IndustryProfile(
        name="academia",
        display_name="Academic / Research",
        scoring_weights={"impact": 0.2, "alignment": 0.3, "coverage": 0.4, "ats": 0.1},
        faiss_index="indices/academia.index",
        tone="formal, publication-aware, comprehensive",
        format_rules=FormatRules(max_pages=5, prefer_bullets=False),
        jd_classifier_keywords=[
            "research", "professor", "phd", "postdoc", "academic", "faculty",
            "publication", "journal", "university", "lab", "thesis",
        ],
    ),
    "consulting": IndustryProfile(
        name="consulting",
        display_name="Management Consulting",
        scoring_weights={"impact": 0.45, "alignment": 0.3, "coverage": 0.15, "ats": 0.1},
        faiss_index="indices/consulting.index",
        tone="concise, structured, client-impact language",
        format_rules=FormatRules(max_pages=1, prefer_bullets=True),
        jd_classifier_keywords=[
            "consulting", "consultant", "mckinsey", "bcg", "bain", "strategy",
            "client", "engagement", "advisory", "management consulting",
        ],
    ),
    "product": IndustryProfile(
        name="product",
        display_name="Product Management",
        scoring_weights={"impact": 0.4, "alignment": 0.35, "coverage": 0.15, "ats": 0.1},
        faiss_index="indices/product.index",
        tone="user-outcome focused, cross-functional, roadmap-aware",
        format_rules=FormatRules(max_pages=1, prefer_bullets=True),
        jd_classifier_keywords=[
            "product manager", "product management", "pm", "roadmap", "stakeholder",
            "agile", "scrum", "user story", "go-to-market", "okr",
        ],
    ),
    "data_science": IndustryProfile(
        name="data_science",
        display_name="Data Science / ML",
        scoring_weights={"impact": 0.35, "alignment": 0.3, "coverage": 0.25, "ats": 0.1},
        faiss_index="indices/data_science.index",
        tone="analytical, experiment-driven, model-performance focused",
        format_rules=FormatRules(max_pages=2, prefer_bullets=True),
        jd_classifier_keywords=[
            "data scientist", "machine learning", "ml", "ai", "deep learning",
            "nlp", "pytorch", "tensorflow", "sklearn", "modeling", "analytics",
        ],
    ),
}

DEFAULT_PROFILE = PROFILES["tech_swe"]


def classify_profile(job_description: str) -> IndustryProfile:
    """Classify a JD into a profile using keyword matching.

    Falls back to tech_swe if no clear match. TailoringAgent can override this
    with a GPT zero-shot call for higher accuracy.
    """
    lower_jd = job_description.lower()
    best_profile = DEFAULT_PROFILE
    best_score = 0

    for profile in PROFILES.values():
        score = sum(1 for kw in profile.jd_classifier_keywords if kw in lower_jd)
        if score > best_score:
            best_score = score
            best_profile = profile

    return best_profile
