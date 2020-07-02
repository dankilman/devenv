import click
from devenv.commands import pythonpath, setup, sync, teardown, export


@click.group()
def cli():
    pass


cli.add_command(pythonpath.pythonpath)
cli.add_command(setup.setup)
cli.add_command(sync.sync)
cli.add_command(teardown.teardown)
cli.add_command(export.export)


if __name__ == "__main__":
    cli()
