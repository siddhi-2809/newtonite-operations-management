from fastapi import status


def test_register_first_user_becomes_admin(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "first_user@newtonite.io",
            "password": "Password123!",
            "full_name": "First Admin",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "first_user@newtonite.io"
    assert data["role"] == "ADMIN"
    assert "hashed_password" not in data


def test_register_duplicate_email_fails(client, member_user):
    response = client.post(
        "/api/auth/register",
        json={
            "email": member_user.email,
            "password": "Password123!",
            "full_name": "Duplicate User",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]


def test_login_success(client, member_user):
    response = client.post(
        "/api/auth/login",
        json={
            "email": member_user.email,
            "password": "MemberPass123!",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == member_user.email


def test_login_invalid_password(client, member_user):
    response = client.post(
        "/api/auth/login",
        json={
            "email": member_user.email,
            "password": "WrongPassword!",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_authenticated(client, member_token, member_user):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == member_user.email
    assert data["role"] == "MEMBER"


def test_get_me_unauthenticated(client):
    response = client.get("/api/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
