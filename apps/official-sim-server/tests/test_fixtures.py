import json
import os
from pathlib import Path
from typing import Dict, Any

import pytest


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_json_fixture(platform: str, category: str, filename: str) -> Dict[str, Any]:
    path = FIXTURES_DIR / platform / category / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_fixture_files() -> list:
    fixtures = []
    for platform_dir in FIXTURES_DIR.iterdir():
        if not platform_dir.is_dir():
            continue
        platform = platform_dir.name
        for category_dir in platform_dir.iterdir():
            if not category_dir.is_dir():
                continue
            category = category_dir.name
            for fixture_file in category_dir.glob("*.json"):
                fixtures.append((platform, category, fixture_file.name))
    return fixtures


def get_all_json_files() -> list:
    fixtures = []
    for platform_dir in FIXTURES_DIR.rglob("*"):
        if platform_dir.is_file() and platform_dir.suffix == ".json":
            rel_path = platform_dir.relative_to(FIXTURES_DIR)
            parts = rel_path.parts
            if len(parts) == 3:
                platform, category, filename = parts
                fixtures.append((platform, category, filename))
    return fixtures


REQUIRED_FIELDS = ["platform", "fixture_type", "scenario_key", "description", "metadata"]
METADATA_REQUIRED_FIELDS = ["version", "created_at"]


class TestFixtureFilesExist:
    def test_fixtures_directory_exists(self):
        assert FIXTURES_DIR.exists(), f"Fixtures directory {FIXTURES_DIR} does not exist"

    def test_taobao_fixtures_exist(self):
        taobao_dir = FIXTURES_DIR / "taobao"
        assert taobao_dir.exists()
        assert (taobao_dir / "success").exists()
        assert (taobao_dir / "edge_case").exists()
        assert (taobao_dir / "error_case").exists()

    def test_douyin_shop_fixtures_exist(self):
        douyin_dir = FIXTURES_DIR / "douyin_shop"
        assert douyin_dir.exists()
        assert (douyin_dir / "success").exists()
        assert (douyin_dir / "edge_case").exists()
        assert (douyin_dir / "error_case").exists()

    def test_wecom_kf_fixtures_exist(self):
        wecom_dir = FIXTURES_DIR / "wecom_kf"
        assert wecom_dir.exists()
        assert (wecom_dir / "success").exists()
        assert (wecom_dir / "edge_case").exists()
        assert (wecom_dir / "error_case").exists()


class TestFixtureSchema:
    @pytest.mark.parametrize("platform,category,filename", get_all_json_files())
    def test_fixture_has_required_fields(self, platform: str, category: str, filename: str):
        fixture = load_json_fixture(platform, category, filename)
        for field in REQUIRED_FIELDS:
            assert field in fixture, f"{platform}/{category}/{filename} missing required field: {field}"

    @pytest.mark.parametrize("platform,category,filename", get_all_json_files())
    def test_fixture_metadata_has_required_fields(self, platform: str, category: str, filename: str):
        fixture = load_json_fixture(platform, category, filename)
        metadata = fixture.get("metadata", {})
        for field in METADATA_REQUIRED_FIELDS:
            assert field in metadata, f"{platform}/{category}/{filename} metadata missing required field: {field}"

    @pytest.mark.parametrize("platform,category,filename", get_all_json_files())
    def test_fixture_platform_matches_path(self, platform: str, category: str, filename: str):
        fixture = load_json_fixture(platform, category, filename)
        assert fixture["platform"] == platform, f"{platform}/{category}/{filename} platform mismatch"


class TestFixtureConsistency:
    def test_taobao_success_fixtures(self):
        success_dir = FIXTURES_DIR / "taobao" / "success"
        expected_files = [
            "trade_wait_pay.json",
            "trade_wait_ship.json",
            "trade_shipped.json",
            "trade_finished.json",
            "refund_requested.json",
            "refund_refunded.json",
        ]
        actual_files = [f.name for f in success_dir.glob("*.json")]
        for expected in expected_files:
            assert expected in actual_files, f"Missing taobao success fixture: {expected}"

    def test_taobao_error_fixtures(self):
        error_dir = FIXTURES_DIR / "taobao" / "error_case"
        expected_files = [
            "token_expired.json",
            "duplicate_push.json",
            "out_of_order_push.json",
            "trade_not_found.json",
        ]
        actual_files = [f.name for f in error_dir.glob("*.json")]
        for expected in expected_files:
            assert expected in actual_files, f"Missing taobao error fixture: {expected}"

    def test_douyin_shop_success_fixtures(self):
        success_dir = FIXTURES_DIR / "douyin_shop" / "success"
        expected_files = [
            "order_created.json",
            "order_paid.json",
            "order_shipped.json",
            "order_confirmed.json",
            "order_completed.json",
            "refund_applied.json",
            "refund_approved.json",
        ]
        actual_files = [f.name for f in success_dir.glob("*.json")]
        for expected in expected_files:
            assert expected in actual_files, f"Missing douyin_shop success fixture: {expected}"

    def test_douyin_shop_error_fixtures(self):
        error_dir = FIXTURES_DIR / "douyin_shop" / "error_case"
        expected_files = [
            "invalid_signature.json",
            "timestamp_out_of_window.json",
        ]
        actual_files = [f.name for f in error_dir.glob("*.json")]
        for expected in expected_files:
            assert expected in actual_files, f"Missing douyin_shop error fixture: {expected}"

    def test_wecom_kf_success_fixtures(self):
        success_dir = FIXTURES_DIR / "wecom_kf" / "success"
        expected_files = [
            "conversation_pending.json",
            "conversation_in_session.json",
            "conversation_closed.json",
        ]
        actual_files = [f.name for f in success_dir.glob("*.json")]
        for expected in expected_files:
            assert expected in actual_files, f"Missing wecom_kf success fixture: {expected}"

    def test_wecom_kf_error_fixtures(self):
        error_dir = FIXTURES_DIR / "wecom_kf" / "error_case"
        expected_files = [
            "msg_code_expired.json",
            "conversation_closed_error.json",
        ]
        actual_files = [f.name for f in error_dir.glob("*.json")]
        for expected in expected_files:
            assert expected in actual_files, f"Missing wecom_kf error fixture: {expected}"


class TestErrorFixtures:
    @pytest.mark.parametrize("platform,category,filename", get_all_json_files())
    def test_error_fixtures_have_error_code(self, platform: str, category: str, filename: str):
        fixture = load_json_fixture(platform, category, filename)
        if fixture.get("fixture_type") == "error":
            assert "error_code" in fixture, f"{platform}/{category}/{filename} is error type but missing error_code"
            assert "http_status" in fixture, f"{platform}/{category}/{filename} is error type but missing http_status"
            assert "retryable" in fixture, f"{platform}/{category}/{filename} is error type but missing retryable"
            assert "response_body" in fixture, f"{platform}/{category}/{filename} is error type but missing response_body"
