"""GitHub service for interacting with the GitHub API.

Uses PyGithub for reading issues and opening pull requests.
"""

from __future__ import annotations

import logging

from github import Github, GithubException

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_github_client() -> Github:
    """Create a GitHub client with the configured token."""
    settings = get_settings()
    return Github(settings.github_token)


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL into (owner, repo) tuple.

    Handles both https://github.com/owner/repo and
    https://github.com/owner/repo.git formats.
    """
    parts = url.rstrip("/").rstrip(".git").split("/")
    return parts[-2], parts[-1]


def parse_issue_url(url: str) -> tuple[str, str, int]:
    """Parse a GitHub issue URL into (owner, repo, issue_number).

    E.g., https://github.com/owner/repo/issues/123
    """
    parts = url.rstrip("/").split("/")
    return parts[-4], parts[-3], int(parts[-1])


async def fetch_issue(issue_url: str) -> dict:
    """Fetch issue details from GitHub.

    Returns:
        Dict with 'title', 'body', 'labels', 'number'.
    """
    owner, repo, number = parse_issue_url(issue_url)
    client = get_github_client()

    try:
        gh_repo = client.get_repo(f"{owner}/{repo}")
        issue = gh_repo.get_issue(number)

        return {
            "title": issue.title,
            "body": issue.body or "",
            "labels": [label.name for label in issue.labels],
            "number": issue.number,
            "url": issue.html_url,
        }
    except GithubException as e:
        logger.error(
            "Failed to fetch issue",
            extra={"url": issue_url, "error": str(e)},
        )
        raise


async def create_pull_request(
    repo_url: str,
    branch_name: str,
    title: str,
    body: str,
    base: str = "main",
) -> str:
    """Create a pull request on GitHub.

    Returns:
        The PR URL.
    """
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
        logger.info(
            "PR created",
            extra={"pr_url": pr.html_url},
        )
        return pr.html_url
    except GithubException as e:
        logger.error(
            "Failed to create PR",
            extra={"repo": f"{owner}/{repo}", "error": str(e)},
        )
        raise
