"""ATS Simulation Agent — Simulates resume parsing through 4 real ATS platforms."""

from __future__ import annotations

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent

logger = structlog.get_logger()

ATS_PLATFORMS: dict[str, dict] = {
    "workday": {
        "required_sections": ["Experience", "Education", "Skills"],
        "max_bullet_length": 200,
        "disallowed_chars": ["•", "→", "★"],
        "weight": 0.3,
    },
    "greenhouse": {
        "required_sections": ["Experience", "Skills"],
        "max_bullet_length": 250,
        "disallowed_chars": ["→", "★"],
        "weight": 0.25,
    },
    "lever": {
        "required_sections": ["Experience", "Education"],
        "max_bullet_length": 300,
        "disallowed_chars": [],
        "weight": 0.25,
    },
    "taleo": {
        "required_sections": ["Experience", "Education", "Skills", "Summary"],
        "max_bullet_length": 180,
        "disallowed_chars": ["•", "→", "★", "|"],
        "weight": 0.2,
    },
}


class ATSAgent(BaseAgent):
    """Simulates resume parsing through Workday, Greenhouse, Lever, and Taleo.

    Each platform has different section requirements, bullet length limits,
    and disallowed characters. The agent produces per-platform parse accuracy
    scores, keyword match rates, and actionable warnings.
    """

    QUALITY_THRESHOLD = 0.0  # ATS agent doesn't block pipeline
    MAX_RETRIES = 1

    def __init__(self) -> None:
        pass  # No LLM or retriever needed — rule-based simulation

    async def execute(self, input: AgentInput) -> AgentOutput:
        resume = input.content
        jd_keywords = input.metadata.get("jd_keywords", [])

        reports: dict[str, dict] = {}
        weighted_score = 0.0

        for platform, rules in ATS_PLATFORMS.items():
            report = self._simulate_parse(resume, jd_keywords, rules, platform)
            reports[platform] = report
            weighted_score += report["parse_accuracy"] * rules["weight"]

        # Deduplicate all warnings across platforms
        all_warnings: list[str] = []
        seen: set[str] = set()
        for r in reports.values():
            for w in r["warnings"]:
                if w not in seen:
                    all_warnings.append(w)
                    seen.add(w)

        logger.info(
            "ats_agent.complete",
            weighted_score=round(weighted_score, 3),
            warning_count=len(all_warnings),
        )

        return AgentOutput(
            content=resume,
            quality_score=weighted_score,
            metadata={
                "ats_reports": reports,
                "weighted_ats_score": round(weighted_score, 3),
                "all_warnings": all_warnings,
                "platforms_checked": list(ATS_PLATFORMS.keys()),
            },
        )

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content for ATS simulation")

    def validate_output(self, output: AgentOutput) -> None:
        pass  # ATS agent never blocks pipeline — it's advisory

    # ------------------------------------------------------------------
    # Simulation logic
    # ------------------------------------------------------------------

    def _simulate_parse(
        self,
        resume: str,
        keywords: list[str],
        rules: dict,
        platform: str,
    ) -> dict:
        warnings: list[str] = []
        detected = self._detect_sections(resume)

        # Section coverage check
        missing = [s for s in rules["required_sections"] if s not in detected]
        if missing:
            warnings.append(
                f"Missing required sections for {platform}: {', '.join(missing)}"
            )

        # Disallowed character check
        for char in rules.get("disallowed_chars", []):
            if char in resume:
                warnings.append(
                    f"[{platform}] Disallowed character '{char}' detected — may cause parse failure"
                )

        # Bullet length check
        long_bullets = [
            line for line in resume.split("\n")
            if len(line.strip()) > rules["max_bullet_length"]
            and line.strip().startswith(("-", "*", "•"))
        ]
        if long_bullets:
            warnings.append(
                f"[{platform}] {len(long_bullets)} bullet(s) exceed {rules['max_bullet_length']}-char limit"
            )

        # Keyword match rate
        matched = [k for k in keywords if k.lower() in resume.lower()]
        keyword_rate = round(len(matched) / max(len(keywords), 1), 3)

        # Parse accuracy: base 1.0 - penalty per warning
        parse_accuracy = max(round(1.0 - len(warnings) * 0.12, 2), 0.0)

        return {
            "platform":          platform,
            "parse_accuracy":    parse_accuracy,
            "keyword_match_rate": keyword_rate,
            "sections_detected": detected,
            "warnings":          warnings,
            "matched_keywords":  matched,
        }

    def _detect_sections(self, resume: str) -> list[str]:
        section_keywords: dict[str, list[str]] = {
            "Experience":      ["experience", "work history", "employment"],
            "Education":       ["education", "academic"],
            "Skills":          ["skills", "technical skills", "competencies"],
            "Summary":         ["summary", "objective", "profile"],
            "Certifications":  ["certifications", "certificates"],
            "Projects":        ["projects", "portfolio"],
        }
        lower = resume.lower()
        return [
            section
            for section, kws in section_keywords.items()
            if any(k in lower for k in kws)
        ]
