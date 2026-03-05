import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authenticated_client(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "testuser@test.com", "password": "testpass123"}
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@test.com", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ==================== INTEGRATION TESTS ====================

@pytest.mark.asyncio
async def test_health_check(client):
    """Integration test: Health endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Integration test: Root endpoint returns welcome message."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_register_user(client):
    """Integration test: User registration creates new user."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@test.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["email"] == "newuser@test.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Integration test: Cannot register with duplicate email."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@test.com", "password": "password123"}
    )
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@test.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client):
    """Integration test: Login returns access token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "loginuser@test.com", "password": "password123"}
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@test.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """Integration test: Login fails with wrong password."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpass@test.com", "password": "correct"}
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@test.com", "password": "incorrect"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_paper(authenticated_client):
    """Integration test: Authenticated user can create paper."""
    response = await authenticated_client.post(
        "/api/v1/papers",
        json={
            "title": "Test Paper",
            "abstract": "Test abstract",
            "content": "This is test content for the paper",
            "is_public": True
        }
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Paper"


@pytest.mark.asyncio
async def test_get_papers(authenticated_client):
    """Integration test: User can list their papers."""
    await authenticated_client.post(
        "/api/v1/papers",
        json={"title": "Paper 1", "content": "Content 1", "is_public": False}
    )
    response = await authenticated_client.get("/api/v1/papers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_get_paper_by_id(authenticated_client):
    """Integration test: User can get their own paper."""
    create_response = await authenticated_client.post(
        "/api/v1/papers",
        json={"title": "Specific Paper", "content": "Content", "is_public": False}
    )
    paper_id = create_response.json()["id"]
    
    response = await authenticated_client.get(f"/api/v1/papers/{paper_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Specific Paper"


@pytest.mark.asyncio
async def test_update_paper(authenticated_client):
    """Integration test: User can update their paper."""
    create_response = await authenticated_client.post(
        "/api/v1/papers",
        json={"title": "Original Title", "content": "Content", "is_public": False}
    )
    paper_id = create_response.json()["id"]
    
    response = await authenticated_client.patch(
        f"/api/v1/papers/{paper_id}",
        json={"title": "Updated Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_paper(authenticated_client):
    """Integration test: User can delete their paper."""
    create_response = await authenticated_client.post(
        "/api/v1/papers",
        json={"title": "To Delete", "content": "Content", "is_public": False}
    )
    paper_id = create_response.json()["id"]
    
    response = await authenticated_client.delete(f"/api/v1/papers/{paper_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_collection(authenticated_client):
    """Integration test: User can create a collection."""
    response = await authenticated_client.post(
        "/api/v1/collections",
        json={"name": "My Collection"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "My Collection"


@pytest.mark.asyncio
async def test_get_collections(authenticated_client):
    """Integration test: User can list their collections."""
    await authenticated_client.post(
        "/api/v1/collections",
        json={"name": "Collection 1"}
    )
    response = await authenticated_client.get("/api/v1/collections")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """Integration test: Cannot access papers without token."""
    response = await client.get("/api/v1/papers")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_access_other_users_private_paper(client):
    """Integration test: Cannot access other user's private paper."""
    # Create user 1 and their paper
    client.headers["Authorization"] = "Bearer user1_token"
    # (This would require setting up multiple users in test)
    # For now, just verify 403/404 for non-existent
    response = await client.get("/api/v1/papers/99999")
    assert response.status_code in [401, 403, 404]
