from devenv.lib import run_out


def get_pyenv_versions(incomplete, **_):
    versions = [v.strip() for v in run_out("pyenv versions --bare", silent=True).split("\n")]
    return [v for v in versions if v.startswith(incomplete)]
