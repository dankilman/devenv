import json
import os

import click

from devenv import res, completion
from devenv.lib import get_and_verify_env, is_env_root, Env

actions = ["add", "remove", "show", "clear", "infer"]
modify_actions = ["add", "remove", "clear"]


class PythonPath:
    def __init__(self, config, source_env):
        self.config = config
        self.source_env = get_and_verify_env(source_env)
        self.env_config = config.find_env(self.source_env)
        self.name = self.env_config["name"] if self.env_config else os.path.basename(self.source_env)
        self.source_site_packages = self.get_site_packages(self.source_env)
        self.external_site_packages_path = os.path.join(self.source_site_packages, "external-site-packages")
        self.external_site_packages = self.get_external_site_packages()

    def infer(self):
        normalize = lambda n: n.lower().replace("-", "_")
        lookup_dirs = self.config.pythonpath_lookup_dirs
        name_to_path = {}
        for lookup_dir in lookup_dirs:
            for entry in lookup_dir.iterdir():
                if not is_env_root(entry):
                    continue
                name = normalize(entry.name)
                assert name and name not in name_to_path
                name_to_path[name] = str(entry.absolute())
        env = Env.from_name(self.config, self.source_env)
        installed_packages = [
            normalize(package["name"]) for package in
            json.loads(env.pip("list --no-index --format json", out=True))
        ]
        inferred_directories = []
        for installed_package in installed_packages:
            if installed_package == self.name:
                continue
            if installed_package in name_to_path:
                inferred_directories.append(name_to_path[installed_package])
        self.add(inferred_directories)

    def modify(self, action, input_envs=None):
        self.operate_on_external_site_packages(action, input_envs)
        self.write_external_site_packages()
        self.verify_sitecustomize_symlink()

    def clear(self):
        self.modify("clear")

    def add(self, names):
        self.modify("add", names)

    def operate_on_external_site_packages(self, action, input_envs):
        if action == "clear":
            self.external_site_packages = []
            return
        for input_env in input_envs:
            if os.path.isdir(os.path.expanduser(input_env)):
                directory = os.path.abspath(os.path.expanduser(input_env))
            else:
                directory = self.get_site_packages(input_env) if input_env else None
            if action == "remove":
                self.external_site_packages = [d for d in self.external_site_packages if d != directory]
            elif action == "add":
                if not any(d == directory for d in self.external_site_packages):
                    self.external_site_packages.append(directory)
            else:
                raise RuntimeError(f"Unknown action {action}")

    def write_external_site_packages(self):
        with open(self.external_site_packages_path, "w") as f:
            f.write("\n".join(self.external_site_packages))

    def verify_sitecustomize_symlink(self):
        internal_customize_path = os.path.join(res.DIR, "sitecustomize.py")
        sitecustomize_path = os.path.join(self.source_site_packages, "sitecustomize.py")
        if not os.path.exists(sitecustomize_path):
            os.symlink(internal_customize_path, sitecustomize_path)

    def get_external_site_packages(self):
        current_external = []
        if os.path.exists(self.external_site_packages_path):
            with open(self.external_site_packages_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    current_external.append(line)
        return current_external

    def get_site_packages(self, from_env):
        env = Env.from_name(self.config, from_env)
        site_packages = env.python(
            f'-c "import site, sys; sys.stdout.write(site.getsitepackages()[0])"',
            out=True,
        )
        return site_packages


@click.command()
@click.argument("action", type=click.Choice(actions))
@click.argument("env", nargs=-1, autocompletion=completion.get_pyenv_versions)
@click.option("--source-env", "-s", autocompletion=completion.get_pyenv_versions)
@click.pass_obj
def pythonpath(config, action, env, source_env):
    if action in modify_actions and action != "clear" and not env:
        raise click.MissingParameter("error: missing env")
    p = PythonPath(config=config, source_env=source_env)
    if action == "show":
        print(json.dumps(p.external_site_packages, indent=2))
    elif action == "infer":
        p.infer()
    else:
        p.modify(action, env)
