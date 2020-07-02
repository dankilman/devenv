import os

import click

from devenv.lib import run, load_config

actions = ["apply", "apply-pythonpath", "apply-setup", "apply-export"]


def sync_setup_single(config, path, env_conf):
    name = env_conf["name"]
    print(f"===> Processing {name}")
    version = env_conf.get("version") or config.default_version
    tpe = env_conf.get("type")
    args = ""
    if tpe == "raw":
        args = "--no-idea --install-method raw"
        path = os.path.basename(path)
    run(f"dev setup {version} -d {path} {args}", env=config.env_vars)


def sync_pythonpath_single(source_env, input_envs):
    print(f"===> Processing {source_env}")
    run(f"dev pythonpath --source-env {source_env} clear")
    for name, action in input_envs:
        run(f"dev pythonpath --source-env {source_env} {action} {name}")


def sync_exports_single(env_name, exports):
    print(f"===> Processing {env_name}")
    for export in exports:
        run(f"dev export {env_name} {export}")


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


def sync_exports(config, directory):
    print("===> Processing `dev export`")
    for path, conf in config.envs.items():
        if directory and directory != path:
            continue
        export = conf.get("export")
        if not export:
            continue
        name = conf["name"]
        sync_exports_single(name, export)


@click.command()
@click.argument("action", type=click.Choice(actions), nargs=-1)
@click.option("--config-path", default="~/.config/devenv.yaml")
@click.option("--directory", "-d")
def sync(action, config_path, directory):
    action = action[0] if action else "apply"
    directory = os.path.abspath(os.path.expanduser(directory)) if directory else None
    c = load_config(config_path)
    if action in ["apply", "apply-setup"]:
        sync_setup(c, directory)
    if action in ["apply", "apply-pythonpath"]:
        sync_pythonpath(c, directory)
    if action in ["apply", "apply-export"]:
        sync_exports(c, directory)
