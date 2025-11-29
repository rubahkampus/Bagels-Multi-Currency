from pathlib import Path
from time import sleep

import click
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from bagels.locations import config_file, database_file, set_custom_root
from bagels.versioning import get_current_version, get_pypi_version, needs_update


@click.group(invoke_without_command=True)
@click.option(
    "--at",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
    help="Specify the path.",
)
@click.option(
    "--migrate",
    type=click.Choice(["actualbudget"]),
    help="Specify the migration type.",
)
@click.option(
    "--source",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to source database file for migration.",
)
@click.pass_context
def cli(ctx, at: Path | None, migrate: str | None, source: Path | None):
    """Bagels CLI."""
    if at:
        set_custom_root(at)

    if migrate:
        if not source:
            raise click.UsageError("--source is required when using --migrate")

        if migrate == "actualbudget":
            try:
                click.echo(f"Starting migration from {source}")
                from bagels.models.database.app import init_db

                init_db()

                from bagels.locations import database_file
                from bagels.migrations.migrate_actualbudget import (
                    BudgetToBagelsMigration,
                )

                migrator = BudgetToBagelsMigration(str(source), str(database_file()))
                migrator.migrate()
                click.echo(click.style("Migration completed successfully!", fg="green"))
                return
            except Exception as e:
                click.echo(click.style(f"Migration failed: {str(e)}", fg="red"))
                ctx.exit(1)

    if ctx.invoked_subcommand is None:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Loading configuration from '{at}'...", total=3)

            from bagels.config import load_config

            load_config()

            from bagels.config import CONFIG

            if CONFIG.state.check_for_updates:
                progress.update(task, advance=1, description="Checking for updates...")

                if needs_update():
                    new = get_pypi_version()
                    cur = get_current_version()
                    click.echo(
                        click.style(
                            f"New version available ({cur} -> {new})! Update with:",
                            fg="yellow",
                        )
                    )
                    click.echo(click.style("```uv tool upgrade bagels```", fg="cyan"))
                    click.echo(
                        click.style(
                            "You can disable this check in-app using the command palette.",
                            fg="bright_black",
                        )
                    )
                    sleep(2)

            progress.update(task, advance=1, description="Initializing database...")

            from bagels.models.database.app import init_db

            init_db()
            progress.update(task, advance=1, description="Starting application...")

            from bagels.app import App

            app = App()
            progress.update(task, advance=1)

        app.run()


@cli.command()
@click.argument("thing_to_locate", type=click.Choice(["config", "database"]))
def locate(thing_to_locate: str) -> None:
    if thing_to_locate == "config":
        print("Config file:")
        print(config_file())
    elif thing_to_locate == "database":
        print("Database file:")
        print(database_file())
        
@cli.group()
def currency() -> None:
    """Manage currency exchange rates."""
    # Ensure config & DB are loaded before subcommands run
    from bagels.config import load_config
    from bagels.models.database.app import init_db

    load_config()
    init_db()


@currency.command("list")
def currency_list() -> None:
    """List all stored exchange rates."""
    # Import lazily so that --at has been processed before DB engine is created
    from bagels.managers.currency_rates import list_rates

    rates = list_rates()
    if not rates:
        click.echo("No currency rates found.")
        return

    click.echo("Stored exchange rates (1 FROM = RATE TO):")
    for r in rates:
        source = "manual" if r.isManual else "auto"
        updated = r.updatedAt.isoformat(sep=" ", timespec="seconds") if r.updatedAt else "n/a"
        click.echo(
            f"- {r.fromCode} -> {r.toCode} = {r.rate} ({source}, updated {updated})"
        )


@currency.command("set-rate")
@click.argument("from_code")
@click.argument("to_code")
@click.argument("rate", type=float)
def currency_set_rate(from_code: str, to_code: str, rate: float) -> None:
    """
    Set or update an exchange rate.

    FROM_CODE and TO_CODE are 3-letter codes (e.g. USD, IDR).
    RATE is the multiplier: 1 FROM_CODE = RATE TO_CODE.
    """
    from bagels.managers.currency_rates import set_rate

    from_code = from_code.strip().upper()
    to_code = to_code.strip().upper()

    set_rate(from_code, to_code, rate)
    click.echo(f"Stored rate: 1 {from_code} = {rate} {to_code}")


if __name__ == "__main__":
    cli()
