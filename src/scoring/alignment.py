"""Alignment Scorer — Measures semantic alignment between resume and JD."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import structlog

from src.rag.embedder import Embedder

logger = structlog.get_logger()


@dataclass
class AlignmentResult:
    """Result of alignment scoring."""

    overall_score: float
    section_scores: dict[str, float]
    top_alignments: list[tuple[str, str, float]]  # (resume_seg, jd_seg, score)
    gaps: list[str]  # JD requirements with low alignment


class AlignmentScorer:
    """Computes semantic alignment between resume sections and JD requirements."""

    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder

    def score(
        self,
        resume_sections: dict[str, str],
        jd_requirements: list[str],
    ) -> AlignmentResult:
        """Score alignment between resume and job description.

        Args:
            resume_sections: Dict of section_name -> content.
            jd_requirements: List of JD requirements/responsibilities.

        Returns:
            AlignmentResult with scores and gaps.
        """
        if not resume_sections or not jd_requirements:
            return AlignmentResult(
                overall_score=0.0, section_scores={}, top_alignments=[], gaps=jd_requirements
            )

        # Encode all segments
        resume_texts = []
        resume_labels = []
        for section, content in resume_sections.items():
            for line in content.split("\n"):
                if line.strip():
                    resume_texts.append(line.strip())
                    resume_labels.append(section)

        resume_vecs = self.embedder.encode(resume_texts)
        jd_vecs = self.embedder.encode(jd_requirements)

        # Compute similarity matrix
        sim_matrix = np.dot(jd_vecs, resume_vecs.T)  # (jd, resume)

        # Overall: average of best match per JD requirement
        best_per_jd = sim_matrix.max(axis=1)
        overall = float(np.mean(best_per_jd))

        # Section scores: average alignment per section
        section_scores: dict[str, float] = {}
        for section in set(resume_labels):
            idxs = [i for i, l in enumerate(resume_labels) if l == section]
            if idxs:
                section_sim = sim_matrix[:, idxs].max(axis=1)
                section_scores[section] = float(np.mean(section_sim))

        # Top alignments
        top_alignments = []
        for j in range(len(jd_requirements)):
            best_i = int(sim_matrix[j].argmax())
            top_alignments.append((
                resume_texts[best_i],
                jd_requirements[j],
                float(sim_matrix[j, best_i]),
            ))
        top_alignments.sort(key=lambda x: x[2], reverse=True)

        # Gaps: JD requirements with low best-match score
        gaps = [
            jd_requirements[j]
            for j in range(len(jd_requirements))
            if best_per_jd[j] < 0.5
        ]

        logger.info(
            "alignment.scored",
            overall=round(overall, 3),
            sections=len(section_scores),
            gaps=len(gaps),
        )
        return AlignmentResult(
            overall_score=overall,
            section_scores=section_scores,
            top_alignments=top_alignments[:10],
            gaps=gaps,
        )
