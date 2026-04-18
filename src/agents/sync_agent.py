"""Sync Agent — Fetches GitHub/LinkedIn deltas and scores them against the target JD."""

from __future__ import annotations

import structlog
import httpx
from sklearn.metrics.pairwise import cosine_similarity

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.rag.embedder import Embedder

logger = structlog.get_logger()

RELEVANCE_THRESHOLD = 0.5

SECTION_CLASSIFIER: dict[str, str] = {
    "repository": "Projects",
    "role":        "Experience",
    "skill":       "Skills",
    "certification": "Certifications",
    "project":     "Projects",
}


class SyncAgent(BaseAgent):
    """Fetches platform deltas (GitHub repos / LinkedIn roles) and scores each item
    against the target JD embedding. Items above RELEVANCE_THRESHOLD are returned
    as structured SyncDelta candidates for the user to apply to their canvas.
    """

    QUALITY_THRESHOLD = 0.5
    MAX_RETRIES = 1

    def __init__(self) -> None:
        self.embedder = Embedder()

    async def execute(self, input: AgentInput) -> AgentOutput:
        platform = input.metadata.get("platform", "github")
        access_token = input.metadata.get("access_token", "")
        sync_cursor = input.metadata.get("sync_cursor")
        jd_embedding = input.metadata.get("jd_embedding")

        if jd_embedding is None:
            # Embed the JD on the fly if not pre-computed
            jd_embedding = self.embedder.encode_single(input.job_description)

        if platform == "github":
            raw_items = await self._fetch_github_delta(access_token, sync_cursor)
        elif platform == "linkedin":
            raw_items = await self._fetch_linkedin_delta(access_token, sync_cursor)
        else:
            raise ValueError(f"Unknown platform: {platform}")

        deltas: list[dict] = []
        for item in raw_items:
            text = item.get("description") or item.get("title", "")
            embedding = self.embedder.encode_single(text)
            score = float(
                cosine_similarity(
                    embedding.reshape(1, -1),
                    jd_embedding.reshape(1, -1),
                )[0][0]
            )
            if score >= RELEVANCE_THRESHOLD:
                deltas.append({
                    "platform":          platform,
                    "item_type":         item["type"],
                    "title":             item["title"],
                    "description":       item.get("description", ""),
                    "relevance_score":   round(score, 4),
                    "suggested_section": SECTION_CLASSIFIER.get(item["type"], "Experience"),
                    "raw_data":          item,
                })

        deltas.sort(key=lambda x: x["relevance_score"], reverse=True)

        new_cursor = raw_items[-1].get("cursor") if raw_items else sync_cursor

        logger.info(
            "sync_agent.complete",
            platform=platform,
            items_fetched=len(raw_items),
            items_above_threshold=len(deltas),
        )

        return AgentOutput(
            content="",
            quality_score=1.0 if deltas else 0.5,
            metadata={
                "deltas": deltas,
                "new_cursor": new_cursor,
                "platform": platform,
            },
        )

    def validate_input(self, input: AgentInput) -> None:
        if not input.metadata.get("access_token"):
            raise ValueError("access_token required in metadata")
        if not input.metadata.get("platform"):
            raise ValueError("platform required in metadata")

    def validate_output(self, output: AgentOutput) -> None:
        pass  # Any result (even empty deltas) is valid

    # ------------------------------------------------------------------
    # Platform fetch helpers
    # ------------------------------------------------------------------

    async def _fetch_github_delta(self, token: str, cursor: str | None) -> list[dict]:
        """Fetch repos updated since last cursor (last repo ID)."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.github.com/user/repos",
                    headers=headers,
                    params={"sort": "updated", "per_page": 30},
                )
                resp.raise_for_status()
                repos = resp.json()
        except Exception as exc:
            logger.error("sync_agent.github_fetch_failed", error=str(exc))
            return []

        items: list[dict] = []
        for repo in repos:
            if cursor and str(repo.get("id", 0)) <= cursor:
                continue
            items.append({
                "type":        "repository",
                "title":       repo["name"],
                "description": repo.get("description") or repo["name"],
                "cursor":      str(repo["id"]),
                "url":         repo.get("html_url", ""),
                "stars":       repo.get("stargazers_count", 0),
                "language":    repo.get("language", ""),
            })
        return items

    async def _fetch_linkedin_delta(self, token: str, cursor: str | None) -> list[dict]:
        """Fetch LinkedIn profile positions and skills.

        NOTE: Requires OAuth 2.0 with r_liteprofile scope.
        The /sync/connect endpoint must exchange the OAuth code before this is called.
        """
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.linkedin.com/v2/me",
                    headers=headers,
                    params={"projection": "(id,localizedFirstName,localizedLastName,positions,skills)"},
                )
                resp.raise_for_status()
                profile = resp.json()
        except Exception as exc:
            logger.error("sync_agent.linkedin_fetch_failed", error=str(exc))
            return []

        items: list[dict] = []
        for pos in profile.get("positions", {}).get("values", []):
            items.append({
                "type":        "role",
                "title":       pos.get("title", ""),
                "description": f"{pos.get('title', '')} at {pos.get('companyName', '')}",
                "cursor":      str(pos.get("id", "")),
            })
        for skill in profile.get("skills", {}).get("values", []):
            name = skill.get("skill", {}).get("name", "")
            items.append({
                "type":        "skill",
                "title":       name,
                "description": name,
                "cursor":      None,
            })
        return items
