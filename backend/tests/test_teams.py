from fastapi import status


def test_admin_can_create_team(client, admin_token):
    response = client.post(
        "/api/teams",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "DevOps Engineers", "description": "DevOps and cloud team"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "DevOps Engineers"


def test_member_cannot_create_team(client, member_token):
    response = client.post(
        "/api/teams",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"name": "Unauthorized Team", "description": "Should fail"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_add_and_remove_member(client, admin_token, test_team, outsider_user):
    # Add member
    add_resp = client.post(
        f"/api/teams/{test_team.id}/members",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_id": outsider_user.id, "team_role": "MEMBER"},
    )
    assert add_resp.status_code == status.HTTP_201_CREATED

    # Remove member
    del_resp = client.delete(
        f"/api/teams/{test_team.id}/members/{outsider_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT


def test_member_cannot_add_team_member(client, member_token, test_team, outsider_user):
    response = client.post(
        f"/api/teams/{test_team.id}/members",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"user_id": outsider_user.id, "team_role": "MEMBER"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
