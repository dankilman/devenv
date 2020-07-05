import shutil
import os

import click

from devenv import completion
from devenv.commands.setup import IDEA_PREFIX
from devenv.lib import run, run_out, JDKTableXML, extract_venv_version_from_misc_xml, get_env_root


@click.command()
@click.argument("directory", nargs=-1)
@click.option("--version", autocompletion=completion.get_pyenv_versions)
@click.option("--idea-product-prefix", default=IDEA_PREFIX, envvar="DEVENV_IDEA_PREFIX")
def teardown(version, directory, idea_product_prefix):
    directory = directory[0] if directory else None
    directory = get_env_root(directory)
    idea_path = os.path.join(directory, ".idea")
    python_version_path = os.path.join(directory, ".python-version")
    venv_name = os.path.basename(directory)
    if os.path.exists(idea_path):
        click.echo("Removing .idea")
        misc_path = os.path.join(idea_path, "misc.xml")
        if not version and os.path.exists(misc_path):
            version = extract_venv_version_from_misc_xml(misc_path)
        shutil.rmtree(idea_path)
    if os.path.exists(python_version_path):
        click.echo("Removing .python-version")
        os.remove(python_version_path)
    venvs = [v.strip() for v in run_out("pyenv versions --bare").split("\n")]
    if venv_name in venvs:
        if not version:
            for venv in venvs:
                if "/" in venv and venv_name in venv:
                    version = venv.split("/")[0]
                    break
        run(f"pyenv virtualenv-delete -f {venv_name}")
    if version:
        jdk_table_xml = JDKTableXML(idea_product_prefix)
        if jdk_table_xml.path:
            entry_name = f"Python {version} ({venv_name})"
            jdk_table_xml.remove_entry(entry_name)
            if jdk_table_xml.dirty:
                click.echo(f"Removing virtualenv from {jdk_table_xml.path}")
                jdk_table_xml.save()
