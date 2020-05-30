import os

import click
import yaml

from devenv.lib import run

actions = ["apply", "apply-pythonpath", "apply-setup"]


class Config:
    def __init__(self, raw_config):
        self.raw_config = raw_config
        self.config = self.preprocess_config(self.raw_config)

    @staticmethod
    def preprocess_config(config):
        result = config.copy()
        result["envs"] = {}
        for k, v in config["envs"].items():
            k = os.path.abspath(os.path.expanduser(k))
            name = os.path.basename(k)
            v = v.copy()
            v["name"] = name
            result["envs"][k] = v
        return result

    @property
    def envs(self):
        return self.config.get("envs", {})

    @property
    def env_vars(self):
        return self.config.get("env_vars", {})


def sync_setup_single(config, path, env_conf):
    name = env_conf["name"]
    print(f"===> Processing {name}")
    run("dev setup {} {}".format(env_conf["version"], path), env=config.env_vars)


def sync_pythonpath_single(source_env, input_envs):
    print(f"===> Processing {source_env}")
    run(f"dev pythonpath --source-env {source_env} clear")
    for name, action in input_envs:
        run(f"dev pythonpath --source-env {source_env} {action} {name}")


def sync_setup(config, directory):
    print("===> Processing `dev setup`")
    for path, conf in config.envs.items():
        if directory and directory != path:
            continue
        sync_setup_single(config, path, conf)


def sync_pythonpath(config, directory):
    print("===> Processing `dev pythonpath`")
    for path, conf in config.envs.items():
        if directory and directory != path:
            continue
        name = conf["name"]
        pythonpath = conf.get("pythonpath")
        if pythonpath is None:
            continue
        sync_pythonpath_single(name, pythonpath)
    pass


@click.command()
@click.argument("action", type=click.Choice(actions), nargs=-1)
@click.option("--config-path", default="~/.config/devenv.yaml")
@click.option("--directory", "-d")
def sync(action, config_path, directory):
    action = action[0] if action else "apply"
    directory = os.path.abspath(os.path.expanduser(directory)) if directory else None
    with open(os.path.expanduser(config_path)) as f:
        c = Config(yaml.safe_load(f))
    if action in ["apply", "apply-setup"]:
        sync_setup(c, directory)
    if action in ["apply", "apply-pythonpath"]:
        sync_pythonpath(c, directory)
