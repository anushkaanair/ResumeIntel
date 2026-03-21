"""Job Description Parser — Extracts structured info from job descriptions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

from src.exceptions import ParsingError

logger = structlog.get_logger()


@dataclass
class ParsedJD:
    """Structured representation of a job description."""

    title: str = ""
    company: str = ""
    raw_text: str = ""
    requirements: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    qualifications: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


class JDParser:
    """Parses job description text into structured components."""

    SECTION_PATTERNS = {
        "requirements": r"(?i)(requirements?|what you.?ll need|must have|required)",
        "responsibilities": r"(?i)(responsibilities?|what you.?ll do|role|duties)",
        "qualifications": r"(?i)(qualifications?|preferred|nice to have|bonus)",
        "skills": r"(?i)(skills?|technical skills?|tech stack|technologies)",
    }

    def parse(self, text: str) -> ParsedJD:
        """Parse job description text into structured format."""
        if not text or len(text.strip()) < 20:
            raise ParsingError("Job description too short (minimum 20 characters)")

        logger.info("jd_parser.parsing", chars=len(text))

        parsed = ParsedJD(raw_text=text.strip())
        parsed.title = self._extract_title(text)
        parsed.requirements = self._extract_section(text, "requirements")
        parsed.responsibilities = self._extract_section(text, "responsibilities")
        parsed.qualifications = self._extract_section(text, "qualifications")
        parsed.skills = self._extract_skills(text)
        parsed.keywords = self._extract_keywords(text)

        logger.info(
            "jd_parser.parsed",
            title=parsed.title,
            requirements=len(parsed.requirements),
            skills=len(parsed.skills),
            keywords=len(parsed.keywords),
        )
        return parsed

    def _extract_title(self, text: str) -> str:
        """Extract job title from first non-empty line."""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) < 100:
                return stripped
        return ""

    def _extract_section(self, text: str, section_type: str) -> list[str]:
        """Extract bullet points from a named section."""
        pattern = self.SECTION_PATTERNS.get(section_type)
        if not pattern:
            return []

        lines = text.split("\n")
        in_section = False
        items: list[str] = []

        for line in lines:
            stripped = line.strip()
            if re.match(pattern, stripped):
                in_section = True
                continue
            if in_section:
                # End of section: hit another header or empty line after content
                if re.match(r"(?i)^(requirements|responsibilities|qualifications|skills|about|benefits)", stripped):
                    break
                if stripped.startswith(("-", "*", "•", "–")):
                    items.append(re.sub(r"^[-*•–]\s*", "", stripped))
                elif stripped and len(items) == 0:
                    items.append(stripped)

        return items

    def _extract_skills(self, text: str) -> list[str]:
        """Extract technical skills and tools mentioned."""
        # Common tech patterns
        tech_pattern = r"\b(Python|Java|JavaScript|TypeScript|React|Node\.?js|AWS|Azure|GCP|Docker|Kubernetes|SQL|PostgreSQL|MongoDB|Redis|FastAPI|Django|Flask|Git|CI/CD|REST|GraphQL|Machine Learning|NLP|TensorFlow|PyTorch)\b"
        found = re.findall(tech_pattern, text, re.IGNORECASE)
        return list(set(found))

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract important keywords from the JD."""
        # Remove common stop words and extract meaningful terms
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "have", "been",
            "will", "are", "was", "were", "has", "had", "not", "but", "can",
            "our", "your", "their", "about", "into", "than", "other", "its",
            "you", "who", "what", "how", "why", "all", "each", "every",
            "more", "most", "some", "such", "only", "own", "same", "also",
        }

        from collections import Counter
        word_counts = Counter(w for w in words if w not in stop_words)
        return [word for word, _ in word_counts.most_common(30)]
