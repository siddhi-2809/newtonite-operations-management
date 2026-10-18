from fastapi import status


def test_create_work_item_success(client, manager_token, test_team, member_user):
    payload = {
        "title": "Migrate Redis cluster to AWS ElastiCache",
        "description": "Upgrade Redis from 6.x to 7.x with zero downtime.",
        "item_type": "TASK",
        "priority": "HIGH",
        "status": "OPEN",
        "team_id": test_team.id,
        "assignee_id": member_user.id,
    }
    response = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {manager_token}"},
        json=payload,
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["version"] == 1
    assert data["team_id"] == test_team.id
    assert data["assignee_id"] == member_user.id


def test_pagination_and_filtering(client, manager_token, test_team, member_user):
    # Create 5 work items
    for i in range(5):
        client.post(
            "/api/work-items",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "title": f"Batch Task {i}",
                "description": f"Description for task {i}",
                "item_type": "FEATURE",
                "priority": "CRITICAL" if i == 0 else "LOW",
                "status": "OPEN",
                "team_id": test_team.id,
                "assignee_id": member_user.id if i % 2 == 0 else None,
            },
        )

    # Test page size
    resp_page = client.get(
        "/api/work-items?page=1&page_size=2",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp_page.status_code == status.HTTP_200_OK
    data = resp_page.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["total_pages"] == 3

    # Test filter by priority
    resp_filter = client.get(
        "/api/work-items?priority=CRITICAL",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp_filter.status_code == status.HTTP_200_OK
    crit_items = resp_filter.json()["items"]
    assert len(crit_items) == 1
    assert crit_items[0]["title"] == "Batch Task 0"

    # Test search
    resp_search = client.get(
        "/api/work-items?search=Task 3",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp_search.status_code == status.HTTP_200_OK
    search_items = resp_search.json()["items"]
    assert len(search_items) == 1
    assert search_items[0]["title"] == "Batch Task 3"


def test_add_comment_and_view_activity(client, member_token, test_team):
    # First create an item
    create_resp = client.post(
        "/api/work-items",
        headers={"Authorization": f"Bearer {member_token}"},
        json={
            "title": "Commentable item",
            "description": "Item to test comments",
            "item_type": "TASK",
            "priority": "MEDIUM",
            "status": "OPEN",
            "team_id": test_team.id,
        },
    )
    item_id = create_resp.json()["id"]

    # Add comment
    comment_resp = client.post(
        f"/api/work-items/{item_id}/comments",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"content": "Root cause identified in connection pool leak."},
    )
    assert comment_resp.status_code == status.HTTP_201_CREATED
    assert comment_resp.json()["content"] == "Root cause identified in connection pool leak."

    # Fetch activity history
    activity_resp = client.get(
        f"/api/work-items/{item_id}/activity",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert activity_resp.status_code == status.HTTP_200_OK
    activities = activity_resp.json()
    actions = [a["action"] for a in activities]
    assert "CREATED" in actions
    assert "COMMENT_ADDED" in actions
