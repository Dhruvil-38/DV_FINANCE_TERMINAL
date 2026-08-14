from datetime import datetime, timedelta

import models


def test_list_notes_newest_first_for_firm_users(client, db, as_role):
    _, headers = as_role("analyst")
    now = datetime.utcnow()
    db.add_all([
        models.ResearchNote(title="Older", created_by="R. Shah", created_at=now - timedelta(days=1)),
        models.ResearchNote(title="Newer", created_by="R. Shah", created_at=now),
    ])
    db.commit()

    response = client.get("/api/research-notes", headers=headers)

    assert response.status_code == 200
    assert [n["title"] for n in response.json()] == ["Newer", "Older"]


def test_list_notes_filters_by_client_id_query(client, db, as_role, make_client_record):
    _, headers = as_role("admin")
    record = make_client_record(name="Meera Kulkarni")
    db.add_all([
        models.ResearchNote(title="For Meera", created_by="R. Shah", client_id=record.id),
        models.ResearchNote(title="Firm-wide", created_by="R. Shah"),
    ])
    db.commit()

    response = client.get(f"/api/research-notes?client_id={record.id}", headers=headers)

    assert [n["title"] for n in response.json()] == ["For Meera"]


def test_client_only_sees_own_notes_ignoring_query(client, db, as_role, make_client_record):
    mine = make_client_record(name="Meera Kulkarni")
    other = make_client_record(name="Arjun Verma")
    _, headers = as_role("client", client_id=mine.id)
    db.add_all([
        models.ResearchNote(title="Mine", created_by="R. Shah", client_id=mine.id),
        models.ResearchNote(title="Theirs", created_by="R. Shah", client_id=other.id),
        models.ResearchNote(title="Unassigned", created_by="R. Shah"),
    ])
    db.commit()

    response = client.get(f"/api/research-notes?client_id={other.id}", headers=headers)

    assert [n["title"] for n in response.json()] == ["Mine"]


def test_create_note_stamps_author(client, as_role, make_client_record):
    user, headers = as_role("analyst")
    record = make_client_record()

    response = client.post("/api/research-notes", headers=headers, json={
        "title": "Energy outlook", "body": "Crude tailwinds", "client_id": record.id,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["created_by"] == user.name
    assert body["client_id"] == record.id
    assert body["call_id"] is None


def test_create_note_forbidden_for_clients(client, as_role):
    _, headers = as_role("client")

    response = client.post("/api/research-notes", headers=headers, json={"title": "Nope"})

    assert response.status_code == 403
