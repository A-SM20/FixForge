"""GitHub service for interacting with the GitHub API.

Supports PyGithub and direct HTTPX requests for high-resiliency
public and authenticated issue fetching.
"""

from __future__ import annotations

import logging

import httpx
from github import Github, GithubException

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_github_client() -> Github:
    """Create a GitHub client with the configured token."""
    settings = get_settings()
    return Github(settings.github_token)


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL into (owner, repo) tuple."""
    parts = url.rstrip("/").rstrip(".git").split("/")
    return parts[-2], parts[-1]


def parse_issue_url(url: str) -> tuple[str, str, int]:
    """Parse a GitHub issue URL into (owner, repo, issue_number)."""
    parts = url.rstrip("/").split("/")
    return parts[-4], parts[-3], int(parts[-1])


async def fetch_issue(issue_url: str) -> dict:
    """Fetch issue details from GitHub (supports public & authenticated)."""
    owner, repo, number = parse_issue_url(issue_url)
    settings = get_settings()

    headers = {"User-Agent": "FixForge-Agent", "Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{number}",
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                labels = [lbl["name"] for lbl in data.get("labels", []) if isinstance(lbl, dict)]
                return {
                    "title": data.get("title", f"Issue #{number}"),
                    "body": data.get("body", "") or "",
                    "labels": labels,
                    "number": number,
                    "url": data.get("html_url", issue_url),
                }
            elif resp.status_code in {401, 403}:
                logger.warning("GitHub API rate limit or auth needed: status %d", resp.status_code)
    except Exception as e:
        logger.warning("HTTPX fetch failed (%s), trying PyGithub fallback", e)

    # Fallback to PyGithub if configured
    try:
        gh_client = get_github_client()
        gh_repo = gh_client.get_repo(f"{owner}/{repo}")
        issue = gh_repo.get_issue(number)
        return {
            "title": issue.title,
            "body": issue.body or "",
            "labels": [label.name for label in issue.labels],
            "number": issue.number,
            "url": issue.html_url,
        }
    except Exception as e:
        logger.error("Failed to fetch issue from GitHub: %s", e)
        raise RuntimeError(f"Could not retrieve issue details from GitHub: {e}")


async def create_pull_request(
    repo_url: str,
    branch_name: str,
    title: str,
    body: str,
    base: str = "main",
) -> str:
    """Create a pull request on GitHub."""
    owner, repo = parse_github_url(repo_url)
    client = get_github_client()

    try:
        gh_repo = client.get_repo(f"{owner}/{repo}")
        pr = gh_repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base,
        )
        return pr.html_url
    except GithubException as e:
        logger.warning("PR creation via API not possible (%s), returning target PR URL", e)
        return f"https://github.com/{owner}/{repo}/pull/new/{branch_name}"
