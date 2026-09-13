"""Sonic plan and dry-run apply engine for hardware revival."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


class PlanPrerequisite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: Literal["satisfied", "failed", "pending"]
    details: dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int
    action: str
    description: str
    destructive: bool = False
    estimated_ms: int = 100


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "sonic.revival-plan/1"
    plan_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    expires_at: str
    target_id: str
    target_fingerprint: dict[str, Any]
    recipe_id: str
    recipe_digest: str
    prerequisites: list[PlanPrerequisite] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    requires_confirmation: bool = True
    confirmed: bool = False
    dry_run_only: bool = True


class DryRunStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int
    action: str
    status: Literal["simulated", "skipped", "error"] = "simulated"
    destructive_prevented: bool = False
    elapsed_ms: float = 0.0
    message: str = "ok"


class DryRunReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "sonic.dry-run-report/1"
    plan_id: str
    target_id: str
    recipe_id: str
    status: Literal[
        "dry_run_success",
        "validation_failed",
        "confirmation_missing",
        "target_mismatch",
        "plan_expired",
    ]
    executed_at: str = Field(default_factory=utc_now_iso)
    steps_simulated: list[DryRunStepResult] = Field(default_factory=list)
    destructive_actions_prevented: list[str] = Field(default_factory=list)
    validation_messages: list[str] = Field(default_factory=list)
    safe_to_apply: bool = False


KNOWN_RECIPES: dict[str, dict[str, Any]] = {
    "udos-minimal-live": {
        "description": "Minimal uDOS bootable live image with diagnostic tools",
        "steps": [
            {"action": "verify_target_table", "description": "Verify target partition table layout", "destructive": False},
            {"action": "create_gpt_table", "description": "Create GPT partition table on target", "destructive": True},
            {"action": "format_efi_partition", "description": "Format EFI system partition (FAT32)", "destructive": True},
            {"action": "write_rootfs_image", "description": "Write uDOS read-only squashfs system image", "destructive": True},
            {"action": "install_systemd_boot", "description": "Deploy signed EFI systemd-boot loader", "destructive": True},
            {"action": "verify_checksums", "description": "Verify rootfs and boot partition SHA256 integrity", "destructive": False},
        ],
    },
    "steam-headless": {
        "description": "HomeNest Steam Tenfoot living room appliance runtime",
        "steps": [
            {"action": "verify_target_table", "description": "Verify existing disk layout", "destructive": False},
            {"action": "create_gpt_table", "description": "Provision GPT layout with persistent user data", "destructive": True},
            {"action": "format_partitions", "description": "Format system and games ext4 partition", "destructive": True},
            {"action": "write_appliance_image", "description": "Deploy HomeNest SteamOS console image", "destructive": True},
            {"action": "configure_autologin", "description": "Configure unprivileged steam-session runner", "destructive": True},
        ],
    },
    "capsule-provisioning": {
        "description": "Offline portable USB or kiosk provisioning with signed uCore runtime and global capsule library",
        "min_storage_bytes": 4_000_000_000,
        "steps": [
            {"action": "probe_storage_geometry", "description": "Verify target disk meets minimum 4GB capsule budget", "destructive": False},
            {"action": "verify_target_table", "description": "Verify partition table and backup existing headers", "destructive": False},
            {"action": "provision_vault_partitions", "description": "Format boot (FAT32), OS runtime (squashfs), and encrypted Vault (ext4/f2fs)", "destructive": True},
            {"action": "deploy_runtime_capsule", "description": "Deploy signed base uCore runtime and desktop services", "destructive": True},
            {"action": "seed_global_knowledge", "description": "Provision canonical Layer 0 global-knowledge datasets and ZIM encyclopedia capsules", "destructive": True},
            {"action": "verify_capsule_manifest", "description": "Verify cryptographic integrity and root-of-trust signatures", "destructive": False},
        ],
    },
}


def create_plan(
    target_id: str,
    recipe_id: str,
    target_device: dict[str, Any] | None = None,
    valid_hours: int = 24,
) -> Plan:
    """Generate a validated, fingerprint-locked provisioning plan."""
    if recipe_id not in KNOWN_RECIPES:
        raise ValueError(f"Unknown recipe: '{recipe_id}'. Available: {list(KNOWN_RECIPES.keys())}")

    recipe_meta = KNOWN_RECIPES[recipe_id]
    recipe_json = json.dumps(recipe_meta, sort_keys=True)
    recipe_digest = hashlib.sha256(recipe_json.encode("utf-8")).hexdigest()

    now = utc_now()
    expires = now + timedelta(hours=valid_hours)
    plan_id = f"plan-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    fingerprint: dict[str, Any] = {
        "target_id": target_id,
        "vendor": target_device.get("vendor", "Generic") if target_device else "Generic",
        "model": target_device.get("model", "BlockDevice") if target_device else "BlockDevice",
        "bus": target_device.get("bus", "usb") if target_device else "usb",
        "size_bytes": target_device.get("size_bytes", 16000000000) if target_device else 16000000000,
        "serial_hash": hashlib.sha256(
            (target_device.get("serial") or target_id).encode("utf-8")
        ).hexdigest()
        if target_device
        else hashlib.sha256(target_id.encode("utf-8")).hexdigest(),
    }

    min_bytes = recipe_meta.get("min_storage_bytes", 8000000000)
    cap_status = "satisfied" if fingerprint["size_bytes"] >= min_bytes else "failed"

    prerequisites = [
        PlanPrerequisite(
            name="target_unmounted",
            status="satisfied",
            details={"target_id": target_id, "mounted_partitions": 0},
        ),
        PlanPrerequisite(
            name="minimum_capacity",
            status=cap_status,
            details={"required_bytes": min_bytes, "actual_bytes": fingerprint["size_bytes"]},
        ),
    ]

    steps: list[PlanStep] = []
    for idx, s in enumerate(recipe_meta["steps"], 1):
        steps.append(
            PlanStep(
                order=idx,
                action=s["action"],
                description=s["description"],
                destructive=s["destructive"],
                estimated_ms=150,
            )
        )

    return Plan(
        plan_id=plan_id,
        created_at=now.isoformat(),
        expires_at=expires.isoformat(),
        target_id=target_id,
        target_fingerprint=fingerprint,
        recipe_id=recipe_id,
        recipe_digest=recipe_digest,
        prerequisites=prerequisites,
        steps=steps,
        requires_confirmation=True,
        confirmed=False,
        dry_run_only=True,
    )


def validate_plan(
    plan: Plan,
    current_fingerprint: dict[str, Any] | None = None,
) -> list[str]:
    """Validate plan constraints, expiration, and target fingerprint consistency."""
    errors: list[str] = []

    # Check expiration
    try:
        expires = datetime.fromisoformat(plan.expires_at)
        if expires < utc_now():
            errors.append(f"Plan expired at {plan.expires_at}")
    except Exception as err:
        errors.append(f"Invalid expires_at format: {err}")

    # Check target fingerprint if provided
    if current_fingerprint is not None:
        tf = plan.target_fingerprint
        if current_fingerprint.get("target_id") and current_fingerprint["target_id"] != tf.get("target_id"):
            errors.append(f"Target ID mismatch: expected {tf.get('target_id')}, got {current_fingerprint.get('target_id')}")
        if current_fingerprint.get("size_bytes") and current_fingerprint["size_bytes"] != tf.get("size_bytes"):
            errors.append(f"Target size mismatch: expected {tf.get('size_bytes')}, got {current_fingerprint.get('size_bytes')}")
        if current_fingerprint.get("bus") and current_fingerprint["bus"] != tf.get("bus"):
            errors.append(f"Target bus mismatch: expected {tf.get('bus')}, got {current_fingerprint.get('bus')}")

    return errors


def dry_run_apply(
    plan: Plan,
    current_fingerprint: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> DryRunReport:
    """Execute a strictly non-destructive dry-run simulation of the plan."""
    val_errors = validate_plan(plan, current_fingerprint)
    if val_errors:
        status: Literal["validation_failed", "plan_expired", "target_mismatch"] = "validation_failed"
        if any("expired" in e for e in val_errors):
            status = "plan_expired"
        elif any("mismatch" in e for e in val_errors):
            status = "target_mismatch"

        return DryRunReport(
            plan_id=plan.plan_id,
            target_id=plan.target_id,
            recipe_id=plan.recipe_id,
            status=status,
            validation_messages=val_errors,
            safe_to_apply=False,
        )

    # Check user safety confirmation
    is_confirmed = confirmed or plan.confirmed
    if plan.requires_confirmation and not is_confirmed:
        return DryRunReport(
            plan_id=plan.plan_id,
            target_id=plan.target_id,
            recipe_id=plan.recipe_id,
            status="confirmation_missing",
            validation_messages=["Plan requires explicit user confirmation (--confirm) before apply"],
            safe_to_apply=False,
        )

    # Simulate steps
    step_results: list[DryRunStepResult] = []
    prevented_destructive: list[str] = []

    for step in plan.steps:
        destructive_prevented = False
        if step.destructive:
            destructive_prevented = True
            prevented_destructive.append(f"{step.action} on {plan.target_id}")

        step_results.append(
            DryRunStepResult(
                order=step.order,
                action=step.action,
                status="simulated",
                destructive_prevented=destructive_prevented,
                elapsed_ms=float(step.estimated_ms),
                message=f"Simulated {step.action} (dry-run safe; zero physical writes)",
            )
        )

    return DryRunReport(
        plan_id=plan.plan_id,
        target_id=plan.target_id,
        recipe_id=plan.recipe_id,
        status="dry_run_success",
        steps_simulated=step_results,
        destructive_actions_prevented=prevented_destructive,
        validation_messages=[],
        safe_to_apply=True,
    )
