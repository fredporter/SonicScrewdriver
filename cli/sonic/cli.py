"""Standalone Python entry point for the Sonic revival baseline."""
import click
from sonic import __version__
from sonic.commands.diagnostics import diagnostics
from sonic.commands.config import config
from sonic.commands.library import library
from sonic.commands.plan import apply_cmd, plan_cmd
from sonic.commands.depot import depot_cmd
from sonic.commands.package import package_cmd
from sonic.commands.profile import profile_cmd
from sonic.commands.scan import doctor, scan

@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.version_option(version=__version__, prog_name="sonic")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    """Sonic-Screwdriver — hardware revival and uDOS provisioning.

    Revival baseline: diagnostics, explicit state intake and offline library lookup. Device discovery, Beacon,
    media creation and capsule deployment return through qualified providers.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

cli.add_command(diagnostics)
cli.add_command(config)
cli.add_command(library)
cli.add_command(depot_cmd, "depot")
cli.add_command(package_cmd, "package")
cli.add_command(profile_cmd, "profile")
cli.add_command(scan)
cli.add_command(doctor)
cli.add_command(plan_cmd, "plan")
cli.add_command(apply_cmd, "apply")

if __name__ == "__main__":
    cli()
