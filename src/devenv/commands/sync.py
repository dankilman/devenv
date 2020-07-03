import os

import click

from devenv.commands import setup, pythonpath, export

actions = ["-", "pythonpath", "setup", "export"]


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
    click.echo("=>   Processing `dev setup`")
    for path, conf in config.envs.items():
        if directory and directory != path:
            continue
        sync_setup_single(config, path, conf)


def sync_pythonpath(config, directory):
    click.echo("=>   Processing `dev pythonpath`")
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
    click.echo("=>   Processing `dev export`")
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
@click.option("--directory", "-d")
@click.pass_obj
def sync(config, action, directory):
    action = action[0] if action else "-"
    directory = os.path.abspath(os.path.expanduser(directory)) if directory else None
    if action in ["-", "setup"]:
        sync_setup(config, directory)
    if action in ["-", "pythonpath"]:
        sync_pythonpath(config, directory)
    if action in ["-", "export"]:
        sync_exports(config, directory)
