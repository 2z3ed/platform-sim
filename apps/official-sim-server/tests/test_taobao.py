import pytest
from fastapi.testclient import TestClient


def test_taobao_full_flow(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "full_flow",
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run_id"]

    advance1 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance1.status_code == 200
    assert advance1.json()["current_step"] == 1

    artifacts1 = client.get(f"/official-sim/runs/{run_id}/artifacts")
    assert artifacts1.status_code == 200
    assert len(artifacts1.json()) >= 1

    advance2 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance2.status_code == 200
    assert advance2.json()["current_step"] == 2

    advance3 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance3.status_code == 200
    assert advance3.json()["current_step"] == 3


def test_taobao_wait_ship_basic(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run_id"]

    advance = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance.status_code == 200

    artifacts = client.get(f"/official-sim/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    artifact_data = artifacts.json()
    assert len(artifact_data) >= 1

    pushes = client.get(f"/official-sim/runs/{run_id}/pushes")
    assert pushes.status_code == 200


def test_taobao_advance_creates_push(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    client.post(f"/official-sim/runs/{run_id}/advance", json={})

    pushes_response = client.get(f"/official-sim/runs/{run_id}/pushes")
    assert pushes_response.status_code == 200
    pushes = pushes_response.json()
    assert len(pushes) >= 1
    assert pushes[0]["platform"] == "taobao"


def test_taobao_shipped_to_finished(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "shipped_to_finished",
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run_id"]

    advance = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance.status_code == 200
    assert advance.json()["current_step"] == 1

    artifacts = client.get(f"/official-sim/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200


def test_taobao_scenario_in_metadata(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    run_response = client.get(f"/official-sim/runs/{run_id}")
    run_data = run_response.json()
    assert run_data["metadata"]["scenario_name"] == "wait_ship_basic"


def test_taobao_duplicate_push_error(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    inject_response = client.post(
        f"/official-sim/runs/{run_id}/inject-error",
        json={"error_code": "duplicate_push"},
    )
    assert inject_response.status_code == 200
    data = inject_response.json()
    assert data["error_code"] == "duplicate_push"
    assert data["http_status"] == 409


def test_taobao_out_of_order_push_error(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "taobao",
            "scenario_name": "wait_ship_basic",
        },
    )
    run_id = create_response.json()["run_id"]

    inject_response = client.post(
        f"/official-sim/runs/{run_id}/inject-error",
        json={"error_code": "out_of_order_push"},
    )
    assert inject_response.status_code == 200
    data = inject_response.json()
    assert data["error_code"] == "out_of_order_push"
    assert data["http_status"] == 400
    assert data["retryable"] is True


def test_taobao_artifact_has_order_payload(client: TestClient):
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

    artifacts_response = client.get(f"/official-sim/runs/{run_id}/artifacts?step_no=2")
    artifacts = artifacts_response.json()
    assert len(artifacts) >= 1
