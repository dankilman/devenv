import shutil
import os

import click

from devenv import completion
from devenv.commands.setup import IDEA_PREFIX
from devenv.lib import run, run_out, JDKTableXML, extract_venv_version_from_misc_xml, get_env_root


class TearDown:
    def __init__(self, directory, version, idea_prefix=IDEA_PREFIX):
        self.directory = get_env_root(directory)
        self.version = version
        self.idea_prefix = idea_prefix
        self.venv_name = os.path.basename(self.directory)

    def run(self):
        self.remove_idea()
        self.remove_python_version()
        self.delete_venv()
        self.remove_venv_from_idea()

    def remove_idea(self):
        idea_path = os.path.join(self.directory, ".idea")
        if not os.path.exists(idea_path):
            return
        click.echo("Removing .idea")
        misc_path = os.path.join(idea_path, "misc.xml")
        if not self.version and os.path.exists(misc_path):
            self.version = extract_venv_version_from_misc_xml(misc_path)
        shutil.rmtree(idea_path)

    def remove_python_version(self):
        python_version_path = os.path.join(self.directory, ".python-version")
        if not os.path.exists(python_version_path):
            return
        click.echo("Removing .python-version")
        os.remove(python_version_path)

    def delete_venv(self):
        venvs = [v.strip() for v in run_out("pyenv versions --bare").split("\n")]
        if self.venv_name not in venvs:
            return
        if not self.version:
            for venv in venvs:
                if "/" in venv and self.venv_name in venv:
                    self.version = venv.split("/")[0]
                    break
        run(f"pyenv virtualenv-delete -f {self.venv_name}")

    def remove_venv_from_idea(self):
        if not self.version:
            return
        jdk_table_xml = JDKTableXML(self.idea_prefix)
        if not jdk_table_xml.path:
            return
        entry_name = f"Python {self.version} ({self.venv_name})"
        jdk_table_xml.remove_entry(entry_name)
        if not jdk_table_xml.dirty:
            return
        click.echo(f"Removing virtualenv from {jdk_table_xml.path}")
        jdk_table_xml.save()


@click.command()
@click.argument("directory", nargs=-1)
@click.option("--version", autocompletion=completion.get_pyenv_versions)
@click.option("--idea-product-prefix", default=IDEA_PREFIX, envvar="DEVENV_IDEA_PREFIX")
def teardown(version, directory, idea_product_prefix):
    directory = directory[0] if directory else None
    t = TearDown(directory, version, idea_product_prefix)
    t.run()
