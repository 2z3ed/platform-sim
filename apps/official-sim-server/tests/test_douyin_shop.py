import pytest
from fastapi.testclient import TestClient


def test_douyin_full_flow(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "full_flow",
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run_id"]

    advance1 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance1.status_code == 200
    assert advance1.json()["current_step"] == 1

    advance2 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance2.status_code == 200
    assert advance2.json()["current_step"] == 2

    advance3 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance3.status_code == 200
    assert advance3.json()["current_step"] == 3

    advance4 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance4.status_code == 200
    assert advance4.json()["current_step"] == 4


def test_douyin_basic_shipped_to_confirmed(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "basic_shipped_to_confirmed",
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run_id"]

    advance = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance.status_code == 200
    assert advance.json()["current_step"] == 1


def test_douyin_refund_flow(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "refund_flow",
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run_id"]

    advance1 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance1.status_code == 200

    artifacts = client.get(f"/official-sim/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    assert len(artifacts.json()) >= 1

    advance2 = client.post(f"/official-sim/runs/{run_id}/advance", json={})
    assert advance2.status_code == 200

    pushes = client.get(f"/official-sim/runs/{run_id}/pushes")
    assert pushes.status_code == 200
    push_list = pushes.json()
    assert len(push_list) >= 1


def test_douyin_advance_creates_push(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "basic_paid_to_shipped",
        },
    )
    run_id = create_response.json()["run_id"]

    client.post(f"/official-sim/runs/{run_id}/advance", json={})

    pushes_response = client.get(f"/official-sim/runs/{run_id}/pushes")
    assert pushes_response.status_code == 200
    pushes = pushes_response.json()
    assert len(pushes) >= 1
    assert pushes[0]["platform"] == "douyin_shop"


def test_douyin_scenario_in_metadata(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "full_flow",
        },
    )
    run_id = create_response.json()["run_id"]

    run_response = client.get(f"/official-sim/runs/{run_id}")
    run_data = run_response.json()
    assert run_data["metadata"]["scenario_name"] == "full_flow"


def test_douyin_invalid_signature_error(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "basic_paid_to_shipped",
        },
    )
    run_id = create_response.json()["run_id"]

    inject_response = client.post(
        f"/official-sim/runs/{run_id}/inject-error",
        json={"error_code": "invalid_signature"},
    )
    assert inject_response.status_code == 200
    data = inject_response.json()
    assert data["error_code"] == "invalid_signature"
    assert data["http_status"] == 403


def test_douyin_permission_denied_error(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "full_flow",
        },
    )
    run_id = create_response.json()["run_id"]

    inject_response = client.post(
        f"/official-sim/runs/{run_id}/inject-error",
        json={"error_code": "permission_denied"},
    )
    assert inject_response.status_code == 200
    data = inject_response.json()
    assert data["error_code"] == "permission_denied"
    assert data["http_status"] == 403


def test_douyin_duplicate_push_error(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "basic_paid_to_shipped",
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


def test_douyin_token_expired_error(client: TestClient):
    create_response = client.post(
        "/official-sim/runs",
        json={
            "platform": "douyin_shop",
            "scenario_name": "basic_paid_to_shipped",
        },
    )
    run_id = create_response.json()["run_id"]

    inject_response = client.post(
        f"/official-sim/runs/{run_id}/inject-error",
        json={"error_code": "token_expired"},
    )
    assert inject_response.status_code == 200
    data = inject_response.json()
    assert data["error_code"] == "token_expired"
    assert data["http_status"] == 401
    assert data["retryable"] is True
