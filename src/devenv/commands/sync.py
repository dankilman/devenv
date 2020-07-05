import click

from devenv.commands import setup, pythonpath, export
from devenv.lib import Config, get_env_root

actions = ["-", "pythonpath", "setup", "export"]


class Sync:

    def __init__(self, config: Config, directory):
        self.config = config
        self.directory = get_env_root(directory) if directory != "all" else None

    def apply(self, action):
        if action in ["-", "setup"]:
            self.sync_setup()
        if action in ["-", "pythonpath"]:
            self.sync_pythonpath()
        if action in ["-", "export"]:
            self.sync_exports()

    def sync_setup(self):
        self._sync(self.sync_setup_single, "setup")

    def sync_pythonpath(self):
        self._sync(self.sync_pythonpath_single, "pythonpath")

    def sync_exports(self):
        self._sync(self.sync_exports_single, "export")

    def _sync(self, fn, name):
        config = self.config
        directory = self.directory
        click.echo(f"=>   Processing {name}")
        for path, conf in config.envs.items():
            if directory and directory != path:
                continue
            fn(path, conf)

    def sync_setup_single(self, path, env_conf):
        name = env_conf["name"]
        click.echo(f"===> Processing {name}")
        install_method = env_conf["install_method"]
        if install_method == "raw":
            path = name
        setup.Setup(
            name=name,
            version=env_conf["version"],
            no_idea=install_method == "raw",
            install_method=install_method,
            config=self.config,
            directory=path,
        ).start()

    @staticmethod
    def sync_pythonpath_single(_, env_conf):
        if env_conf["install_method"] == "raw":
            return
        source_env = env_conf["name"]
        input_envs = env_conf["pythonpath"]
        click.echo(f"===> Processing {source_env} {input_envs}")
        p = pythonpath.PythonPath(source_env)
        p.clear()
        for action, name in input_envs:
            p.run(action, name)

    @staticmethod
    def sync_exports_single(_, env_conf):
        exports = env_conf["export"]
        if not exports:
            return
        env_name = env_conf["name"]
        exp = export.Export(env_name)
        for e in exports:
            exp.export(e)


@click.command()
@click.argument("action", type=click.Choice(actions), nargs=-1)
@click.option("--directory", "-d")
@click.option("--sync-all", "-a", is_flag=True)
@click.pass_obj
def sync(config, action, directory, sync_all):
    action = action[0] if action else "-"
    assert not (directory and sync_all)
    directory = directory or (sync_all and "all") or None
    Sync(config, directory).apply(action)
