import pytest
from fastapi import status


# ---------------- Behavior A: Concurrent Assignment ----------------

def test_concurrent_assignment_protection(client, test_team, member_token, outsider_token, manager_token):
    """
    Test Reliability Behaviour A:
    When an item is unassigned, user 1 successfully claims it.
    If user 2 attempts to claim the same item with the stale version (or after it is claimed),
    the request is rejected with HTTP 409 Conflict.
    """
    # Create unassigned work item
    create_resp = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": "Unassigned Critical Database Bug",
            "description": "Needs immediate claim",
            "item_type": "BUG",
            "priority": "CRITICAL",
            "status": "OPEN",
            "team_id": test_team.id,
            "assignee_id": None,
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    item = create_resp.json()
    item_id = item["id"]
    initial_version = item["version"]

    # First user claims successfully
    claim_1 = client.post(
        f"/api/work-items/{item_id}/claim",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"version": initial_version},
    )
    assert claim_1.status_code == status.HTTP_200_OK
    assert claim_1.json()["assignee_id"] is not None
    assert claim_1.json()["version"] == initial_version + 1

    # Second user tries to claim the same work item
    claim_2 = client.post(
        f"/api/work-items/{item_id}/claim",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"version": initial_version},
    )
    assert claim_2.status_code == status.HTTP_409_CONFLICT
    assert "already been claimed" in claim_2.json()["detail"] or "Conflict" in claim_2.json()["detail"]


# ---------------- Behavior B: Stale Updates ----------------

def test_stale_update_rejection(client, test_team, manager_token):
    """
    Test Reliability Behaviour B:
    If User A updates a work item, incrementing its version from 1 to 2,
    User B attempting to update using stale version 1 must receive HTTP 409 Conflict.
    """
    create_resp = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": "Concurrency Target Task",
            "description": "Original text",
            "item_type": "TASK",
            "priority": "LOW",
            "status": "OPEN",
            "team_id": test_team.id,
        },
    )
    item_id = create_resp.json()["id"]
    stale_version = create_resp.json()["version"]

    # User A updates title (version increments to 2)
    update_a = client.put(
        f"/api/work-items/{item_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": "User A Updated Title",
            "version": stale_version,
        },
    )
    assert update_a.status_code == status.HTTP_200_OK
    assert update_a.json()["version"] == stale_version + 1

    # User B sends update using original stale_version
    update_b = client.put(
        f"/api/work-items/{item_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": "User B Stale Overwrite Attempt",
            "version": stale_version,
        },
    )
    assert update_b.status_code == status.HTTP_409_CONFLICT
    assert "Conflict" in update_b.json()["detail"]
    assert "modified by another user" in update_b.json()["detail"]


def test_stale_status_update_rejection(client, test_team, manager_token):
    """Test optimistic concurrency control on direct status transition endpoint."""
    create_resp = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": "Status OCC Test",
            "item_type": "TASK",
            "priority": "LOW",
            "status": "OPEN",
            "team_id": test_team.id,
        },
    )
    item_id = create_resp.json()["id"]

    # Valid transition OPEN -> IN_PROGRESS
    res1 = client.patch(
        f"/api/work-items/{item_id}/status",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"status": "IN_PROGRESS", "version": 1},
    )
    assert res1.status_code == status.HTTP_200_OK
    assert res1.json()["version"] == 2

    # Second status update with old version 1 -> 409
    res2 = client.patch(
        f"/api/work-items/{item_id}/status",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"status": "BLOCKED", "version": 1},
    )
    assert res2.status_code == status.HTTP_409_CONFLICT


# ---------------- Behavior C: Authorization ----------------

def test_authorization_member_cannot_modify_unauthorized_team(client, outsider_token, test_team):
    """
    Test Reliability Behaviour C:
    A user who is not a member of the team cannot view, modify, or create tasks in that team.
    Hiding buttons on frontend is not enough; API must reject direct calls with HTTP 403 Forbidden.
    """
    # Outsider tries to create an item in test_team
    create_resp = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {outsider_token}"},
        json={
            "title": "Unauthorized Item Creation",
            "team_id": test_team.id,
            "priority": "LOW",
            "status": "OPEN",
            "item_type": "TASK",
        },
    )
    assert create_resp.status_code == status.HTTP_403_FORBIDDEN


def test_authorization_member_cannot_delete_work_item(client, member_token, manager_token, test_team):
    """Members cannot delete work items (Admin/Manager only)."""
    create_resp = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": "Item To Delete",
            "team_id": test_team.id,
            "priority": "LOW",
            "status": "OPEN",
            "item_type": "TASK",
        },
    )
    item_id = create_resp.json()["id"]

    del_resp = client.delete(
        f"/api/work-items/{item_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert del_resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------- Behavior D: Duplicate Operations & Activity History ----------------

def test_idempotent_work_item_creation(client, manager_token, test_team):
    """
    Test Reliability Behaviour D:
    Using an Idempotency-Key header ensures repeating the exact request
    returns the identical cached result and does NOT create a duplicate record in the database.
    """
    idempotency_key = "test-idem-key-unique-12345"
    payload = {
        "title": "Idempotent Work Item",
        "description": "Safe against network retries",
        "team_id": test_team.id,
        "priority": "HIGH",
        "status": "OPEN",
        "item_type": "FEATURE",
    }

    # Request 1
    resp1 = client.post(
        "/api/work-items",
        headers={
            "Authorization": f"Bearer {manager_token}",
            "Idempotency-Key": idempotency_key,
        },
        json=payload,
    )
    assert resp1.status_code == status.HTTP_201_CREATED
    item1 = resp1.json()

    # Repeated Request 2 with same Idempotency-Key
    resp2 = client.post(
        "/api/work-items",
        headers={
            "Authorization": f"Bearer {manager_token}",
            "Idempotency-Key": idempotency_key,
        },
        json=payload,
    )
    assert resp2.status_code == status.HTTP_201_CREATED
    item2 = resp2.json()

    # Must return exact same work item ID
    assert item1["id"] == item2["id"]

    # Verify in DB total count is 1, not 2
    list_resp = client.get(
        "/api/work-items?search=Idempotent Work Item",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert list_resp.json()["total"] == 1


def test_activity_history_transaction_consistency(client, manager_token, test_team):
    """
    Test Activity Log transaction consistency:
    - Successful status change records actor, previous value, new value, and timestamp.
    - Invalid transition (e.g., OPEN -> RESOLVED directly) fails with HTTP 400 and does NOT record any activity event.
    """
    create_resp = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "title": "Audit Consistency Item",
            "team_id": test_team.id,
            "priority": "LOW",
            "status": "OPEN",
            "item_type": "TASK",
        },
    )
    item_id = create_resp.json()["id"]

    # 1. Invalid status transition OPEN -> RESOLVED should fail
    fail_resp = client.patch(
        f"/api/work-items/{item_id}/status",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"status": "RESOLVED", "version": 1},
    )
    assert fail_resp.status_code == status.HTTP_400_BAD_REQUEST

    # Check activity logs: should only have CREATED, no failed transition logged
    act_resp1 = client.get(
        f"/api/work-items/{item_id}/activity",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    actions1 = [a["action"] for a in act_resp1.json()]
    assert "STATUS_CHANGE" not in actions1

    # 2. Valid status transition OPEN -> IN_PROGRESS
    ok_resp = client.patch(
        f"/api/work-items/{item_id}/status",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"status": "IN_PROGRESS", "version": 1},
    )
    assert ok_resp.status_code == status.HTTP_200_OK

    # Check activity logs now: STATUS_CHANGE must be present with previous & new values
    act_resp2 = client.get(
        f"/api/work-items/{item_id}/activity",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    activities = act_resp2.json()
    status_changes = [a for a in activities if a["action"] == "STATUS_CHANGE"]
    assert len(status_changes) == 1
    assert status_changes[0]["previous_value"] == "OPEN"
    assert status_changes[0]["new_value"] == "IN_PROGRESS"
    assert status_changes[0]["timestamp"] is not None
