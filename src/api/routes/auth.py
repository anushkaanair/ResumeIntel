"""OAuth 2.0 flows for LinkedIn and GitHub (patent claim 1d — live profile sync).

Both platforms require a 3-legged OAuth redirect so each user authorises
their own account. Tokens are stored in Redis keyed by resume_id so that
canvas.py's profile-sync routes can fetch per-user data — not a shared
server-side token.
"""

from __future__ import annotations

import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from src.config.settings import settings
from src.db.redis_store import rget, rset

router = APIRouter()

_STATE_KEY = "linkedin_oauth_state:{state}"
_TOKEN_KEY = "linkedin_token:{resume_id}"

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

SCOPES = "openid profile email"


@router.get("/auth/linkedin/login")
async def linkedin_login(resume_id: str = Query(...)) -> dict:
    """Return the LinkedIn authorization URL for the frontend to redirect to."""
    if not settings.linkedin_client_id:
        raise HTTPException(
            status_code=501,
            detail="LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID and "
            "LINKEDIN_CLIENT_SECRET in your .env file.",
        )

    state = secrets.token_urlsafe(24)
    await rset(_STATE_KEY.format(state=state), {"resume_id": resume_id}, ttl=600)

    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    auth_url = f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"status": "ok", "data": {"auth_url": auth_url}}


@router.get("/auth/linkedin/callback")
async def linkedin_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> RedirectResponse:
    """Exchange the authorization code for an access token and store it in Redis."""
    state_data = await rget(_STATE_KEY.format(state=state)) if state else None
    resume_id = state_data.get("resume_id") if state_data else ""

    if error or not code or not state_data:
        redirect = f"{settings.frontend_base_url}/canvas/{resume_id or 'unknown'}?linkedin=error"
        return RedirectResponse(url=redirect)

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.linkedin_redirect_uri,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if token_resp.status_code != 200:
        redirect = f"{settings.frontend_base_url}/canvas/{resume_id}?linkedin=error"
        return RedirectResponse(url=redirect)

    token_data = token_resp.json()
    access_token = token_data.get("access_token", "")
    expires_in = token_data.get("expires_in", 3600)

    if access_token:
        await rset(
            _TOKEN_KEY.format(resume_id=resume_id),
            {"access_token": access_token},
            ttl=expires_in,
        )

    redirect = f"{settings.frontend_base_url}/canvas/{resume_id}?linkedin=connected"
    return RedirectResponse(url=redirect)


@router.get("/auth/linkedin/status")
async def linkedin_status(resume_id: str = Query(...)) -> dict:
    """Check whether this resume_id has a live LinkedIn token connected."""
    token_data = await rget(_TOKEN_KEY.format(resume_id=resume_id))
    return {"status": "ok", "data": {"connected": bool(token_data and token_data.get("access_token"))}}


async def get_linkedin_token(resume_id: str) -> str:
    """Helper used by canvas.py to fetch the stored access token, if any."""
    token_data = await rget(_TOKEN_KEY.format(resume_id=resume_id))
    return token_data.get("access_token", "") if token_data else ""


async def fetch_linkedin_profile(access_token: str) -> list[dict]:
    """Fetch identity data from LinkedIn's OpenID Connect userinfo endpoint.

    Returns delta items in the same shape as _fetch_github_deltas for
    consistency with the JD-relevance filter in canvas.py.
    """
    if not access_token:
        return []

    headers = {"Authorization": f"Bearer {access_token}"}
    deltas: list[dict] = []

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(LINKEDIN_USERINFO_URL, headers=headers)
        if resp.status_code == 200:
            profile = resp.json()
            headline = profile.get("headline") or ""
            name = profile.get("name") or ""
            if headline:
                deltas.append({"type": "headline", "text": headline, "platform": "linkedin"})
            if name and not headline:
                deltas.append({
                    "type": "profile",
                    "text": f"LinkedIn profile connected for {name}. "
                    "Position and certification history requires LinkedIn partner API access.",
                    "platform": "linkedin",
                })

    return deltas


# ─── GitHub OAuth ─────────────────────────────────────────────────────────────

_GH_STATE_KEY = "github_oauth_state:{state}"
_GH_TOKEN_KEY = "github_token:{resume_id}"

GITHUB_AUTH_URL  = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE  = "https://api.github.com"
GITHUB_SCOPES    = "read:user repo"


@router.get("/auth/github/login")
async def github_login(resume_id: str = Query(...)) -> dict:
    """Return the GitHub OAuth authorization URL for the frontend to redirect to."""
    if not settings.github_client_id:
        raise HTTPException(
            status_code=501,
            detail="GitHub OAuth not configured. Set GITHUB_CLIENT_ID and "
                   "GITHUB_CLIENT_SECRET in your .env file.",
        )

    state = secrets.token_urlsafe(24)
    await rset(_GH_STATE_KEY.format(state=state), {"resume_id": resume_id}, ttl=600)

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": GITHUB_SCOPES,
        "state": state,
    }
    auth_url = f"{GITHUB_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"status": "ok", "data": {"auth_url": auth_url}}


@router.get("/auth/github/callback")
async def github_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> RedirectResponse:
    """Exchange the GitHub authorization code for a user access token."""
    state_data = await rget(_GH_STATE_KEY.format(state=state)) if state else None
    resume_id = state_data.get("resume_id") if state_data else ""

    if error or not code or not state_data:
        redirect = f"{settings.frontend_base_url}/canvas/{resume_id or 'unknown'}?github=error"
        return RedirectResponse(url=redirect)

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

    if token_resp.status_code != 200:
        return RedirectResponse(url=f"{settings.frontend_base_url}/canvas/{resume_id}?github=error")

    token_data = token_resp.json()
    access_token = token_data.get("access_token", "")

    if access_token:
        # GitHub tokens don't expire — store with a long TTL (30 days)
        await rset(
            _GH_TOKEN_KEY.format(resume_id=resume_id),
            {"access_token": access_token},
            ttl=60 * 60 * 24 * 30,
        )

    redirect = f"{settings.frontend_base_url}/canvas/{resume_id}?github=connected"
    return RedirectResponse(url=redirect)


@router.get("/auth/github/status")
async def github_status(resume_id: str = Query(...)) -> dict:
    """Check whether this resume_id has a connected GitHub OAuth token."""
    token_data = await rget(_GH_TOKEN_KEY.format(resume_id=resume_id))
    return {"status": "ok", "data": {"connected": bool(token_data and token_data.get("access_token"))}}


async def get_github_token(resume_id: str) -> str:
    """Helper used by canvas.py to fetch the per-user GitHub access token."""
    token_data = await rget(_GH_TOKEN_KEY.format(resume_id=resume_id))
    return token_data.get("access_token", "") if token_data else ""


async def fetch_github_profile(access_token: str) -> list[dict]:
    """Fetch the user's own repos and bio using their OAuth token.

    Returns delta items in the same shape as the LinkedIn helper so the
    JD-relevance filter in canvas.py works identically for both platforms.
    """
    if not access_token:
        return []

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    deltas: list[dict] = []

    async with httpx.AsyncClient(timeout=10) as client:
        # User profile + bio
        user_resp = await client.get(f"{GITHUB_API_BASE}/user", headers=headers)
        if user_resp.status_code == 200:
            user = user_resp.json()
            bio = user.get("bio") or ""
            if bio:
                deltas.append({"type": "bio", "text": bio, "platform": "github"})

        # Recent non-fork repos (up to 15, sorted by last push)
        repos_resp = await client.get(
            f"{GITHUB_API_BASE}/user/repos?sort=pushed&per_page=15&type=owner",
            headers=headers,
        )
        if repos_resp.status_code == 200:
            for repo in repos_resp.json():
                if repo.get("fork"):
                    continue
                lang = repo.get("language") or ""
                desc = repo.get("description") or ""
                text = f"Built {repo['name']}" \
                       + (f" in {lang}" if lang else "") \
                       + (f" — {desc}" if desc else "")
                deltas.append({
                    "type": "repo",
                    "text": text,
                    "platform": "github",
                    "url": repo.get("html_url", ""),
                })

        # Pinned / starred topics as skills signal
        topics_resp = await client.get(
            f"{GITHUB_API_BASE}/user/starred?per_page=5",
            headers=headers,
        )
        if topics_resp.status_code == 200:
            stars = topics_resp.json()
            langs = list({r.get("language") for r in stars if r.get("language")})
            if langs:
                deltas.append({
                    "type": "skills",
                    "text": "Experienced with " + ", ".join(langs[:6]),
                    "platform": "github",
                })

    return deltas
