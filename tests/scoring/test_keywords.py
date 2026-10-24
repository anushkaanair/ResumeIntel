"""JD skill extraction — must not mistake ordinary words for skills."""

from src.scoring.keywords import extract_jd_keywords, missing_keywords, terms_in


def _terms(jd: str) -> list[str]:
    return [k.term for k in extract_jd_keywords(jd)]


def test_aliases_map_to_one_canonical_term() -> None:
    assert "kubernetes" in terms_in("Ran workloads on k8s")


def test_ordinary_words_are_not_skills() -> None:
    jd = "Internship Spring 2027. Please express interest. You will go beyond. R&D team. https://go.dev/careers"
    t = {x.lower() for x in _terms(jd)}
    assert not ({"go", "r", "spring", "express"} & t)


def test_ambiguous_names_need_an_unambiguous_form() -> None:
    assert "go" in terms_in("Backend in Golang and Python")
    assert "go" not in terms_in("We go beyond. Go team!")


def test_requirements_outweigh_nice_to_have() -> None:
    jd = "Requirements:\n- Python\n\nNice to have:\n- Terraform\n"
    ranked = _terms(jd)
    assert ranked.index("python") < ranked.index("terraform")


def test_missing_keywords_lists_only_what_the_resume_lacks() -> None:
    miss = [k.term for k in missing_keywords("Python, Docker", "Python, Docker, Kubernetes, Terraform")]
    assert "kubernetes" in miss and "python" not in miss
