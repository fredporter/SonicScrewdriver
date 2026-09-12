"""CLI commands for provisioning plans and dry-run apply."""
from __future__ import annotations

import json
from pathlib import Path

import click

from sonic.lib.plan import KNOWN_RECIPES, Plan, create_plan, dry_run_apply


@click.command("plan")
@click.option("--target", "-t", required=True, help="Target device identifier (e.g. /dev/sda, disk2, sdb)")
@click.option("--recipe", "-r", required=True, type=click.Choice(list(KNOWN_RECIPES.keys())), help="Provisioning recipe name")
@click.option("--out", "-o", type=click.Path(dir_okay=False, writable=True), help="Optional file path to output plan JSON")
@click.option("--json", "as_json", is_flag=True, help="Emit plan in JSON format")
@click.pass_context
def plan_cmd(ctx: click.Context, target: str, recipe: str, out: str | None, as_json: bool):
    """Generate a locked, fingerprint-verified provisioning plan."""
    try:
        plan = create_plan(target_id=target, recipe_id=recipe)
    except Exception as err:
        click.echo(f"Error creating plan: {err}", err=True)
        ctx.exit(1)

    plan_json = plan.model_dump_json(indent=2)

    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(plan_json, encoding="utf-8")

    if as_json:
        click.echo(plan_json)
    else:
        click.echo(f"Sonic Provisioning Plan: {plan.plan_id}")
        click.echo(f"Target: {plan.target_id} | Recipe: {plan.recipe_id} (digest: {plan.recipe_digest[:12]}...)")
        click.echo(f"Created: {plan.created_at} | Expires: {plan.expires_at}")
        click.echo(f"Dry-Run Mode Enforced: {plan.dry_run_only} (Zero physical disk writes)")
        click.echo("\nPrerequisites:")
        for prereq in plan.prerequisites:
            click.echo(f"  [{prereq.status.upper()}] {prereq.name}")
        click.echo(f"\nExecution Steps ({len(plan.steps)}):")
        for step in plan.steps:
            flag = " [DESTRUCTIVE]" if step.destructive else " [READ-ONLY]"
            click.echo(f"  {step.order}. {step.action}{flag} - {step.description}")
        if out:
            click.echo(f"\nPlan written to {out}")

    ctx.exit(0)


@click.command("apply")
@click.option("--plan", "-p", required=True, type=click.Path(exists=True, dir_okay=False), help="Path to plan JSON file")
@click.option("--dry-run/--no-dry-run", default=True, help="Simulate execution without modifying disk (enforced)")
@click.option("--confirm", is_flag=True, help="Acknowledge plan execution and safety confirmation")
@click.option("--json", "as_json", is_flag=True, help="Emit dry-run report in JSON format")
@click.pass_context
def apply_cmd(ctx: click.Context, plan: str, dry_run: bool, confirm: bool, as_json: bool):
    """Execute dry-run simulation of a provisioning plan."""
    plan_path = Path(plan)
    try:
        raw_data = json.loads(plan_path.read_text(encoding="utf-8"))
        plan_obj = Plan.model_validate(raw_data)
    except Exception as err:
        click.echo(f"Error parsing plan from {plan}: {err}", err=True)
        ctx.exit(1)

    # In milestone 2, physical writes are disabled; dry-run is enforced
    report = dry_run_apply(plan_obj, confirmed=confirm)

    if as_json:
        click.echo(report.model_dump_json(indent=2))
    else:
        click.echo(f"Sonic Plan Execution Report — Plan: {report.plan_id}")
        click.echo(f"Status: {report.status.upper()} | Safe to Apply: {report.safe_to_apply}")
        click.echo(f"Target: {report.target_id} | Recipe: {report.recipe_id}")
        if report.validation_messages:
            click.echo("\nValidation Messages:")
            for msg in report.validation_messages:
                click.echo(f"  ! {msg}")
        if report.destructive_actions_prevented:
            click.echo("\nDestructive Actions Prevented (Dry-Run Enforced):")
            for action in report.destructive_actions_prevented:
                click.echo(f"  🛡️  Prevented: {action}")
        if report.steps_simulated:
            click.echo(f"\nSimulated Steps ({len(report.steps_simulated)}):")
            for s in report.steps_simulated:
                click.echo(f"  {s.order}. {s.action}: {s.status.upper()} ({s.elapsed_ms}ms) - {s.message}")

    if report.status == "dry_run_success":
        ctx.exit(0)
    else:
        ctx.exit(1)
