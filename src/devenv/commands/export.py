import os
from pathlib import Path

import click
from devenv import completion
from devenv.lib import get_and_verify_env, Env

DEVNEV_EXPORT_DIR = os.environ.get("DEVENV_EXPORT_DIR", "~/.local/bin")


class Export:
    def __init__(self, config, source_env, export_dir=DEVNEV_EXPORT_DIR):
        self.config = config
        self.source_env = get_and_verify_env(source_env)
        self.export_dir = Path(export_dir).expanduser()

    def export(self, bin_name):
        env = Env.from_name(self.config, self.source_env)
        bin_path = env.prefix / "bin" / bin_name
        link_path = self.export_dir / bin_name
        if not bin_path.exists():
            raise click.BadParameter(f"{bin_name} do not exists")
        if link_path.exists():
            if link_path.is_symlink():
                if link_path.resolve() == bin_path.resolve():
                    click.echo(click.style(f"{bin_name}: Already symlinked", fg='magenta'))
                else:
                    click.echo(
                        click.style(f"{bin_name}: Already symlinked, but to something else [{bin_path}]", fg='yellow'))
            else:
                click.echo(click.style(f"{bin_name}: Already exists and is not symlinked", fg='red'))
            return
        click.echo(click.style(f"{bin_name}: Creating symlink", fg='green'))
        link_path.symlink_to(bin_path)


@click.command()
@click.argument("bin_name")
@click.option("--source-env", "-s", autocompletion=completion.get_pyenv_versions)
@click.option("--export-dir", "-e", default=DEVNEV_EXPORT_DIR)
@click.pass_obj
def export(config, source_env, bin_name, export_dir):
    e = Export(config=config, source_env=source_env, export_dir=export_dir)
    e.export(bin_name)
