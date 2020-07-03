import os

import click

from devenv.commands import setup, pythonpath, export
from devenv.lib import Config

actions = ["-", "pythonpath", "setup", "export"]


class Sync:

    def __init__(self, config: Config, directory):
        self.config = config
        self.directory = os.path.abspath(os.path.expanduser(directory)) if directory else None

    def apply(self, action):
        if action in ["-", "setup"]:
            self.sync_setup()
        if action in ["-", "pythonpath"]:
            self.sync_pythonpath()
        if action in ["-", "export"]:
            self.sync_exports()

    def sync_setup(self):
        config = self.config
        directory = self.directory
        click.echo("=>   Processing `dev setup`")
        for path, conf in config.envs.items():
            if directory and directory != path:
                continue
            self.sync_setup_single(path, conf)

    def sync_pythonpath(self):
        config = self.config
        directory = self.directory
        click.echo("=>   Processing `dev pythonpath`")
        for path, conf in config.envs.items():
            if directory and directory != path:
                continue
            if conf.get("install_method") == "raw":
                continue
            name = conf["name"]
            ppath = conf.get("pythonpath") or []
            self.sync_pythonpath_single(name, ppath)

    def sync_exports(self):
        config = self.config
        directory = self.directory
        click.echo("=>   Processing `dev export`")
        for path, conf in config.envs.items():
            if directory and directory != path:
                continue
            e = conf.get("export")
            if not e:
                continue
            name = conf["name"]
            self.sync_exports_single(name, e)

    def sync_setup_single(self, path, env_conf):
        config = self.config
        name = env_conf["name"]
        click.echo(f"===> Processing {name}")
        version = env_conf.get("version") or config.default_version
        install_method = env_conf.get("install_method") or config.default_install_method
        if install_method == "raw":
            path = os.path.basename(path)
        setup.Setup(
            version=version,
            no_idea=install_method == "raw",
            install_method=install_method,
            config=config,
            directory=path,
        ).start()

    @staticmethod
    def sync_pythonpath_single(source_env, input_envs):
        click.echo(f"===> Processing {source_env} {input_envs}")
        fn = pythonpath.pythonpath.callback
        fn("clear", None, source_env)
        for action, name in input_envs:
            fn(action, name, source_env)

    @staticmethod
    def sync_exports_single(env_name, exports):
        fn = export.export.callback
        for e in exports:
            fn(env_name, e)


@click.command()
@click.argument("action", type=click.Choice(actions), nargs=-1)
@click.option("--directory", "-d")
@click.pass_obj
def sync(config, action, directory):
    action = action[0] if action else "-"
    Sync(config, directory).apply(action)
