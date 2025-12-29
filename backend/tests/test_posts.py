"""Tests for post endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, auth_headers: dict) -> None:
    """Test creating a post."""
    response = await client.post(
        "/api/v1/posts/",
        headers=auth_headers,
        json={"body": "Hello, world!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["body"] == "Hello, world!"
    assert "author" in data


@pytest.mark.asyncio
async def test_create_post_too_long(client: AsyncClient, auth_headers: dict) -> None:
    """Test creating a post that's too long."""
    response = await client.post(
        "/api/v1/posts/",
        headers=auth_headers,
        json={"body": "x" * 281},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_post_unauthorized(client: AsyncClient) -> None:
    """Test creating a post without auth."""
    response = await client.post(
        "/api/v1/posts/",
        json={"body": "Hello, world!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_explore(client: AsyncClient, auth_headers: dict) -> None:
    """Test getting explore posts."""
    # Create a post first
    await client.post(
        "/api/v1/posts/",
        headers=auth_headers,
        json={"body": "Test post"},
    )

    # Get explore (public endpoint)
    response = await client.get("/api/v1/posts/explore")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_post(client: AsyncClient, auth_headers: dict) -> None:
    """Test getting a specific post."""
    # Create a post
    create_response = await client.post(
        "/api/v1/posts/",
        headers=auth_headers,
        json={"body": "Test post"},
    )
    post_id = create_response.json()["id"]

    # Get the post
    response = await client.get(f"/api/v1/posts/{post_id}")
    assert response.status_code == 200
    assert response.json()["body"] == "Test post"


@pytest.mark.asyncio
async def test_delete_post(client: AsyncClient, auth_headers: dict) -> None:
    """Test deleting a post."""
    # Create a post
    create_response = await client.post(
        "/api/v1/posts/",
        headers=auth_headers,
        json={"body": "Test post"},
    )
    post_id = create_response.json()["id"]

    # Delete the post
    response = await client.delete(
        f"/api/v1/posts/{post_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/api/v1/posts/{post_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_like_post(client: AsyncClient, auth_headers: dict) -> None:
    """Test liking a post."""
    # Create a post
    create_response = await client.post(
        "/api/v1/posts/",
        headers=auth_headers,
        json={"body": "Test post"},
    )
    post_id = create_response.json()["id"]

    # Like the post
    response = await client.post(
        f"/api/v1/posts/{post_id}/like",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify like is reflected
    get_response = await client.get(
        f"/api/v1/posts/{post_id}",
        headers=auth_headers,
    )
    assert get_response.json()["is_liked"] is True
    assert get_response.json()["likes_count"] == 1


@pytest.mark.asyncio
async def test_unlike_post(client: AsyncClient, auth_headers: dict) -> None:
    """Test unliking a post."""
    # Create and like a post
    create_response = await client.post(
        "/api/v1/posts/",
        headers=auth_headers,
        json={"body": "Test post"},
    )
    post_id = create_response.json()["id"]
    await client.post(
        f"/api/v1/posts/{post_id}/like",
        headers=auth_headers,
    )

    # Unlike the post
    response = await client.delete(
        f"/api/v1/posts/{post_id}/like",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Verify unlike is reflected
    get_response = await client.get(
        f"/api/v1/posts/{post_id}",
        headers=auth_headers,
    )
    assert get_response.json()["is_liked"] is False
    assert get_response.json()["likes_count"] == 0
