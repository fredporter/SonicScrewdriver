"""Tests for Sonic plan and dry-run apply engine."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from sonic.cli import cli
from sonic.lib.plan import (
    KNOWN_RECIPES,
    Plan,
    create_plan,
    dry_run_apply,
    validate_plan,
)


def test_create_plan_success():
    target_device = {
        "vendor": "Samsung",
        "model": "EVO 970",
        "bus": "nvme",
        "size_bytes": 500107862016,
        "serial": "S466NF0MA01234",
    }
    plan = create_plan(
        target_id="/dev/nvme0n1",
        recipe_id="udos-minimal-live",
        target_device=target_device,
    )
    assert plan.plan_id.startswith("plan-")
    assert plan.target_id == "/dev/nvme0n1"
    assert plan.recipe_id == "udos-minimal-live"
    assert plan.target_fingerprint["vendor"] == "Samsung"
    assert plan.target_fingerprint["bus"] == "nvme"
    assert len(plan.steps) > 0
    assert plan.dry_run_only is True
    assert plan.requires_confirmation is True


def test_create_plan_unknown_recipe():
    with pytest.raises(ValueError, match="Unknown recipe"):
        create_plan(target_id="/dev/sda", recipe_id="nonexistent-recipe")


def test_validate_plan_expiration():
    plan = create_plan(target_id="/dev/sda", recipe_id="udos-minimal-live")
    # Manually expire plan
    expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    plan_dict = plan.model_dump()
    plan_dict["expires_at"] = expired_time
    expired_plan = Plan.model_validate(plan_dict)

    errors = validate_plan(expired_plan)
    assert any("expired" in e for e in errors)


def test_validate_plan_fingerprint_mismatch():
    plan = create_plan(
        target_id="/dev/sda",
        recipe_id="udos-minimal-live",
        target_device={"size_bytes": 16000000000, "bus": "usb"},
    )
    # Different target size
    mismatched = {"target_id": "/dev/sda", "size_bytes": 32000000000, "bus": "usb"}
    errors = validate_plan(plan, current_fingerprint=mismatched)
    assert any("size mismatch" in e for e in errors)


def test_dry_run_apply_requires_confirmation():
    plan = create_plan(target_id="/dev/sdb", recipe_id="steam-headless")
    report = dry_run_apply(plan, confirmed=False)
    assert report.status == "confirmation_missing"
    assert report.safe_to_apply is False
    assert any("confirmation" in msg.lower() for msg in report.validation_messages)


def test_dry_run_apply_confirmed_success():
    plan = create_plan(target_id="/dev/sdb", recipe_id="steam-headless")
    report = dry_run_apply(plan, confirmed=True)
    assert report.status == "dry_run_success"
    assert report.safe_to_apply is True
    assert len(report.steps_simulated) == len(plan.steps)
    assert len(report.destructive_actions_prevented) > 0
    assert any("format_partitions" in a for a in report.destructive_actions_prevented)


def test_cli_plan_and_apply_dry_run(tmp_path: Path):
    runner = CliRunner()
    plan_file = tmp_path / "test_plan.json"

    # 1. Generate plan
    res_plan = runner.invoke(
        cli,
        [
            "plan",
            "--target",
            "/dev/sda",
            "--recipe",
            "udos-minimal-live",
            "--out",
            str(plan_file),
            "--json",
        ],
    )
    assert res_plan.exit_code == 0
    plan_json = json.loads(res_plan.output)
    assert plan_json["target_id"] == "/dev/sda"
    assert plan_file.exists()

    # 2. Apply without confirm -> fails with status confirmation_missing
    res_apply_fail = runner.invoke(
        cli,
        ["apply", "--plan", str(plan_file)],
    )
    assert res_apply_fail.exit_code == 1
    assert "CONFIRMATION_MISSING" in res_apply_fail.output

    # 3. Apply with confirm -> succeeds
    res_apply_success = runner.invoke(
        cli,
        ["apply", "--plan", str(plan_file), "--confirm", "--json"],
    )
    assert res_apply_success.exit_code == 0
    report_json = json.loads(res_apply_success.output)
    assert report_json["status"] == "dry_run_success"
    assert report_json["safe_to_apply"] is True
    assert len(report_json["destructive_actions_prevented"]) > 0
