"""Fetch real, public job descriptions for evaluation.

Uses the public JSON endpoints that Ashby, Lever and Greenhouse expose for
their own job boards (no login, no scraping of rendered pages). Output goes to
``data/eval/jds/`` which is git-ignored.

    uv run python -m evals.fetch_jds
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("data/eval/jds")

# slug -> (provider, board/org, posting id)
POSTINGS: dict[str, tuple[str, str, str]] = {
    "cohere-ml-intern": ("ashby", "cohere", "36d1f52f-8270-4652-adf5-5303a0ff341b"),
    "cohere-swe-intern": ("ashby", "cohere", "8c035d3d-081d-4c8a-914a-72f4efaad254"),
    "perplexity-mle-intern": ("ashby", "perplexity", "b9e1ff15-d52a-46d5-abf0-26460f2a116c"),
    "sierra-swe-agent": ("ashby", "sierra", "79953d72-60d4-43e0-8c8c-6eccda422dce"),
    "snowflake-swe-intern": ("ashby", "snowflake", "ab028e3c-c1cf-4455-8915-8e4e6b0cc9e8"),
    "partly-ml-research": ("ashby", "partly.com", "49cc37df-a604-4c7e-910b-e4e9bcf35e46"),
    "palantir-swe-newgrad": ("lever", "palantir", "2458ba08-de79-4e8f-b553-060f9568727e"),
    "ifm-ai-engineer": ("lever", "ifm-us", "08930bb0-7ea7-4ace-a453-2e4cff4a11dc"),
    "datadog-applied-science": ("greenhouse", "datadog", "8181440"),
    "datadog-swe-intern": ("greenhouse", "datadog", "8114186"),
    "rubrik-swe-intern": ("greenhouse", "rubrik", "8166523"),
    "scale-swe-newgrad": ("greenhouse", "scaleai", "4730862005"),
}

UA = {"User-Agent": "ResumeIntel-eval/0.1 (personal evaluation; public postings only)"}


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def html_to_text(raw: str) -> str:
    s = html.unescape(raw or "")
    s = re.sub(r"(?i)<\s*li[^>]*>", "\n- ", s)
    s = re.sub(r"(?i)<\s*/\s*(p|div|h[1-6]|ul|ol|tr)\s*>", "\n", s)
    s = re.sub(r"(?i)<\s*br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t ]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()


def fetch(provider: str, org: str, pid: str) -> tuple[str, str]:
    if provider == "ashby":
        data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{org}")
        job = next(j for j in data["jobs"] if j["id"] == pid)
        return job["title"], job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml", ""))
    if provider == "lever":
        job = _get(f"https://api.lever.co/v0/postings/{org}/{pid}")
        parts = [job.get("descriptionPlain", "")]
        for lst in job.get("lists", []):
            parts.append(f"{lst.get('text', '')}\n{html_to_text(lst.get('content', ''))}")
        parts.append(job.get("additionalPlain", ""))
        return job["text"], "\n\n".join(p for p in parts if p)
    if provider == "greenhouse":
        job = _get(f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs/{pid}")
        return job["title"], html_to_text(job.get("content", ""))
    raise ValueError(provider)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for slug, (provider, org, pid) in POSTINGS.items():
        try:
            title, text = fetch(provider, org, pid)
        except (urllib.error.URLError, StopIteration, KeyError, TimeoutError) as e:
            print(f"SKIP {slug}: {type(e).__name__}: {e}")
            continue
        if len(text) < 400:
            print(f"SKIP {slug}: description too short ({len(text)} chars)")
            continue
        (OUT / f"{slug}.txt").write_text(f"{title}\n\n{text}\n", encoding="utf-8")
        print(f"OK   {slug}: {title!r} ({len(text)} chars)")
        ok += 1
    print(f"\n{ok}/{len(POSTINGS)} job descriptions saved to {OUT}/")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
