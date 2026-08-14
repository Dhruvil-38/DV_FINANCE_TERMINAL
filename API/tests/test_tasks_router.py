from datetime import datetime

import models


def test_list_tasks_orders_by_due_date_with_undated_last(client, db, as_role):
    _, headers = as_role("staff")
    db.add_all([
        models.Task(title="No deadline"),
        models.Task(title="Later", due_date=datetime(2024, 6, 1)),
        models.Task(title="Sooner", due_date=datetime(2024, 1, 1)),
    ])
    db.commit()

    response = client.get("/api/tasks", headers=headers)

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["Sooner", "Later", "No deadline"]


def test_list_tasks_forbidden_for_clients(client, as_role):
    _, headers = as_role("client")

    assert client.get("/api/tasks", headers=headers).status_code == 403


def test_create_task_applies_defaults(client, as_role):
    _, headers = as_role("admin")

    response = client.post("/api/tasks", headers=headers, json={"title": "Prepare deck"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "TODO"
    assert body["priority"] == "MEDIUM"
    assert body["assigned_to"] is None
    assert body["due_date"] is None


def test_create_task_forbidden_for_clients(client, as_role):
    _, headers = as_role("client")

    assert client.post("/api/tasks", headers=headers, json={"title": "Nope"}).status_code == 403


def test_update_task_patches_only_supplied_fields(client, db, as_role):
    _, headers = as_role("analyst")
    task = models.Task(title="Prepare deck", status="TODO", priority="LOW", assigned_to="K. Rao")
    db.add(task)
    db.commit()

    response = client.patch(f"/api/tasks/{task.id}", headers=headers,
                            json={"status": "IN_PROGRESS", "priority": "HIGH"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["priority"] == "HIGH"
    assert body["assigned_to"] == "K. Rao"


def test_update_missing_task_returns_404(client, as_role):
    _, headers = as_role("admin")

    response = client.patch("/api/tasks/999", headers=headers, json={"status": "DONE"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
