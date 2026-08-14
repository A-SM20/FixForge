"""API route tests for /api/runs endpoints.

Tests the full request/response cycle through the FastAPI app
using the async test client and in-memory SQLite database.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Health endpoint should return 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_create_run(client):
    """POST /api/runs should create a new run and return 201."""
    payload = {
        "issue_url": "https://github.com/pallets/flask/issues/1234",
        "repo_url": "https://github.com/pallets/flask",
    }
    response = await client.post("/api/runs/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["issue_url"] == str(payload["issue_url"])
    assert data["repo_url"] == str(payload["repo_url"])
    assert data["status"] == "pending"
    assert data["state"] == "READ_ISSUE"
    assert data["iteration_count"] == 0
    assert "id" in data


@pytest.mark.asyncio
async def test_create_run_invalid_url(client):
    """POST /api/runs with invalid URL should return 422."""
    payload = {
        "issue_url": "not-a-url",
        "repo_url": "https://github.com/pallets/flask",
    }
    response = await client.post("/api/runs/", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_runs_empty(client):
    """GET /api/runs should return empty list when no runs exist."""
    response = await client.get("/api/runs/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_runs_with_data(client):
    """GET /api/runs should return created runs."""
    # Create two runs
    for i in range(2):
        await client.post("/api/runs/", json={
            "issue_url": f"https://github.com/test/repo/issues/{i}",
            "repo_url": "https://github.com/test/repo",
        })

    response = await client.get("/api/runs/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_runs_pagination(client):
    """GET /api/runs with pagination should limit results."""
    # Create 3 runs
    for i in range(3):
        await client.post("/api/runs/", json={
            "issue_url": f"https://github.com/test/repo/issues/{i}",
            "repo_url": "https://github.com/test/repo",
        })

    response = await client.get("/api/runs/?page=1&page_size=2")
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_list_runs_filter_by_status(client):
    """GET /api/runs with status filter should return matching runs."""
    # Create a run (status=pending by default)
    await client.post("/api/runs/", json={
        "issue_url": "https://github.com/test/repo/issues/1",
        "repo_url": "https://github.com/test/repo",
    })

    # Filter by pending — should find 1
    response = await client.get("/api/runs/?status=pending")
    data = response.json()
    assert data["total"] == 1

    # Filter by success — should find 0
    response = await client.get("/api/runs/?status=success")
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_run_detail(client):
    """GET /api/runs/{id} should return full run details."""
    # Create a run
    create_response = await client.post("/api/runs/", json={
        "issue_url": "https://github.com/test/repo/issues/1",
        "repo_url": "https://github.com/test/repo",
    })
    run_id = create_response.json()["id"]

    # Fetch details
    response = await client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["patches"] == []


@pytest.mark.asyncio
async def test_get_run_not_found(client):
    """GET /api/runs/{id} with unknown ID should return 404."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/runs/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_run(client):
    """DELETE /api/runs/{id} should remove the run."""
    # Create a run
    create_response = await client.post("/api/runs/", json={
        "issue_url": "https://github.com/test/repo/issues/1",
        "repo_url": "https://github.com/test/repo",
    })
    run_id = create_response.json()["id"]

    # Delete it
    response = await client.delete(f"/api/runs/{run_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = await client.get(f"/api/runs/{run_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_run_not_found(client):
    """DELETE /api/runs/{id} with unknown ID should return 404."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"/api/runs/{fake_id}")
    assert response.status_code == 404
