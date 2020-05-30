import os
from inspect import cleandoc

import click
from devenv.lib import run, run_out, JDKTableXML
from devenv import res

install_methods = ["auto", "pip", "poetry", "mono-repo", "requirements"]


class Setup:
    def __init__(self, version, no_idea, idea_product_prefix, directory, install_method):
        self.abs_dir = os.path.abspath(os.path.expanduser(directory or "."))
        self.name = os.path.basename(self.abs_dir)
        self.prefix = None
        self.version = version
        self.no_idea = no_idea
        self.idea_product_prefix = idea_product_prefix
        self.chdir()
        self.install_method = self.process_install_method(install_method)

    @staticmethod
    def process_install_method(install_method):
        if install_method == "auto":
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
        versions = [v.strip() for v in run_out("pyenv versions --bare").split("\n")]
        if self.name not in versions:
            run(f"pyenv virtualenv {self.version} {self.name}")
        run(f"pyenv local {self.name}")
        self.prefix = run_out(f"pyenv prefix {self.name}")

    def install(self):
        install_method = self.install_method
        if install_method == "pip":
            self.install_by_pip()
        elif install_method == "poetry":
            self.install_by_poetry()
        elif install_method == "mono-repo":
            self.install_for_mono_repo()
        elif install_method == "requirements":
            self.install_requirements()
        else:
            raise ValueError(f"{install_method}?")

    def pip(self, command):
        run(f"{self.prefix}/bin/pip {command}")

    def poetry(self, command):
        poetry = os.path.expanduser("~/.poetry/bin/poetry")
        run(f"{poetry} {command}", env={"VIRTUAL_ENV": self.prefix})
        pass

    def install_by_pip(self):
        self.pip("install -e .")

    def install_by_poetry(self):
        self.poetry("install")

    def install_for_mono_repo(self):
        self.pip("install -r prod-external-requirements.txt -c ../constraints.txt")
        self.pip("install -r prod-internal-requirements.txt -c ../constraints.txt")
        self.pip("install -r test-requirements.txt -c ../constraints.txt")
        self.pip("install -e . --no-deps")

    def install_requirements(self):
        has_constraints = os.path.exists("constraints.txt")
        command = "install -r requirements.txt {}".format("-c constraints.txt" if has_constraints else "")
        self.pip(command)

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
            print(
                cleandoc(
                    """
                Could not locate jdk.table.xml to configure virtualenv in pycharm
                Either set the env manually from within pycharm or manually put this in the correct place 
                one you find where the file is located:
            """
                )
            )
            print(venv_conf)
        else:
            print(f"Updating {jdk_table_xml_path}")
            jdk_table_xml.add_entry(raw_entry=venv_conf, entry_name=f"Python {version} ({name})")
            jdk_table_xml.save()


@click.command()
@click.argument("version")
@click.argument("directory", nargs=-1)
@click.option("--install-method", default="auto", type=click.Choice(install_methods))
@click.option("--no-idea", is_flag=True)
@click.option("--idea-product-prefix", default="PyCharm", envvar="IDEA_PRODUCT_PREFIX")
def setup(version, directory, install_method, no_idea, idea_product_prefix):
    s = Setup(
        directory=directory[0] if directory else None,
        version=version,
        install_method=install_method,
        no_idea=no_idea,
        idea_product_prefix=idea_product_prefix,
    )
    s.create_env()
    s.install()
    s.configure_idea()
