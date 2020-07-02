from pathlib import Path

import click
from devenv import completion
from devenv.lib import run_out


@click.command()
@click.argument("version", autocompletion=completion.get_pyenv_versions)
@click.argument("bin_name")
def export(version, bin_name):
    bin_path = Path(run_out(f"pyenv prefix {version}")) / "bin" / bin_name
    link_path = Path("~/.local/bin").expanduser() / bin_name
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
