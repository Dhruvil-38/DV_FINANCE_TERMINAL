import models


def test_list_watchlist_is_sorted_by_symbol(client, as_role, db):
    _, headers = as_role("client")
    db.add_all([
        models.WatchlistItem(symbol="TCS", sector="Technology"),
        models.WatchlistItem(symbol="ONGC", sector="Energy"),
    ])
    db.commit()

    response = client.get("/api/market/watchlist", headers=headers)

    assert response.status_code == 200
    assert [item["symbol"] for item in response.json()] == ["ONGC", "TCS"]


def test_add_watchlist_stamps_creator(client, as_role):
    user, headers = as_role("staff")

    response = client.post("/api/market/watchlist", headers=headers, json={
        "symbol": "IRCTC", "sector": "Railway", "last_price": 812.55, "day_change_pct": 2.31,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "IRCTC"
    assert body["added_by"] == user.name


def test_add_watchlist_forbidden_for_clients(client, as_role):
    _, headers = as_role("client")

    response = client.post("/api/market/watchlist", headers=headers, json={"symbol": "TCS"})

    assert response.status_code == 403


def test_delete_watchlist_removes_row(client, as_role, db):
    _, headers = as_role("admin")
    item = models.WatchlistItem(symbol="TCS")
    db.add(item)
    db.commit()

    response = client.delete(f"/api/market/watchlist/{item.id}", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"deleted": item.id}
    assert db.query(models.WatchlistItem).count() == 0


def test_delete_missing_watchlist_item_returns_404(client, as_role):
    _, headers = as_role("admin")

    response = client.delete("/api/market/watchlist/999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Watchlist item not found"


def test_list_calls_filters_by_status_and_sector(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(symbol="RELIANCE", sector="Energy", status="ACTIVE")
    make_call(symbol="TCS", sector="Technology", status="TARGET_HIT")
    make_call(symbol="ONGC", sector="Energy", status="TARGET_HIT")

    all_calls = client.get("/api/market/calls", headers=headers).json()
    by_status = client.get("/api/market/calls?status_filter=TARGET_HIT", headers=headers).json()
    by_sector = client.get("/api/market/calls?sector=Energy", headers=headers).json()
    combined = client.get("/api/market/calls?status_filter=TARGET_HIT&sector=Energy",
                          headers=headers).json()

    assert len(all_calls) == 3
    assert {c["symbol"] for c in by_status} == {"TCS", "ONGC"}
    assert {c["symbol"] for c in by_sector} == {"RELIANCE", "ONGC"}
    assert [c["symbol"] for c in combined] == ["ONGC"]


def test_create_call_defaults_to_active(client, as_role):
    user, headers = as_role("analyst")

    response = client.post("/api/market/calls", headers=headers, json={
        "symbol": "HDFCBANK", "sector": "Finance", "direction": "LONG",
        "entry": 1652.9, "stop_loss": 1600.0, "target": 1750.0, "notes": "breakout",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["result_pct"] is None
    assert body["closed_at"] is None
    assert body["created_by"] == user.name


def test_create_call_rejects_unknown_direction(client, as_role):
    _, headers = as_role("analyst")

    response = client.post("/api/market/calls", headers=headers, json={
        "symbol": "HDFCBANK", "direction": "SIDEWAYS",
        "entry": 100.0, "stop_loss": 95.0, "target": 110.0,
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "direction must be LONG or SHORT"


def test_create_call_forbidden_for_staff(client, as_role):
    _, headers = as_role("staff")

    response = client.post("/api/market/calls", headers=headers, json={
        "symbol": "TCS", "direction": "LONG", "entry": 100.0, "stop_loss": 95.0, "target": 110.0,
    })

    assert response.status_code == 403


def test_update_call_applies_partial_update_without_closing(client, as_role, make_call):
    _, headers = as_role("admin")
    call = make_call()

    response = client.patch(f"/api/market/calls/{call.id}", headers=headers,
                            json={"notes": "trailing stop raised"})

    assert response.status_code == 200
    body = response.json()
    assert body["notes"] == "trailing stop raised"
    assert body["status"] == "ACTIVE"
    assert body["closed_at"] is None


def test_update_call_sets_closed_at_on_terminal_status(client, as_role, make_call):
    _, headers = as_role("admin")
    call = make_call()

    response = client.patch(f"/api/market/calls/{call.id}", headers=headers,
                            json={"status": "TARGET_HIT", "result_pct": 6.4})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "TARGET_HIT"
    assert body["result_pct"] == 6.4
    assert body["closed_at"] is not None


def test_update_call_cancelled_leaves_closed_at_empty(client, as_role, make_call):
    _, headers = as_role("admin")
    call = make_call()

    response = client.patch(f"/api/market/calls/{call.id}", headers=headers,
                            json={"status": "CANCELLED"})

    assert response.json()["closed_at"] is None


def test_update_missing_call_returns_404(client, as_role):
    _, headers = as_role("admin")

    response = client.patch("/api/market/calls/999", headers=headers, json={"status": "CLOSED"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Trade call not found"
