"""Fabrication detection: the guarantee the whole product rests on."""

from src.scoring.grounding import check, numbers_in

SOURCE = "Built a REST API serving 10K requests/day with 99.9% uptime. Used Python and FastAPI. Cut deploy time by 60%."
JD = "We need Python, FastAPI, Kubernetes and Terraform experience."


def test_honest_rewrite_passes() -> None:
    out = "Built a Python/FastAPI REST API serving 10K requests/day at 99.9% uptime"
    assert not check(out, [SOURCE], JD).flagged


def test_invented_number_is_flagged() -> None:
    r = check("Cut deploy time by 75%", [SOURCE], JD)
    assert r.flagged and "75" in r.novel_numbers


def test_invented_multiplier_is_flagged() -> None:
    assert check("Improved throughput 5x", [SOURCE], JD).flagged


def test_jd_skill_the_resume_never_had_is_flagged() -> None:
    r = check("Deployed services with Kubernetes", [SOURCE], JD)
    assert r.flagged and "kubernetes" in [t.lower() for t in r.injected_jd_terms]


def test_jd_skill_already_in_resume_is_fine() -> None:
    assert not check("Built APIs in FastAPI", [SOURCE], JD).flagged


def test_years_and_list_numbers_are_ignored() -> None:
    assert numbers_in("2024 - 2026\n1. First item\n2) Second") == set()


def test_any_source_text_counts_as_truth() -> None:
    truth = "Also managed 12 engineers."
    assert not check("Managed 12 engineers", [SOURCE, truth], JD).flagged
