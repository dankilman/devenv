import sys
import os
import site


# copied from site.py adding prepend support
def addsitedir(sitedir, known_paths=None, prepend=False):
    if known_paths is None:
        known_paths = site._init_pathinfo()
        reset = True
    else:
        reset = False
    sitedir, sitedircase = site.makepath(sitedir)
    if sitedircase not in known_paths:
        _add_to_syspath(sitedir, prepend)
        known_paths.add(sitedircase)
    try:
        names = os.listdir(sitedir)
    except OSError:
        return
    names = [name for name in names if name.endswith(".pth")]
    for name in sorted(names):
        _addpackage(sitedir, name, known_paths, prepend)
    if reset:
        known_paths = None
    return known_paths


def _addpackage(sitedir, name, known_paths, prepend):
    if known_paths is None:
        known_paths = site._init_pathinfo()
        reset = True
    else:
        reset = False
    fullname = os.path.join(sitedir, name)
    try:
        f = open(fullname, "rb")
    except OSError:
        return
    with f:
        for n, line in enumerate(f):
            line = line.decode()
            if line.startswith("#"):
                continue
            try:
                if line.startswith(("import ", "import\t")):
                    exec(line)
                    continue
                line = line.rstrip()
                directory, dircase = site.makepath(sitedir, line)
                if dircase not in known_paths and os.path.exists(directory):
                    _add_to_syspath(directory, prepend)
                    known_paths.add(dircase)
            except Exception:
                sys.stderr.write("Error processing line {:d} of {}:\n".format(n + 1, fullname))
                import traceback

                for record in traceback.format_exception(*sys.exc_info()):
                    for line2 in record.splitlines():
                        sys.stderr.write("  " + line2 + "\n")
                sys.stderr.write("\nRemainder of file ignored\n")
                break
    if reset:
        known_paths = None
    return known_paths


# copied from site.py adding prepend support (END)


def _add_to_syspath(entry, prepend=False):
    if prepend:
        sys.path.insert(0, entry)
    else:
        sys.path.append(entry)


def _load():
    external_site_packages_path = os.path.join(os.path.dirname(__file__), "external-site-packages")
    if os.path.exists(external_site_packages_path):
        with open(external_site_packages_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                should_prepend, site_dir = line.split("|")
                should_prepend = should_prepend == "prepend"
                addsitedir(site_dir, None, should_prepend)


if not os.environ.get('DEVENV_IGNORE_EXTERNAL_SITE_PACKAGES'):
    _load()
