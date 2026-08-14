from datetime import datetime, timedelta

import models


def _cards(response):
    return {card["label"]: card for card in response.json()["cards"]}


def test_summary_for_firm_user_includes_ops_cards(client, db, as_role, make_call, make_client_record):
    _, headers = as_role("admin")
    make_call(status="ACTIVE")
    make_call(status="TARGET_HIT", result_pct=6.0)
    make_call(status="SL_HIT", result_pct=-2.0)
    make_client_record(name="Meera Kulkarni", status="Active")
    make_client_record(name="Devika Iyer", status="Dormant")
    db.add_all([models.Task(title="Call client", status="TODO"),
                models.Task(title="File report", status="DONE")])
    db.commit()

    response = client.get("/api/dashboard/summary", headers=headers)

    assert response.status_code == 200
    cards = _cards(response)
    assert cards["Active Calls"]["value"] == 1
    assert cards["Total Calls (All-Time)"]["value"] == 3
    assert cards["Win Rate"]["value"] == "50.0%"
    assert cards["Win Rate"]["trend"] == "up"
    assert cards["Avg Result / Call"]["value"] == "2.0%"
    assert cards["Active Clients"]["value"] == "1/2"
    assert cards["Open Tasks"]["value"] == 1
    assert response.json()["generated_at"].endswith("Z")


def test_summary_marks_weak_win_rate_and_negative_average(client, as_role, make_call):
    _, headers = as_role("analyst")
    make_call(status="SL_HIT", result_pct=-5.0)

    cards = _cards(client.get("/api/dashboard/summary", headers=headers))

    assert cards["Win Rate"]["value"] == "0.0%"
    assert cards["Win Rate"]["trend"] == "down"
    assert cards["Avg Result / Call"]["trend"] == "down"


def test_summary_with_no_data_reports_zeroes(client, as_role):
    _, headers = as_role("staff")

    cards = _cards(client.get("/api/dashboard/summary", headers=headers))

    assert cards["Active Calls"]["value"] == 0
    assert cards["Win Rate"]["value"] == "0.0%"
    assert cards["Avg Result / Call"]["value"] == "0.0%"


def test_summary_for_client_shows_portfolio_cards_only(client, as_role, make_client_record):
    record = make_client_record(name="Meera Kulkarni", tier="Institutional", aum=8_450_000)
    _, headers = as_role("client", client_id=record.id)

    cards = _cards(client.get("/api/dashboard/summary", headers=headers))

    assert "Open Tasks" not in cards
    assert "Active Clients" not in cards
    assert cards["Portfolio AUM"]["value"] == "₹8,450,000"
    assert cards["Account Tier"]["value"] == "Institutional"


def test_summary_for_client_without_linked_record_omits_portfolio_cards(client, as_role):
    _, headers = as_role("client")

    cards = _cards(client.get("/api/dashboard/summary", headers=headers))

    assert set(cards) == {"Active Calls", "Win Rate", "Avg Result / Call", "Total Calls (All-Time)"}


def test_call_performance_series_is_cumulative_and_windowed(client, as_role, make_call):
    _, headers = as_role("admin")
    now = datetime.utcnow()
    make_call(symbol="OLD", status="TARGET_HIT", result_pct=99.0,
              created_at=now - timedelta(days=40))
    make_call(symbol="A", status="TARGET_HIT", result_pct=3.0, created_at=now - timedelta(days=3))
    make_call(symbol="B", status="ACTIVE", created_at=now - timedelta(days=2))
    make_call(symbol="C", status="SL_HIT", result_pct=-1.5, created_at=now - timedelta(days=1))

    series = client.get("/api/dashboard/call-performance", headers=headers).json()["series"]

    assert [point["cumulative_pct"] for point in series] == [3.0, 3.0, 1.5]


def test_call_performance_empty_series(client, as_role):
    _, headers = as_role("admin")

    assert client.get("/api/dashboard/call-performance", headers=headers).json() == {"series": []}


def test_notifications_filters_by_audience_role(client, db, as_role):
    _, headers = as_role("analyst")
    db.add_all([
        models.Notification(message="Everyone", level="info"),
        models.Notification(message="Analysts only", audience_role="analyst", level="warning"),
        models.Notification(message="Clients only", audience_role="client"),
    ])
    db.commit()

    items = client.get("/api/dashboard/notifications", headers=headers).json()["notifications"]

    assert {n["message"] for n in items} == {"Everyone", "Analysts only"}
    assert all(n["created_at"].endswith("Z") for n in items)


def test_notifications_caps_at_twenty(client, db, as_role):
    _, headers = as_role("staff")
    db.add_all([models.Notification(message=f"note {i}") for i in range(25)])
    db.commit()

    items = client.get("/api/dashboard/notifications", headers=headers).json()["notifications"]

    assert len(items) == 20


def test_recent_updates_merges_sources_for_firm_users(client, db, as_role, make_call):
    _, headers = as_role("admin")
    make_call(symbol="RELIANCE", direction="LONG")
    db.add(models.NewsItem(category="MARKET", title="Nifty ends higher"))
    db.add(models.ResearchNote(title="Energy sector note", created_by="Rohan Shah"))
    db.commit()

    updates = client.get("/api/dashboard/recent-updates", headers=headers).json()["updates"]

    by_type = {u["type"]: u for u in updates}
    assert set(by_type) == {"call", "news", "note"}
    assert by_type["call"]["title"] == "LONG call opened — RELIANCE"
    assert by_type["note"]["meta"] == "Rohan Shah"


def test_recent_updates_hides_research_notes_from_clients(client, db, as_role, make_call):
    _, headers = as_role("client")
    make_call()
    db.add(models.ResearchNote(title="Internal note", created_by="Rohan Shah"))
    db.commit()

    updates = client.get("/api/dashboard/recent-updates", headers=headers).json()["updates"]

    assert {u["type"] for u in updates} == {"call"}


def test_recent_updates_returns_at_most_ten_items(client, db, as_role, make_call):
    _, headers = as_role("admin")
    for i in range(6):
        make_call(symbol=f"S{i}")
    db.add_all([models.NewsItem(category="MARKET", title=f"news {i}") for i in range(6)])
    db.add_all([models.ResearchNote(title=f"note {i}", created_by="R") for i in range(6)])
    db.commit()

    updates = client.get("/api/dashboard/recent-updates", headers=headers).json()["updates"]

    assert len(updates) == 10
    timestamps = [u["timestamp"] for u in updates]
    assert timestamps == sorted(timestamps, reverse=True)
