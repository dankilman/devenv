import click
from devenv.commands import pythonpath, setup, sync, teardown, export
from devenv.lib import load_config


@click.group()
@click.option("--config-path", default="~/.config/devenv.yaml", envvar="DEVENV_CONFIG_PATH")
@click.pass_context
def cli(ctx, config_path):
    config = load_config(config_path)
    ctx.obj = config


cli.add_command(pythonpath.pythonpath)
cli.add_command(setup.setup)
cli.add_command(sync.sync)
cli.add_command(teardown.teardown)
cli.add_command(export.export)


if __name__ == "__main__":
    cli()
