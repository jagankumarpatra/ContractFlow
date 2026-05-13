def test_register_success(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Jagan Kumar",
        "email": "jagan@test.com",
        "password": "securepass123",
        "company_name": "Runo Inc"
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "jagan@test.com"
    assert data["user"]["role"] == "admin"  # first user = admin

def test_register_duplicate_email(client):
    payload = {
        "name": "User One", "email": "dup@test.com",
        "password": "pass123", "company_name": "Company A"
    }
    client.post("/api/v1/auth/register", json=payload)
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409

def test_register_second_user_is_member(client):
    client.post("/api/v1/auth/register", json={
        "name": "Admin", "email": "admin@company.com",
        "password": "pass123", "company_name": "SharedCo"
    })
    res = client.post("/api/v1/auth/register", json={
        "name": "Member", "email": "member@company.com",
        "password": "pass123", "company_name": "SharedCo"
    })
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "member"

def test_login_success(client, registered_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_login_wrong_password(client, registered_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert res.status_code == 401

def test_login_nonexistent_user(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "pass123"
    })
    assert res.status_code == 401

def test_protected_route_without_token(client):
    res = client.get("/api/v1/contracts/")
    assert res.status_code == 403

def test_protected_route_with_invalid_token(client):
    res = client.get("/api/v1/contracts/",
                     headers={"Authorization": "Bearer invalidtoken"})
    assert res.status_code == 401
