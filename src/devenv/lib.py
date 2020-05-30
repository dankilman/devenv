import subprocess
import os
from xml.dom.minidom import parse, parseString


def extract_venv_version_from_misc_xml(misc_path):
    dom = parse(misc_path)
    components = dom.getElementsByTagName("component")
    for component in components:
        if component.getAttribute("name") == "ProjectRootManager":
            entry_name = component.getAttribute("project-jdk-name")
            if not entry_name.startswith("Python "):
                continue
            return entry_name[len("Python ") :].split(" ")[0]
    return None


class JDKTableXML(object):
    def __init__(self, idea_product_prefix):
        self.idea_product_prefix = idea_product_prefix
        self.path = self.locate_jdk_table_xml()
        self.dirty = False
        self._dom = None

    @property
    def dom(self):
        if not self._dom:
            self._dom = parse(self.path)
        return self._dom

    @property
    def entries(self):
        return self.dom.getElementsByTagName("component")[0]

    def locate_jdk_table_xml(self):
        possible_root_locations = ["~/Library/Application Support/JetBrains"]
        path_suffix = "options/jdk.table.xml"
        for possible_root_location in possible_root_locations:
            possible_root_location = os.path.expanduser(possible_root_location)
            if not os.path.isdir(possible_root_location):
                continue
            dirs = os.listdir(possible_root_location)
            product_dirs = sorted(
                [d for d in dirs if d.lower().startswith(self.idea_product_prefix.lower())], reverse=True
            )
            if not product_dirs:
                continue
            product_dir = product_dirs[0]
            possibly_jdk_table_xml_path = os.path.join(possible_root_location, product_dir, path_suffix)
            if os.path.exists(possibly_jdk_table_xml_path):
                return possibly_jdk_table_xml_path

    def get_entries(self, entry_name):
        entries = []
        for entry in self.entries.getElementsByTagName("jdk"):
            name_node = entry.getElementsByTagName("name")[0]
            name = name_node.getAttribute("value")
            if name == entry_name:
                entries.append(entry)
        return entries

    def entry_exists(self, entry_name):
        return bool(self.get_entries(entry_name))

    def add_entry(self, raw_entry, entry_name):
        if self.entry_exists(entry_name):
            return
        entry_node = parseString(raw_entry).childNodes[0]
        self.entries.appendChild(entry_node)
        self.dirty = True

    def remove_entry(self, entry_name):
        entries = self.get_entries(entry_name)
        if entries:
            for entry in entries:
                self.entries.removeChild(entry)
            self.dirty = True

    def save(self):
        if self.dirty:
            with open(self.path, "w") as f:
                f.write(self.dom.toprettyxml())


def run(command, env=None):
    final_env = os.environ.copy()
    final_env.update(env or {})
    print("Running '{}'".format(command))
    subprocess.check_call(command, shell=True, env=final_env)


def run_out(command):
    print("Running '{}'".format(command))
    return subprocess.check_output(command, shell=True, env=os.environ).decode().strip()
