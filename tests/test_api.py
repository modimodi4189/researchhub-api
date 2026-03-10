import pytest
from httpx import Client, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    with Client(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def authenticated_client(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "testuser@test.com", "password": "testpass123"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@test.com", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ==================== INTEGRATION TESTS ====================

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@test.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["email"] == "newuser@test.com"


def test_register_duplicate_email(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@test.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@test.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "loginuser@test.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@test.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpass@test.com", "password": "correct"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@test.com", "password": "incorrect"}
    )
    assert response.status_code == 401


def test_create_paper(authenticated_client):
    response = authenticated_client.post(
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


def test_get_papers(authenticated_client):
    authenticated_client.post(
        "/api/v1/papers",
        json={"title": "Paper 1", "content": "Content 1", "is_public": False}
    )
    response = authenticated_client.get("/api/v1/papers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_paper_by_id(authenticated_client):
    create_response = authenticated_client.post(
        "/api/v1/papers",
        json={"title": "Specific Paper", "content": "Content", "is_public": False}
    )
    paper_id = create_response.json()["id"]
    
    response = authenticated_client.get(f"/api/v1/papers/{paper_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Specific Paper"


def test_update_paper(authenticated_client):
    create_response = authenticated_client.post(
        "/api/v1/papers",
        json={"title": "Original Title", "content": "Content", "is_public": False}
    )
    paper_id = create_response.json()["id"]
    
    response = authenticated_client.patch(
        f"/api/v1/papers/{paper_id}",
        json={"title": "Updated Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_delete_paper(authenticated_client):
    create_response = authenticated_client.post(
        "/api/v1/papers",
        json={"title": "To Delete", "content": "Content", "is_public": False}
    )
    paper_id = create_response.json()["id"]
    
    response = authenticated_client.delete(f"/api/v1/papers/{paper_id}")
    assert response.status_code == 204


def test_create_collection(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/collections",
        json={"name": "My Collection"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "My Collection"


def test_get_collections(authenticated_client):
    authenticated_client.post(
        "/api/v1/collections",
        json={"name": "Collection 1"}
    )
    response = authenticated_client.get("/api/v1/collections")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unauthorized_access(client):
    response = client.get("/api/v1/papers")
    assert response.status_code == 403


def test_access_other_users_private_paper(client):
    response = client.get("/api/v1/papers/99999")
    assert response.status_code in [401, 403, 404]
