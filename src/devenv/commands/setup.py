import os
from inspect import cleandoc

import click

from devenv.lib import run, run_out, JDKTableXML, Config, get_env_root, Env
from devenv import res, completion

IDEA_PREFIX = os.environ.get("DEVENV_IDEA_PREFIX", "PyCharm")

install_methods = ["auto", "pip", "poetry", "mono-repo", "requirements", "raw"]


class Setup:
    def __init__(self, name, version, no_idea, install_method, config: Config, directory, idea_product_prefix=IDEA_PREFIX):
        self.abs_dir = get_env_root(directory)
        self.name = name or os.path.basename(self.abs_dir)
        self.prefix = None
        self.env = None
        self.no_idea = no_idea
        self.idea_product_prefix = idea_product_prefix
        if install_method != "raw":
            self.chdir()
        self.install_method = self.process_install_method(install_method)
        self.config = config
        self.env_config = config.find_env(self.name)
        if self.install_method == "raw" and not self.env_config:
            raise ValueError(f"raw setup requires configuration and none was found for {self.name}")
        self.version = self.process_version(version)

    def start(self):
        self.create_env()
        self.install()
        self.configure_idea()

    def process_version(self, version):
        if version:
            return version
        if self.env_config:
            return self.env_config["version"]
        if self.env_exists():
            python_bin = os.path.join(run_out(f"pyenv prefix {self.name}", silent=True), "bin", "python")
            return run_out(f"{python_bin} --version", silent=True).split(" ")[1]
        return self.config.default_version

    @staticmethod
    def process_install_method(install_method):
        if install_method != "auto":
            return install_method
        if os.path.exists("prod-internal-requirements.txt"):
            install_method = "mono-repo"
        elif os.path.exists("poetry.lock"):
            install_method = "poetry"
        elif os.path.exists("setup.py"):
            install_method = "pip"
        elif os.path.exists("requirements.txt"):
            install_method = "requirements"
        else:
            raise RuntimeError("Can't deduce install method")
        return install_method

    def chdir(self):
        os.chdir(self.abs_dir)

    def env_exists(self):
        versions = [v.strip() for v in run_out("pyenv versions --bare", silent=True).split("\n")]
        return self.name in versions

    def create_env(self):
        if not self.env_exists():
            run(f"pyenv virtualenv {self.version} {self.name}")
        if self.install_method != "raw":
            run(f"pyenv local {self.name}")
        self.prefix = run_out(f"pyenv prefix {self.name}", silent=True)
        self.env = Env(self.config, self.prefix)

    def install(self):
        handlers = {
            "pip": self.install_by_pip,
            "poetry": self.install_by_poetry,
            "mono-repo": self.install_for_mono_repo,
            "requirements": self.install_requirements,
            "raw": self.install_raw,
        }
        handler = handlers.get(self.install_method)
        if not handler:
            raise ValueError(f"{self.install_method}?")
        handler()
        if self.install_method != "raw":
            self.install_raw()

    def install_by_pip(self):
        self.env.pip("install -e .")

    def install_by_poetry(self):
        self.env.poetry("install")

    def install_for_mono_repo(self):
        self.env.run(f"mre install --virtual-env {self.prefix}")

    def install_requirements(self):
        has_constraints = os.path.exists("constraints.txt")
        has_test_requirements = os.path.exists("test-requirements.txt")
        command = "install -r requirements.txt"
        if has_test_requirements:
            command = f"{command} -r test-requirements.txt"
        if has_constraints:
            command = f"{command} -c constraints.txt"
        self.env.pip(command)

    def install_raw(self):
        env_conf = self.env_config
        if not env_conf:
            return
        requirements = env_conf["requirements"]
        if not requirements:
            return
        self.env.pip(f"install {' '.join(requirements)}")

    def configure_idea(self):
        if self.no_idea:
            return

        name = self.name
        version = self.version
        abs_dir = self.abs_dir
        prefix = self.prefix

        idea_template_dir = os.path.join(res.DIR, "dot-idea-template")
        idea_template_misc = os.path.join(idea_template_dir, "misc.xml")
        idea_template_iml = os.path.join(idea_template_dir, "name.iml")
        idea_template_venv = os.path.join(idea_template_dir, "venv-conf.xml")

        idea_dir = os.path.join(abs_dir, ".idea")
        idea_project_name = os.path.join(idea_dir, ".name")
        idea_misc = os.path.join(idea_dir, "misc.xml")
        idea_iml = os.path.join(idea_dir, f"{name}.iml")

        if not os.path.exists(idea_dir):
            os.mkdir(idea_dir)

        # .name
        if not os.path.exists(idea_project_name):
            with open(idea_project_name, "w") as f:
                f.write(name)

        # misc.xml
        if not os.path.exists(idea_misc):
            with open(idea_template_misc) as f:
                misc = f.read()
                misc = misc.replace("{{name}}", name)
                misc = misc.replace("{{version}}", version)
            with open(idea_misc, "w") as f:
                f.write(misc)

        # {{name}}.iml
        if not os.path.exists(idea_iml):
            with open(idea_template_iml) as f:
                iml = f.read()
            with open(idea_iml, "w") as f:
                f.write(iml)

        # jdk.table.xml
        with open(idea_template_venv) as f:
            venv_conf = f.read()
            venv_conf = venv_conf.replace("{{name}}", name)
            venv_conf = venv_conf.replace("{{version}}", version)
            venv_conf = venv_conf.replace("{{prefix}}", prefix)

        jdk_table_xml = JDKTableXML(self.idea_product_prefix)
        jdk_table_xml_path = jdk_table_xml.path
        if not jdk_table_xml_path:
            click.echo(
                cleandoc(
                    """
                Could not locate jdk.table.xml to configure virtualenv in pycharm
                Either set the env manually from within pycharm or manually put this in the correct place 
                one you find where the file is located:
            """
                )
            )
            click.echo(venv_conf)
        else:
            jdk_table_xml.add_entry(raw_entry=venv_conf, entry_name=f"Python {version} ({name})")
            if jdk_table_xml.dirty:
                click.echo(f"Updating {jdk_table_xml_path}")
                jdk_table_xml.save()


@click.command()
@click.argument("version", autocompletion=completion.get_pyenv_versions, nargs=-1)
@click.option("--install-method", default="auto", type=click.Choice(install_methods))
@click.option("--no-idea", is_flag=True)
@click.option("--idea-product-prefix", default=IDEA_PREFIX, envvar="DEVENV_IDEA_PREFIX")
@click.option("--directory", "-d")
@click.option("--name", "-n")
@click.pass_obj
def setup(config, name, version, install_method, no_idea, idea_product_prefix, directory):
    Setup(
        name=name,
        version=version[0] if version else None,
        install_method=install_method,
        no_idea=no_idea,
        idea_product_prefix=idea_product_prefix,
        config=config,
        directory=directory,
    ).start()
