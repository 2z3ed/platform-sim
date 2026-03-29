import pytest
from fastapi.testclient import TestClient


def test_healthz(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_run(client: TestClient):
    response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["platform"] == "taobao"
    assert data["status"] == "created"
    assert data["current_step"] == 0
    assert "run_id" in data
    assert "run_code" in data


def test_get_run(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    get_response = client.get(f"/official-sim/runs/{run_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["run_id"] == run_id
    assert data["platform"] == "taobao"


def test_get_run_not_found(client: TestClient):
    response = client.get("/official-sim/runs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_advance_run(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    advance_response = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance_response.status_code == 200
    data = advance_response.json()
    assert data["previous_step"] == 0
    assert data["current_step"] == 1
    assert data["status"] == "running"
    assert "event_id" in data


def test_advance_run_creates_event(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    client.post(f"/official-sim/runs/{run_id}/advance", json={})

    events_response = client.get(f"/official-sim/runs/{run_id}/events")
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "step_advance"
    assert events[0]["step_no"] == 1


def test_advance_run_creates_snapshot(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    client.post(f"/official-sim/runs/{run_id}/advance", json={})

    snapshots_response = client.get(f"/official-sim/runs/{run_id}/snapshots")
    assert snapshots_response.status_code == 200
    snapshots = snapshots_response.json()
    assert len(snapshots) == 1
    assert snapshots[0]["step_no"] == 1
    assert snapshots[0]["auth_state"]["platform"] == "taobao"


def test_advance_run_multiple_steps(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    for expected_step in [1, 2, 3]:
        advance_response = client.post(f"/official-sim/runs/{run_id}/advance", json={})
        data = advance_response.json()
        assert data["current_step"] == expected_step

    events_response = client.get(f"/official-sim/runs/{run_id}/events")
    assert len(events_response.json()) == 3

    snapshots_response = client.get(f"/official-sim/runs/{run_id}/snapshots")
    assert len(snapshots_response.json()) == 3


def test_advance_run_cannot_advance_completed_run(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    response = client.post(
        f"/official-sim/runs/{run_id}/advance",
        json={},
    )
    assert response.status_code == 200


def test_list_events_empty(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    events_response = client.get(f"/official-sim/runs/{run_id}/events")
    assert events_response.status_code == 200
    assert events_response.json() == []


def test_list_snapshots_empty(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    snapshots_response = client.get(f"/official-sim/runs/{run_id}/snapshots")
    assert snapshots_response.status_code == 200
    assert snapshots_response.json() == []
