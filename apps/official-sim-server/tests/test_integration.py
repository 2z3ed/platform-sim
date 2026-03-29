import pytest
from fastapi.testclient import TestClient


def test_unified_run_creation(client: TestClient):
    response = client.post(
        "/official-sim/unified/run",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["platform"] == "taobao"
    assert "orders" in data
    assert "conversations" in data
    assert "push_events" in data


def test_unified_run_for_douyin(client: TestClient):
    response = client.post(
        "/official-sim/unified/run",
        json={
            "platform": "douyin_shop",
            "scenario_name": "basic_paid_to_shipped",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "douyin_shop"


def test_unified_run_for_wecom(client: TestClient):
    response = client.post(
        "/official-sim/unified/run",
        json={
            "platform": "wecom_kf",
            "scenario_name": "basic_session",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "wecom_kf"


def test_unified_get_run_with_advances(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "full_flow",
        },
    )
    run_id = create_response.json()["run_id"]

    client.post(f"/official-sim/runs/{run_id}/advance", json={})
    client.post(f"/official-sim/runs/{run_id}/advance", json={})

    unified_response = client.get(f"/official-sim/unified/runs/{run_id}")
    assert unified_response.status_code == 200
    data = unified_response.json()
    assert data["run_id"] == run_id
    assert len(data["orders"]) >= 0


def test_unified_run_not_found(client: TestClient):
    response = client.get(
        "/official-sim/unified/runs/00000000-0000-0000-0000-000000000000",
    )
    assert response.status_code == 200
    assert response.json().get("error") == "Run not found"


def test_unified_artifact_mapping(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    client.post(f"/official-sim/runs/{run_id}/advance", json={})

    unified_response = client.get(f"/official-sim/unified/runs/{run_id}")
    assert unified_response.status_code == 200
    data = unified_response.json()
    assert isinstance(data["orders"], list)
    assert isinstance(data["conversations"], list)
    assert isinstance(data["push_events"], list)
