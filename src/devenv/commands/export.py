import os
from pathlib import Path

import click
from devenv import completion
from devenv.lib import run_out, get_and_verify_env

DEVNEV_EXPORT_DIR = os.environ.get("DEVENV_EXPORT_DIR", "~/.local/bin")


@click.command()
@click.argument("bin_name")
@click.option("--source-env", "-s", autocompletion=completion.get_pyenv_versions)
@click.option("--export-dir", "-e", default=DEVNEV_EXPORT_DIR)
def export(source_env, bin_name, export_dir):
    source_env = get_and_verify_env(source_env)
    bin_path = Path(run_out(f"pyenv prefix {source_env}", silent=True)) / "bin" / bin_name
    link_path = Path(export_dir).expanduser() / bin_name
    if not bin_path.exists():
        raise click.BadParameter(f"{bin_name} do not exists")
    if link_path.exists():
        if link_path.is_symlink():
            if link_path.resolve() == bin_path.resolve():
                click.echo(click.style(f"{bin_name}: Already symlinked", fg='magenta'))
            else:
                click.echo(click.style(f"{bin_name}: Already symlinked, but to something else [{bin_path}]", fg='yellow'))
        else:
            click.echo(click.style(f"{bin_name}: Already exists and is not symlinked", fg='red'))
        return
    click.echo(click.style(f"{bin_name}: Creating symlink", fg='green'))
    link_path.symlink_to(bin_path)
