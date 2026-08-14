import io
import os

import models
from engagement import documents_router


def test_list_documents_returns_everything_for_firm_users(client, db, as_role):
    _, headers = as_role("staff")
    db.add_all([
        models.Document(filename="research.pdf", category="Research", uploaded_by="R. Shah"),
        models.Document(filename="kyc.pdf", category="Client", uploaded_by="R. Shah", client_id=7),
    ])
    db.commit()

    response = client.get("/api/documents", headers=headers)

    assert response.status_code == 200
    assert {d["filename"] for d in response.json()} == {"research.pdf", "kyc.pdf"}


def test_list_documents_scopes_clients_to_own_and_general(client, db, as_role, make_client_record):
    mine = make_client_record(name="Meera Kulkarni")
    other = make_client_record(name="Arjun Verma")
    _, headers = as_role("client", client_id=mine.id)
    db.add_all([
        models.Document(filename="mine.pdf", category="Client", uploaded_by="R. Shah", client_id=mine.id),
        models.Document(filename="theirs.pdf", category="Client", uploaded_by="R. Shah", client_id=other.id),
        models.Document(filename="brochure.pdf", category="General", uploaded_by="R. Shah"),
        models.Document(filename="internal.pdf", category="Compliance", uploaded_by="R. Shah"),
    ])
    db.commit()

    response = client.get("/api/documents", headers=headers)

    assert {d["filename"] for d in response.json()} == {"mine.pdf", "brochure.pdf"}


def test_register_document_stores_metadata_only(client, as_role):
    user, headers = as_role("analyst")

    response = client.post("/api/documents", headers=headers, json={
        "filename": "sector-note.pdf", "category": "Research", "size_kb": 128.5,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["uploaded_by"] == user.name
    assert body["size_kb"] == 128.5
    assert body["client_id"] is None


def test_register_document_forbidden_for_clients(client, as_role):
    _, headers = as_role("client")

    response = client.post("/api/documents", headers=headers, json={"filename": "nope.pdf"})

    assert response.status_code == 403


def test_upload_document_writes_file_and_computes_size(client, as_role, tmp_path, monkeypatch):
    user, headers = as_role("admin")
    monkeypatch.setattr(documents_router, "UPLOAD_DIR", str(tmp_path))
    payload = b"x" * 2048

    response = client.post(
        "/api/documents/upload", headers=headers,
        files={"file": ("statement.csv", io.BytesIO(payload), "text/csv")},
        data={"category": "Client", "client_id": "3"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "statement.csv"
    assert body["category"] == "Client"
    assert body["client_id"] == 3
    assert body["size_kb"] == 2.0
    assert body["uploaded_by"] == user.name
    assert os.path.exists(tmp_path / "statement.csv")


def test_upload_document_defaults_category_to_general(client, as_role, tmp_path, monkeypatch):
    _, headers = as_role("staff")
    monkeypatch.setattr(documents_router, "UPLOAD_DIR", str(tmp_path))

    response = client.post(
        "/api/documents/upload", headers=headers,
        files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "General"
    assert body["client_id"] is None


def test_upload_document_forbidden_for_clients(client, as_role, tmp_path, monkeypatch):
    _, headers = as_role("client")
    monkeypatch.setattr(documents_router, "UPLOAD_DIR", str(tmp_path))

    response = client.post(
        "/api/documents/upload", headers=headers,
        files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 403
    assert not list(tmp_path.iterdir())
