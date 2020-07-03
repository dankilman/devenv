import os
from inspect import cleandoc

import click

from devenv.lib import run, run_out, JDKTableXML, Config
from devenv import res, completion

IDEA_PREFIX = "PyCharm"

install_methods = ["auto", "pip", "poetry", "mono-repo", "requirements", "raw"]


class Setup:
    def __init__(self, version, no_idea, install_method, config: Config, directory, idea_product_prefix=IDEA_PREFIX):
        self.abs_dir = os.path.abspath(os.path.expanduser(directory or "."))
        self.name = os.path.basename(self.abs_dir)
        self.prefix = None
        self.version = self.process_version(version)
        self.no_idea = no_idea
        self.idea_product_prefix = idea_product_prefix
        if install_method != "raw":
            self.chdir()
        self.install_method = self.process_install_method(install_method)
        self.config = config
        for env in config.envs.values():
            if env["name"] == self.name:
                self.env_config = env
                break
        else:
            self.env_config = None
        if self.install_method == "raw" and not self.env_config:
            raise ValueError(f"raw setup requires configuration and none was found for {self.name}")

    def start(self):
        self.create_env()
        self.install()
        self.configure_idea()

    @staticmethod
    def process_version(version):
        if version:
            return version
        return run_out('python --version', silent=True).strip().split(' ')[1]

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

    def create_env(self):
        versions = [v.strip() for v in run_out("pyenv versions --bare", silent=True).split("\n")]
        if self.name not in versions:
            self.run(f"pyenv virtualenv {self.version} {self.name}")
        if self.install_method != "raw":
            self.run(f"pyenv local {self.name}")
        self.prefix = run_out(f"pyenv prefix {self.name}", silent=True)

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

    def pip(self, command):
        self.run(f"{self.prefix}/bin/pip {command}")

    def poetry(self, command):
        poetry = os.path.expanduser("~/.poetry/bin/poetry")
        self.run(f"{poetry} {command}", env={"VIRTUAL_ENV": self.prefix})
        pass

    def run(self, command, env=None):
        final_env = self.config.env_vars.copy()
        final_env['DEVENV_IGNORE_EXTERNAL_SITE_PACKAGES'] = '1'
        final_env.update(env or {})
        run(command, final_env)

    def install_by_pip(self):
        self.pip("install -e .")

    def install_by_poetry(self):
        self.poetry("install")

    def install_for_mono_repo(self):
        self.run(f"mre install --virtual-env {self.prefix}")

    def install_requirements(self):
        has_constraints = os.path.exists("constraints.txt")
        has_test_requirements = os.path.exists("test-requirements.txt")
        command = "install -r requirements.txt"
        if has_test_requirements:
            command = f"{command} -r test-requirements.txt"
        if has_constraints:
            command = f"{command} -c constraints.txt"
        self.pip(command)

    def install_raw(self):
        conf = self.env_config
        if not conf:
            return
        requirements = conf.get("requirements")
        if not requirements:
            return
        self.pip(f"install {' '.join(requirements)}")

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
@click.option("--idea-product-prefix", default=IDEA_PREFIX, envvar="IDEA_PRODUCT_PREFIX")
@click.option("--directory", "-d")
@click.pass_obj
def setup(config, version, install_method, no_idea, idea_product_prefix, directory):
    Setup(
        version=version[0] if version else None,
        install_method=install_method,
        no_idea=no_idea,
        idea_product_prefix=idea_product_prefix,
        config=config,
        directory=directory,
    ).start()
