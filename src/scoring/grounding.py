"""Grounding: claims in a rewritten resume that the source material never made.

Used in two places: as a **gate** inside the pipeline (a rewrite that adds
claims is rejected and retried with the offending items named), and by the
offline evaluation in ``evals/``.

This does not prove an output is honest — it catches the two failure modes that
matter most for a resume tool and are mechanically detectable:

* **Novel numbers** — a metric (``40%``, ``10,000+``, ``3x``) in the output that
  appears nowhere in the candidate's source material.
* **Injected skills** — a technology/skill term in the output that the source
  never mentions. When that term is also in the target JD, it is the signature
  of keyword stuffing: the tool wrote the JD's vocabulary into the resume.

Everything it flags still needs a human read; it only decides where to look.

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.scoring.keywords import terms_in

_NUM = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\s?(?:%|x\b|×|k\b|K\b|M\b|\+))?(?![\w])"
)
_YEAR = re.compile(r"^(19|20)\d{2}$")
_LIST_NUMERAL = re.compile(r"(?m)^\s*\d{1,2}[.)]\s")


def numbers_in(text: str) -> set[str]:
    """Normalised metric-like numbers.

    Excluded on purpose: calendar years, numbered-list markers ("1. "), and bare
    single digits with no unit ("5 users", "Python 3") — those are everywhere in
    honest text. A single digit WITH a unit ("5x", "7%") still counts: that is
    exactly what an invented metric looks like.
    """
    out: set[str] = set()
    text = _LIST_NUMERAL.sub("", text or "")
    for m in _NUM.finditer(text):
        tok = m.group(1).replace(",", "")
        if tok.endswith(".0"):
            tok = tok[:-2]
        if _YEAR.match(tok):
            continue
        if len(tok) == 1 and not m.group(2):
            continue
        out.add(tok)
    return out


@dataclass
class FabricationReport:
    novel_numbers: list[str] = field(default_factory=list)
    injected_terms: list[str] = field(default_factory=list)
    injected_jd_terms: list[str] = field(default_factory=list)
    bullets_with_novel_numbers: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return bool(self.novel_numbers or self.injected_jd_terms)

    def as_dict(self) -> dict:
        return {
            "flagged": self.flagged,
            "novel_numbers": self.novel_numbers,
            "injected_terms": self.injected_terms,
            "injected_jd_terms": self.injected_jd_terms,
            "bullets_with_novel_numbers": self.bullets_with_novel_numbers[:8],
        }


def check(
    output: str,
    source_texts: list[str],
    jd: str,
    number_sources: list[str] | None = None,
) -> FabricationReport:
    """Compare ``output`` with the resume.

    ``number_sources`` narrows where a *number* may come from (default: ``source_texts``).
    Rewriting a single bullet passes the bullet itself, so a figure that belongs to one
    project cannot be attached to another.
    """
    source = "\n".join(source_texts)
    src_nums = numbers_in("\n".join(number_sources) if number_sources is not None else source)
    src_terms = terms_in(source, specific_only=True)

    novel_nums = sorted(numbers_in(output) - src_nums, key=lambda x: (len(x), x))
    injected = sorted(terms_in(output, specific_only=True) - src_terms)
    injected_jd = sorted(set(injected) & terms_in(jd, specific_only=True))

    bad_bullets = [
        line.strip()
        for line in output.splitlines()
        if line.strip().startswith(("-", "*", "•")) and (numbers_in(line) - src_nums)
    ]
    return FabricationReport(novel_nums, injected, injected_jd, bad_bullets)


def retry_feedback(report: FabricationReport) -> str:
    """Instruction text naming exactly what a rewrite must remove."""
    parts = []
    if report.novel_numbers:
        parts.append("numbers/metrics that are NOT in the source: " + ", ".join(report.novel_numbers[:10]))
    if report.injected_jd_terms:
        parts.append(
            "skills copied from the job description that the candidate never listed: "
            + ", ".join(report.injected_jd_terms[:10])
        )
    return (
        "YOUR PREVIOUS ATTEMPT WAS REJECTED. It added " + "; and ".join(parts) + ". "
        "Rewrite again using ONLY facts present in the source resume; delete every item above."
        if parts else ""
    )
