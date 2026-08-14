from datetime import datetime, timedelta

import models


def _seed_news(db):
    now = datetime.utcnow()
    db.add_all([
        models.NewsItem(category="MARKET", title="Nifty ends higher", published_at=now),
        models.NewsItem(category="COMPANY", title="TCS wins deal",
                        published_at=now - timedelta(hours=1)),
        models.NewsItem(category="FIRM", title="Desk note",
                        published_at=now - timedelta(hours=2)),
    ])
    db.commit()


def test_list_news_returns_newest_first(client, as_role, db):
    _, headers = as_role("client")
    _seed_news(db)

    response = client.get("/api/news", headers=headers)

    assert response.status_code == 200
    assert [n["title"] for n in response.json()] == ["Nifty ends higher", "TCS wins deal", "Desk note"]


def test_list_news_filters_by_case_insensitive_category(client, as_role, db):
    _, headers = as_role("client")
    _seed_news(db)

    response = client.get("/api/news?category=company", headers=headers)

    assert [n["category"] for n in response.json()] == ["COMPANY"]


def test_list_news_honours_limit(client, as_role, db):
    _, headers = as_role("client")
    _seed_news(db)

    response = client.get("/api/news?limit=2", headers=headers)

    assert len(response.json()) == 2


def test_list_news_requires_authentication(client):
    assert client.get("/api/news").status_code == 401


def test_create_news_stamps_author(client, as_role):
    user, headers = as_role("staff")

    response = client.post("/api/news", headers=headers, json={
        "category": "FIRM", "title": "Compliance update", "body": "New SEBI circular",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["created_by"] == user.name
    assert body["source"] == "DV Finance Desk"


def test_create_news_forbidden_for_clients(client, as_role):
    _, headers = as_role("client")

    response = client.post("/api/news", headers=headers,
                           json={"category": "MARKET", "title": "Nope"})

    assert response.status_code == 403
