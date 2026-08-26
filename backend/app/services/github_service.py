"""GitHub service for interacting with the GitHub API.

Supports PyGithub and direct HTTPX requests for high-resiliency
public and authenticated issue fetching, repo tree listing, and
raw file content retrieval.
"""

from __future__ import annotations

import base64
import logging
import re

import httpx
from github import Github, GithubException

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Placeholder tokens that should NOT be sent as Authorization headers
_PLACEHOLDER_TOKENS = {"ghp-placeholder", "ghp_your-token-here", "sk-placeholder", ""}

# In-memory cache for default branch per repo (avoids redundant API calls)
_branch_cache: dict[str, str] = {}

# Maximum file content size to fetch (50KB — balances LLM context vs completeness)
MAX_FILE_CONTENT_CHARS = 50_000


def _is_valid_token(token: str | None) -> bool:
    """Check whether a token is a real credential (not a placeholder)."""
    if not token:
        return False
    return token.strip() not in _PLACEHOLDER_TOKENS


def _build_github_headers(*, accept: str = "application/vnd.github.v3+json") -> dict[str, str]:
    """Build GitHub API request headers, attaching auth only if the token is real."""
    settings = get_settings()
    headers = {"User-Agent": "FixForge-Agent", "Accept": accept}
    if _is_valid_token(settings.github_token):
        headers["Authorization"] = f"token {settings.github_token}"
    return headers


def get_github_client() -> Github:
    """Create a GitHub client with the configured token."""
    settings = get_settings()
    token = settings.github_token if _is_valid_token(settings.github_token) else None
    return Github(token)


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL into (owner, repo) tuple."""
    parts = url.rstrip("/").rstrip(".git").split("/")
    return parts[-2], parts[-1]


def parse_issue_url(url: str) -> tuple[str, str, int]:
    """Parse a GitHub issue URL into (owner, repo, issue_number)."""
    parts = url.rstrip("/").split("/")
    return parts[-4], parts[-3], int(parts[-1])


async def fetch_default_branch(owner: str, repo: str) -> str:
    """Fetch the default branch name for a repository.

    Queries `GET /repos/{owner}/{repo}` and returns the `default_branch`
    field (e.g. 'main', 'master', 'develop').  Falls back to 'main' if
    the API call fails.  Results are cached in-memory to avoid redundant
    API calls when fetching multiple files from the same repo.
    """
    cache_key = f"{owner}/{repo}"
    if cache_key in _branch_cache:
        return _branch_cache[cache_key]

    headers = _build_github_headers()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=headers,
            )
            if resp.status_code == 200:
                branch = resp.json().get("default_branch", "main")
                logger.info("Resolved default branch for %s/%s: %s", owner, repo, branch)
                _branch_cache[cache_key] = branch
                return branch
    except Exception as e:
        logger.warning(
            "Could not fetch default branch for %s/%s (%s), falling back to 'main'",
            owner, repo, e,
        )
    _branch_cache[cache_key] = "main"
    return "main"


async def fetch_issue(issue_url: str) -> dict:
    """Fetch issue details from GitHub (supports public & authenticated)."""
    owner, repo, number = parse_issue_url(issue_url)

    headers = _build_github_headers()

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


async def fetch_issue_comments(
    owner: str,
    repo: str,
    number: int,
    max_comments: int = 10,
) -> list[dict]:
    """Fetch the top comments on a GitHub issue.

    Returns a list of dicts with 'author' and 'body' keys.
    Comments often contain stack traces, reproduction steps,
    and maintainer hints that are critical for diagnosis.
    """
    headers = _build_github_headers()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments",
                headers=headers,
                params={"per_page": max_comments},
            )
            if resp.status_code == 200:
                return [
                    {
                        "author": c.get("user", {}).get("login", "unknown"),
                        "body": c.get("body", ""),
                    }
                    for c in resp.json()
                    if c.get("body")
                ]
    except Exception as e:
        logger.warning("Failed to fetch issue comments: %s", e)
    return []


async def fetch_repo_tree(
    owner: str,
    repo: str,
    extensions: tuple[str, ...] = (
        ".py", ".ts", ".js", ".jsx", ".tsx",
        ".go", ".rs", ".java", ".rb", ".c", ".cpp", ".h",
        ".cs", ".swift", ".kt", ".scala", ".php", ".sh",
    ),
    branch: str | None = None,
) -> list[str]:
    """Fetch the full file tree of a repo from GitHub API.

    Returns a list of file paths (e.g. 'src/ambforecast/forecast.py')
    filtered to the given extensions.
    """
    if branch is None:
        branch = await fetch_default_branch(owner, repo)

    headers = _build_github_headers()

    url = (
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/git/trees/{branch}?recursive=1"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                tree = resp.json().get("tree", [])
                return [
                    item["path"]
                    for item in tree
                    if item.get("type") == "blob"
                    and any(item["path"].endswith(ext) for ext in extensions)
                ]
    except Exception as e:
        logger.warning("Failed to fetch repo tree: %s", e)
    return []


async def fetch_file_content(
    owner: str, repo: str, path: str, ref: str | None = None
) -> str:
    """Fetch raw file content from GitHub (up to MAX_FILE_CONTENT_CHARS)."""
    if ref is None:
        ref = await fetch_default_branch(owner, repo)

    headers = _build_github_headers(accept="application/vnd.github.v3.raw")

    url = (
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/contents/{path}?ref={ref}"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.text[:MAX_FILE_CONTENT_CHARS]
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", path, e)
    return ""


async def create_pull_request(
    repo_url: str,
    branch_name: str,
    title: str,
    body: str,
    base: str | None = None,
) -> str:
    """Create a pull request on GitHub."""
    owner, repo = parse_github_url(repo_url)

    if base is None:
        base = await fetch_default_branch(owner, repo)

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


async def create_pull_request_via_api(
    owner: str,
    repo: str,
    branch: str,
    title: str,
    body: str,
    diff: str,
    base: str,
) -> str:
    """Create a real pull request via the GitHub REST API.

    Steps:
    1. Get base branch HEAD SHA
    2. Create a new branch ref from that SHA
    3. Parse the diff to extract changed file paths and new content
    4. For each changed file: create blob → build tree entry
    5. Create a new tree from entries
    6. Create a commit on the new tree
    7. Update the branch ref to point to the new commit
    8. Open a pull request from the branch to base

    Raises RuntimeError if the token lacks write access or the API fails.
    """
    headers = _build_github_headers()
    api = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Get base branch HEAD SHA
        resp = await client.get(f"{api}/git/refs/heads/{base}", headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Cannot read base branch '{base}': {resp.status_code} {resp.text}")
        base_sha = resp.json()["object"]["sha"]

        # 2. Create the new branch
        resp = await client.post(
            f"{api}/git/refs",
            headers=headers,
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )
        if resp.status_code == 422:
            # Branch already exists — update it
            resp = await client.patch(
                f"{api}/git/refs/heads/{branch}",
                headers=headers,
                json={"sha": base_sha, "force": True},
            )
        if resp.status_code not in {200, 201}:
            raise RuntimeError(f"Cannot create branch '{branch}': {resp.status_code} {resp.text}")

        # 3. Get the base tree SHA
        resp = await client.get(f"{api}/git/commits/{base_sha}", headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Cannot read base commit: {resp.status_code}")
        base_tree_sha = resp.json()["tree"]["sha"]

        # 4. Parse the diff to extract changed files and apply changes
        tree_entries = await _diff_to_tree_entries(
            client, api, headers, owner, repo, base, diff
        )

        if not tree_entries:
            raise RuntimeError("No valid file changes extracted from diff")

        # 5. Create a new tree
        resp = await client.post(
            f"{api}/git/trees",
            headers=headers,
            json={"base_tree": base_tree_sha, "tree": tree_entries},
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Cannot create tree: {resp.status_code} {resp.text}")
        new_tree_sha = resp.json()["sha"]

        # 6. Create a commit
        resp = await client.post(
            f"{api}/git/commits",
            headers=headers,
            json={
                "message": title,
                "tree": new_tree_sha,
                "parents": [base_sha],
            },
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Cannot create commit: {resp.status_code} {resp.text}")
        new_commit_sha = resp.json()["sha"]

        # 7. Update the branch ref
        resp = await client.patch(
            f"{api}/git/refs/heads/{branch}",
            headers=headers,
            json={"sha": new_commit_sha},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Cannot update branch ref: {resp.status_code} {resp.text}")

        # 8. Create the pull request
        resp = await client.post(
            f"{api}/pulls",
            headers=headers,
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": base,
            },
        )
        if resp.status_code == 201:
            pr_url = resp.json().get("html_url", "")
            logger.info("PR created successfully: %s", pr_url)
            return pr_url

        raise RuntimeError(f"Cannot create PR: {resp.status_code} {resp.text}")


async def _diff_to_tree_entries(
    client: httpx.AsyncClient,
    api: str,
    headers: dict,
    owner: str,
    repo: str,
    base: str,
    diff: str,
) -> list[dict]:
    """Parse a unified diff and produce GitHub tree entries with new content.

    For each file in the diff, fetch the original content, apply the
    hunks line-by-line, and create a blob with the patched content.
    """
    entries: list[dict] = []

    # Split diff into per-file sections
    file_diffs = re.split(r"(?=^--- a/)", diff, flags=re.MULTILINE)

    for file_diff in file_diffs:
        if not file_diff.strip():
            continue

        # Extract file path
        m_old = re.search(r"^--- a/(.+)$", file_diff, re.MULTILINE)
        m_new = re.search(r"^\+\+\+ b/(.+)$", file_diff, re.MULTILINE)
        if not m_old or not m_new:
            continue

        file_path = m_new.group(1).strip()

        # Fetch original file content
        original = await fetch_file_content(owner, repo, file_path, ref=base)
        if not original:
            logger.warning("Could not fetch original content for %s, skipping", file_path)
            continue

        # Apply the diff hunks to produce patched content
        patched = _apply_diff_hunks(original, file_diff)

        # Create blob via API
        content_b64 = base64.b64encode(patched.encode("utf-8")).decode("ascii")
        resp = await client.post(
            f"{api}/git/blobs",
            headers=headers,
            json={"content": content_b64, "encoding": "base64"},
        )
        if resp.status_code != 201:
            logger.warning("Failed to create blob for %s: %s", file_path, resp.status_code)
            continue

        blob_sha = resp.json()["sha"]
        entries.append({
            "path": file_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })

    return entries


def _apply_diff_hunks(original: str, diff_text: str) -> str:
    """Apply unified diff hunks to original text, producing patched output.

    Simple line-level application: parses @@ -start,count +start,count @@
    hunks and applies additions/removals. Falls back to returning original
    if parsing fails.
    """
    original_lines = original.splitlines(keepends=True)
    # Ensure all lines end with newline for consistency
    if original_lines and not original_lines[-1].endswith("\n"):
        original_lines[-1] += "\n"

    hunks = re.findall(
        r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n(.*?)(?=(?:^@@ |\Z))",
        diff_text,
        re.MULTILINE | re.DOTALL,
    )

    if not hunks:
        return original

    result_lines = list(original_lines)
    offset = 0  # Track line offset from insertions/deletions

    for hunk in hunks:
        old_start = int(hunk[0]) - 1  # Convert to 0-indexed
        hunk_body = hunk[4]

        pos = old_start + offset
        new_lines: list[str] = []
        remove_count = 0

        for line in hunk_body.splitlines(keepends=True):
            if line.startswith("+"):
                new_lines.append(line[1:])
            elif line.startswith("-"):
                remove_count += 1
            elif line.startswith(" "):
                new_lines.append(line[1:])
            elif line.startswith("\\"):
                # "\ No newline at end of file" — skip
                continue
            else:
                new_lines.append(line)

        # Apply: remove old lines, insert new lines
        if 0 <= pos <= len(result_lines):
            result_lines[pos : pos + remove_count] = new_lines
            offset += len(new_lines) - remove_count

    return "".join(result_lines)
