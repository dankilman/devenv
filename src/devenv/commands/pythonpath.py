import json
import os

import click

from devenv import res, completion
from devenv.lib import run_out, get_and_verify_env


class Action:
    actions = ["append", "prepend", "remove", "show", "clear"]

    def __init__(self, action, source_env, input_env):
        self.action = action
        self.source_env = source_env
        self.input_env = input_env
        self.source_site_packages = get_site_packages(self.source_env)
        self.external_site_packages_path = os.path.join(self.source_site_packages, "external-site-packages")
        self.external_site_packages = self.get_external_site_packages()

    def get_external_site_packages(self):
        current_external = []
        if os.path.exists(self.external_site_packages_path):
            with open(self.external_site_packages_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    what, sitedir = line.split("|")
                    current_external.append((what, sitedir))
        return current_external


class Show(Action):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(json.dumps(self.external_site_packages, indent=2))


class Modification(Action):
    modify_actions = ["append", "prepend", "remove", "clear"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.operate_on_external_site_packages()
        self.write_external_site_packages()
        self.verify_sitecustomize_symlink()

    def operate_on_external_site_packages(self):
        input_site_packages = get_site_packages(self.input_env) if self.input_env else None
        if self.action == "remove":
            self.external_site_packages = [(w, d) for (w, d) in self.external_site_packages if d != input_site_packages]
        elif self.action == "clear":
            self.external_site_packages = []
        else:
            if not any(d == input_site_packages for (_, d) in self.external_site_packages):
                self.external_site_packages.append((self.action, input_site_packages))

    def write_external_site_packages(self):
        with open(self.external_site_packages_path, "w") as f:
            for w, d in self.external_site_packages:
                f.write(f"{w}|{d}\n")

    def verify_sitecustomize_symlink(self):
        internal_customize_path = os.path.join(res.DIR, "sitecustomize.py")
        sitecustomize_path = os.path.join(self.source_site_packages, "sitecustomize.py")
        if not os.path.exists(sitecustomize_path):
            os.symlink(internal_customize_path, sitecustomize_path)


def get_site_packages(from_env):
    prefix = run_out(f"pyenv prefix {from_env}", silent=True)
    python_path = os.path.join(prefix, "bin", "python")
    site_packages = run_out(
        f'{python_path} -c  "import site, sys; sys.stdout.write(site.getsitepackages()[0])"',
        silent=True,
    )
    return site_packages


@click.command()
@click.argument("action", type=click.Choice(Action.actions))
@click.argument("env", nargs=-1, autocompletion=completion.get_pyenv_versions)
@click.option("--source-env", "-s", autocompletion=completion.get_pyenv_versions)
def pythonpath(action, env, source_env):
    env = env[0] if isinstance(env, list) else env
    if action in Modification.modify_actions and action != "clear" and not env:
        raise click.MissingParameter("error: missing env")
    source_env = get_and_verify_env(source_env)
    action_cls = Modification if action in Modification.modify_actions else Show
    action_cls(action=action, source_env=source_env, input_env=env)
