import csv
import io


def _rows(response):
    return list(csv.DictReader(io.StringIO(response.text)))


def test_export_calls_returns_csv_attachment(client, as_role, make_call):
    _, headers = as_role("client")
    make_call(symbol="RELIANCE", sector="Energy", status="TARGET_HIT", result_pct=6.0)

    response = client.get("/api/reports/export?type=calls", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == \
        "attachment; filename=dvfinance_calls_report.csv"
    rows = _rows(response)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "RELIANCE"
    assert rows[0]["result_pct"] == "6.0"


def test_export_clients_for_firm_users(client, as_role, make_client_record):
    _, headers = as_role("analyst")
    make_client_record(name="Meera Kulkarni", tier="Institutional", aum=8_450_000)

    response = client.get("/api/reports/export?type=clients", headers=headers)

    assert response.status_code == 200
    rows = _rows(response)
    assert rows[0]["name"] == "Meera Kulkarni"
    assert rows[0]["tier"] == "Institutional"


def test_export_clients_forbidden_for_client_role(client, as_role):
    _, headers = as_role("client")

    response = client.get("/api/reports/export?type=clients", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Not permitted"


def test_export_performance_only_includes_scored_calls(client, as_role, make_call):
    _, headers = as_role("admin")
    make_call(symbol="TCS", status="TARGET_HIT", result_pct=4.0)
    make_call(symbol="ONGC", status="ACTIVE")

    rows = _rows(client.get("/api/reports/export?type=performance", headers=headers))

    assert [row["symbol"] for row in rows] == ["TCS"]


def test_export_rejects_unknown_type(client, as_role):
    _, headers = as_role("admin")

    response = client.get("/api/reports/export?type=magic", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "type must be one of: calls, clients, performance"


def test_export_requires_type_parameter(client, as_role):
    _, headers = as_role("admin")

    assert client.get("/api/reports/export", headers=headers).status_code == 422


def test_export_with_no_rows_returns_empty_csv(client, as_role):
    _, headers = as_role("admin")

    response = client.get("/api/reports/export?type=calls", headers=headers)

    assert response.status_code == 200
    assert response.text.strip() == ""


def test_export_requires_authentication(client):
    assert client.get("/api/reports/export?type=calls").status_code == 401
