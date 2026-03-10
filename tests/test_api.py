from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_register_user():
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@test.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["email"] == "newuser@test.com"


def test_register_duplicate_email():
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


def test_login_success():
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


def test_login_invalid_credentials():
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpass@test.com", "password": "correct"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@test.com", "password": "incorrect"}
    )
    assert response.status_code == 401


def test_create_paper():
    client.post(
        "/api/v1/auth/register",
        json={"email": "paperuser@test.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "paperuser@test.com", "password": "password123"}
    )
    token = response.json()["access_token"]
    
    response = client.post(
        "/api/v1/papers",
        json={
            "title": "Test Paper",
            "abstract": "Test abstract",
            "content": "This is test content for the paper",
            "is_public": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Paper"


def test_get_papers():
    client.post(
        "/api/v1/auth/register",
        json={"email": "getpapers@test.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "getpapers@test.com", "password": "password123"}
    )
    token = response.json()["access_token"]
    
    client.post(
        "/api/v1/papers",
        json={"title": "Paper 1", "content": "Content 1", "is_public": False},
        headers={"Authorization": f"Bearer {token}"}
    )
    response = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unauthorized_access():
    response = client.get("/api/v1/papers")
    assert response.status_code == 403
