from datetime import datetime

import models
from dataframes import calls_dataframe


def test_calls_dataframe_empty_has_expected_columns(db):
    df = calls_dataframe(db)

    assert df.empty
    assert list(df.columns) == ["id", "symbol", "sector", "direction", "entry", "stop_loss",
                                "target", "status", "result_pct", "created_at", "closed_at"]


def test_calls_dataframe_maps_rows(db, make_call):
    make_call(symbol="TCS", sector="Technology", status="TARGET_HIT", result_pct=4.0)

    df = calls_dataframe(db)

    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "TCS"
    assert df.iloc[0]["result_pct"] == 4.0


def test_win_rate_with_no_closed_calls(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(status="ACTIVE")

    response = client.get("/api/analytics/win-rate", headers=headers)

    assert response.json() == {"win_rate_pct": 0.0, "wins": 0, "losses": 0, "total_closed": 0}


def test_win_rate_counts_only_target_and_sl_hits(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(status="TARGET_HIT", result_pct=5.0)
    make_call(status="TARGET_HIT", result_pct=3.0)
    make_call(status="SL_HIT", result_pct=-2.0)
    make_call(status="CLOSED", result_pct=1.0)
    make_call(status="ACTIVE")

    response = client.get("/api/analytics/win-rate", headers=headers)

    assert response.json() == {"win_rate_pct": 66.67, "wins": 2, "losses": 1, "total_closed": 3}


def test_accuracy_with_no_results(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(status="ACTIVE")

    response = client.get("/api/analytics/accuracy", headers=headers)

    assert response.json() == {"accuracy_pct": 0.0, "sample_size": 0,
                               "avg_result_pct": 0.0, "std_dev_pct": 0.0}


def test_accuracy_uses_all_scored_calls(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(status="TARGET_HIT", result_pct=6.0)
    make_call(status="CLOSED", result_pct=2.0)
    make_call(status="SL_HIT", result_pct=-4.0)
    make_call(status="ACTIVE")

    body = client.get("/api/analytics/accuracy", headers=headers).json()

    assert body["sample_size"] == 3
    assert body["accuracy_pct"] == 66.67
    assert body["avg_result_pct"] == 1.33
    assert body["std_dev_pct"] == 4.11


def test_accuracy_single_sample_has_zero_std_dev(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(status="TARGET_HIT", result_pct=6.0)

    body = client.get("/api/analytics/accuracy", headers=headers).json()

    assert body == {"accuracy_pct": 100.0, "sample_size": 1,
                    "avg_result_pct": 6.0, "std_dev_pct": 0.0}


def test_monthly_performance_empty(client, as_role):
    _, headers = as_role("client")

    assert client.get("/api/analytics/monthly-performance", headers=headers).json() == {"months": []}


def test_monthly_performance_groups_by_close_month(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(status="TARGET_HIT", result_pct=4.0,
              created_at=datetime(2024, 1, 5), closed_at=datetime(2024, 2, 10))
    make_call(status="SL_HIT", result_pct=-2.0,
              created_at=datetime(2024, 2, 1), closed_at=datetime(2024, 2, 20))
    # No closed_at -> falls back to created_at for bucketing.
    make_call(status="CLOSED", result_pct=1.5, created_at=datetime(2024, 3, 3))

    months = client.get("/api/analytics/monthly-performance", headers=headers).json()["months"]

    assert months == [
        {"month": "2024-02", "avg_result_pct": 1.0, "total_result_pct": 2.0, "calls": 2},
        {"month": "2024-03", "avg_result_pct": 1.5, "total_result_pct": 1.5, "calls": 1},
    ]


def test_sector_performance_empty(client, as_role):
    _, headers = as_role("client")

    assert client.get("/api/analytics/sector-performance", headers=headers).json() == {"sectors": []}


def test_sector_performance_without_any_results(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(sector="Energy", status="ACTIVE")

    sectors = client.get("/api/analytics/sector-performance", headers=headers).json()["sectors"]

    assert sectors == [{"sector": "Energy", "total_calls": 1,
                        "avg_result_pct": 0.0, "win_rate_pct": 0.0}]


def test_sector_performance_ranks_sectors_by_avg_result(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(sector="Technology", status="TARGET_HIT", result_pct=8.0)
    make_call(sector="Technology", status="SL_HIT", result_pct=-2.0)
    make_call(sector="Energy", status="TARGET_HIT", result_pct=1.0)
    make_call(sector="Railway", status="ACTIVE")  # no scored calls -> zero-filled

    sectors = client.get("/api/analytics/sector-performance", headers=headers).json()["sectors"]

    by_sector = {s["sector"]: s for s in sectors}
    assert [s["sector"] for s in sectors] == ["Technology", "Energy", "Railway"]
    assert by_sector["Technology"] == {"sector": "Technology", "total_calls": 2,
                                       "avg_result_pct": 3.0, "win_rate_pct": 50.0}
    assert by_sector["Railway"]["avg_result_pct"] == 0.0
    assert by_sector["Railway"]["win_rate_pct"] == 0.0


def test_call_history_empty(client, as_role):
    _, headers = as_role("client")

    assert client.get("/api/analytics/call-history", headers=headers).json() == {"history": []}


def test_call_history_accumulates_results_and_nulls_missing(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(symbol="A", status="TARGET_HIT", result_pct=3.0, created_at=datetime(2024, 1, 1))
    make_call(symbol="B", status="ACTIVE", created_at=datetime(2024, 1, 2))
    make_call(symbol="C", status="SL_HIT", result_pct=-1.0, created_at=datetime(2024, 1, 3))

    history = client.get("/api/analytics/call-history", headers=headers).json()["history"]

    assert [h["symbol"] for h in history] == ["A", "B", "C"]
    assert [h["cumulative_pct"] for h in history] == [3.0, 3.0, 2.0]
    assert history[1]["result_pct"] is None
    assert history[0]["created_at"] == "2024-01-01"


def test_call_history_limit_keeps_most_recent(client, as_role, make_call):
    _, headers = as_role("client")
    for day in range(1, 4):
        make_call(symbol=f"S{day}", created_at=datetime(2024, 1, day))

    history = client.get("/api/analytics/call-history?limit=2", headers=headers).json()["history"]

    assert [h["symbol"] for h in history] == ["S2", "S3"]


def test_client_engagement_requires_firm_role(client, as_role):
    _, headers = as_role("client")

    assert client.get("/api/analytics/client-engagement", headers=headers).status_code == 403


def test_client_engagement_without_clients(client, as_role):
    _, headers = as_role("admin")

    assert client.get("/api/analytics/client-engagement", headers=headers).json() == {"clients": []}


def test_client_engagement_scores_and_sorts(client, db, as_role, make_client_record):
    _, headers = as_role("admin")
    active = make_client_record(name="Meera Kulkarni")
    quiet = make_client_record(name="Devika Iyer")
    db.add_all([
        models.EngagementEvent(client_id=active.id, event_type="LOGIN"),
        models.EngagementEvent(client_id=active.id, event_type="MESSAGE"),
        models.EngagementEvent(client_id=active.id, event_type="DOWNLOAD"),
        models.EngagementEvent(client_id=quiet.id, event_type="LOGIN"),
    ])
    db.commit()

    clients = client.get("/api/analytics/client-engagement", headers=headers).json()["clients"]

    assert [c["client_name"] for c in clients] == ["Meera Kulkarni", "Devika Iyer"]
    assert clients[0]["engagement_score"] == 6  # 1 + 3 + 2
    assert clients[0]["total_events"] == 3
    assert clients[0]["breakdown"] == {"LOGIN": 1, "REPORT_VIEW": 0, "DOWNLOAD": 1, "MESSAGE": 1}
    assert clients[1]["engagement_score"] == 1


def test_client_engagement_zeroes_clients_without_events(client, as_role, make_client_record):
    _, headers = as_role("analyst")
    make_client_record(name="Priya Nair")

    clients = client.get("/api/analytics/client-engagement", headers=headers).json()["clients"]

    assert clients[0]["total_events"] == 0
    assert clients[0]["engagement_score"] == 0
    assert clients[0]["breakdown"] == {"LOGIN": 0, "REPORT_VIEW": 0, "DOWNLOAD": 0, "MESSAGE": 0}
