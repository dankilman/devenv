from devenv.lib import pyenv_versions


def get_pyenv_versions(incomplete, **_):
    return [v for v in pyenv_versions() if v.startswith(incomplete)]
