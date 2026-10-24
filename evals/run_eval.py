"""Run the real pipeline on real job descriptions and audit what comes out.

    LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:3b \\
      uv run python -m evals.run_eval \\
        --resume ~/Desktop/Cld/Anushka_Nair_Resume_Nike.pdf \\
        --truth  ~/Desktop/Cld/job_search/Master_Resume.md \\
        --out data/eval/run-baseline

Writes one JSON per JD plus ``summary.md``. Everything under ``data/`` is
git-ignored because the outputs contain personal details.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
import traceback
from pathlib import Path

from src.parsers.resume_parser import ResumeParser
from src.scoring.grounding import check


def load_resume(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        with path.open("rb") as f:
            return ResumeParser().parse(f, path.name)
    return path.read_text(encoding="utf-8")


def _root_cause(exc: BaseException) -> str:
    ctx = getattr(exc, "context", None)
    if isinstance(ctx, dict) and ctx.get("last_error"):
        return str(ctx["last_error"])
    return ""


async def run_one(slug: str, jd: str, resume: str, truth: str, skip_interview: bool, timeout: int) -> dict:
    from src.llm.client import LLMClient
    from src.pipeline import Pipeline

    row: dict = {"slug": slug, "status": "error"}
    t0 = time.time()
    try:
        pipeline = Pipeline(llm_client=LLMClient(), user_id=f"eval_{slug}")
        result = await asyncio.wait_for(
            pipeline.run(resume, jd, skip_interview=skip_interview), timeout=timeout
        )
        row["status"] = "ok"
        tailoring = result["agents"].get("tailoring", {})
        row["gate_aborted"] = bool(tailoring.get("metadata", {}).get("alignment_gate_aborted"))
        row["metrics"] = result.get("metrics", {})
        row["unresolvable_bullets"] = len(result.get("unresolvable_bullets") or [])
        out = result.get("optimized_content", "")
        row["changed_vs_original"] = out.strip() != resume.strip()
        row["fabrication"] = check(out, [resume, truth], jd).as_dict()
        row["optimized_content"] = out
        row["agent_scores"] = {k: v.get("quality_score") for k, v in result["agents"].items()}
    except Exception as e:  # noqa: BLE001 — we want every failure recorded, not raised
        row["error_type"] = type(e).__name__
        row["error"] = str(e)[:400]
        row["root_cause"] = _root_cause(e)[:400]
        row["traceback_tail"] = "".join(traceback.format_exception(e)[-3:])[-900:]
    row["elapsed_s"] = round(time.time() - t0, 1)
    return row


def write_summary(out: Path, rows: list[dict]) -> None:
    ok = [r for r in rows if r["status"] == "ok"]
    lines = [f"# Eval summary — {len(rows)} job descriptions\n"]
    lines.append(f"- completed without error: **{len(ok)}/{len(rows)}**")
    if ok:
        lines.append(f"- alignment gate aborted tailoring: {sum(r['gate_aborted'] for r in ok)}/{len(ok)}")
        lines.append(f"- output differs from the original resume: {sum(r['changed_vs_original'] for r in ok)}/{len(ok)}")
        flagged = [r for r in ok if r["fabrication"]["flagged"]]
        lines.append(f"- **runs flagged for possible fabrication: {len(flagged)}/{len(ok)}**")
        lines.append(f"  - with novel numbers: {sum(bool(r['fabrication']['novel_numbers']) for r in ok)}")
        lines.append(f"  - with JD skills injected that the resume never had: {sum(bool(r['fabrication']['injected_jd_terms']) for r in ok)}")
        lines.append(f"- median runtime: {statistics.median(r['elapsed_s'] for r in ok):.0f}s")
    errs: dict[str, int] = {}
    for r in rows:
        if r["status"] != "ok":
            key = f"{r.get('error_type')}: {(r.get('root_cause') or r.get('error') or '')[:110]}"
            errs[key] = errs.get(key, 0) + 1
    if errs:
        lines.append("\n## Failures\n")
        for k, n in sorted(errs.items(), key=lambda kv: -kv[1]):
            lines.append(f"- ×{n}  `{k}`")
    lines.append("\n## Per job\n")
    lines.append("| JD | status | s | align | ATS | kw cov | novel #s | injected JD skills |")
    lines.append("|---|---|--:|--:|--:|--:|---|---|")
    for r in rows:
        if r["status"] == "ok":
            m, f = r["metrics"], r["fabrication"]
            lines.append(
                f"| {r['slug']} | ok{' (gate)' if r['gate_aborted'] else ''} | {r['elapsed_s']:.0f} | "
                f"{m.get('alignment')} | {m.get('atsPassRate')} | {m.get('keywordCoverage')} | "
                f"{', '.join(f['novel_numbers'][:6]) or '-'} | {', '.join(f['injected_jd_terms'][:8]) or '-'} |"
            )
        else:
            lines.append(f"| {r['slug']} | **{r.get('error_type')}** | {r['elapsed_s']:.0f} | - | - | - | - | - |")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main_async(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    resume = load_resume(Path(args.resume).expanduser())
    truth = Path(args.truth).expanduser().read_text(encoding="utf-8")
    jds = sorted(Path(args.jds).glob("*.txt"))
    if args.only:
        wanted = set(args.only.split(","))
        jds = [p for p in jds if p.stem in wanted]
    if args.limit:
        jds = jds[: args.limit]
    print(f"resume: {len(resume)} chars | truth: {len(truth)} chars | {len(jds)} JDs", flush=True)

    rows: list[dict] = []
    for p in jds:
        row = await run_one(p.stem, p.read_text(encoding="utf-8"), resume, truth, args.skip_interview, args.timeout)
        rows.append(row)
        (out / f"{p.stem}.json").write_text(json.dumps(row, indent=2, default=str), encoding="utf-8")
        write_summary(out, rows)
        tag = row["status"] if row["status"] == "ok" else f"{row.get('error_type')}"
        print(f"[{len(rows)}/{len(jds)}] {p.stem}: {tag} in {row['elapsed_s']}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", required=True)
    ap.add_argument("--truth", required=True, help="canonical source-of-truth resume (markdown/text)")
    ap.add_argument("--jds", default="data/eval/jds")
    ap.add_argument("--out", default="data/eval/run")
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-interview", action="store_true", default=True)
    ap.add_argument("--timeout", type=int, default=1500, help="seconds per JD")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
