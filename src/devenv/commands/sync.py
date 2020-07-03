import os

import click

from devenv.lib import load_config
from devenv.commands import setup, pythonpath, export

actions = ["apply", "apply-pythonpath", "apply-setup", "apply-export"]


def sync_setup_single(config, path, env_conf):
    name = env_conf["name"]
    click.echo(f"===> Processing {name}")
    version = env_conf.get("version") or config.default_version
    tpe = env_conf.get("type")
    if tpe == "raw":
        path = os.path.basename(path)
    setup.Setup(
        version=version,
        no_idea=tpe == "raw",
        install_method="raw" if tpe == "raw" else "auto",
        config=config,
        directory=path,
    ).start()


def sync_pythonpath_single(source_env, input_envs):
    click.echo(f"===> Processing {source_env} {input_envs}")
    fn = pythonpath.pythonpath.callback
    fn("clear", None, source_env)
    for action, name in input_envs:
        fn(action, name, source_env)


def sync_exports_single(env_name, exports):
    fn = export.export.callback
    for e in exports:
        fn(env_name, e)


def sync_setup(config, directory):
    click.echo("===> Processing `dev setup`")
    for path, conf in config.envs.items():
        if directory and directory != path:
            continue
        sync_setup_single(config, path, conf)


def sync_pythonpath(config, directory):
    click.echo("===> Processing `dev pythonpath`")
    for path, conf in config.envs.items():
        if directory and directory != path:
            continue
        if conf.get("type") == "raw":
            continue
        name = conf["name"]
        ppath = conf.get("pythonpath") or []
        sync_pythonpath_single(name, ppath)
    pass


def sync_exports(config, directory):
    click.echo("===> Processing `dev export`")
    for path, conf in config.envs.items():
        if directory and directory != path:
            continue
        e = conf.get("export")
        if not e:
            continue
        name = conf["name"]
        sync_exports_single(name, e)


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
