from enum import Enum
import sys
import os
import platform


Target = Enum('Target', [
    'EXECUTABLE',
    'SHARED_LIBRARY',
    'STATIC_LIBRARY'
    ])


Platform = Enum('Platform', [
    'UNKNOWN',
    'WIN32',
    'LINUX'
    ])


class Host:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Host, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.os = Platform.UNKNOWN
        self.generator = ""
        if sys.platform.startswith('linux'):
            self.os = Platform.LINUX
            self.generator = "make"
        elif sys.platform.startswith('win32'):
            self.os = Platform.WIN32
            self.generator = "vs"
            self.vs = "vs22"

        self.arch = platform.machine()
        self.vcpu = os.cpu_count()
        self._prebuild = []
        self._postbuild = []
        self.lib = "lib"
        self.config = "debug"


class CODE:
    def __init__(self, code):
        self._code = code


class Project:
    def __init__(self, name, target):
        self._name = name
        self._target = target
        self._files = []
        self._defines = {}
        self._dependencies = []
        self._include_dirs = []
        self._library_dirs = []
        self._compile = []
        self._link = []

        # for binary only projects
        self.binaries = []
        self.includes = []
        self.libpaths = []

        self._options = {}
        self._filters = {}
        self._prebuild = []
        self._postbuild = []
        self._default_options()

    def _default_options(self):
        self["debug"] = False
        self["rtti"] = True
        self["warn"] = 3
        self["binary_only"] = False
        self["optimization"] = False

    def add(self, files):
        if type(files) == str:
            self._files.append(files)
        if type(files) == list:
            self._files.extend(files)

    def include(self, dirs):
        if type(dirs) == str:
            self._include_dirs.append(dirs)
        if type(dirs) == list:
            self._include_dirs.extend(dirs)

    def compile(self, options):
        if type(options) == str:
            self._compile.append(options)
        if type(options) == list:
            self._compile.extend(options)

    def link(self, options):
        if type(options) == str:
            self._link.append(options)
        if type(options) == list:
            self._link.extend(options)

    def libpath(self, dirs):
        if type(dirs) == str:
            self._library_dirs.append(dirs)
        if type(dirs) == list:
            self._library_dirs.extend(dirs)

    def depend(self, dependency):
        if type(dependency) == str or type(dependency) == Project:
            self._dependencies.append(dependency)
        if type(dependency) == list:
            self._dependencies.extend(dependency)
        if type(dependency) == Workspace:
            self._dependencies.extend(dependency.libraries())

    def filter(self, config):
        f = Project(config, self._target)
        for key, val in self._options.items():
            f[key] = val
        self._filters[config] = f
        return f

    def options(self, configs):
        opt = {}
        for config in configs:
            projfilter = self._filters[config] if config in self._filters else self
            opt[config] = projfilter._options | {}
            opt[config]["defines"] = self._defines | projfilter._defines
            inc = self._include_dirs + (projfilter._include_dirs if config in self._filters else [])
            lib = self._library_dirs + (projfilter._library_dirs if config in self._filters else [])
            dep = []
            for dependency in self._dependencies:
                if type(dependency) == str:
                    dep.append(dependency)
                if type(dependency) == Project:
                    inc.extend(dependency.includes)
                    dep.extend(dependency.binaries)
                    lib.extend(dependency.libpaths)
                    if not dependency["binary_only"]:
                        dep.append(dependency._name)

            opt[config]["includes"] = inc
            opt[config]["libpaths"] = lib
            opt[config]["depends"] = dep
            opt[config]["compile"] = self._compile
            opt[config]["link"] = self._link

        return opt

    def define(self, key, value):
        self._defines[key] = value

    def prebuild(self):
        for func in self._prebuild:
            func(self)

    def postbuild(self):
        for func in self._postbuild:
            func(self)

    def __getitem__(self, key):
        return self._options[key]

    def __setitem__(self, key, val):
        self._options[key] = val

    def __delitem__(self, key):
        del self._defines[key]


class Workspace:
    def __init__(self, name):
        self._name = name
        self._projects = {}
        self._configs = ["debug", "release"]

        self.bin = "bin"
        self.lang = "cpp17"
        self.libc = "mt"

    def add(self, project):
        if type(project) == Project:
            project = [ project ]

        for p in project:
            if p._name in self._projects:
                continue
            self._projects[p._name] = p
            deps = [ dep for dep in p._dependencies if type(dep) == Project ]
            self.add(deps)

    def libraries(self):
        targets = [ Target.SHARED_LIBRARY, Target.STATIC_LIBRARY ]
        libs = [project for project in self._projects.values() if project._target in targets ]
        return libs

    def __getitem__(self, key):
        return self._projects[key]


def prebuild(project=None):
    def global_prebuild(func):
        host = Host()
        host._prebuild.append(func)
        return func

    def project_prebuild(func):
        project._prebuild.append(func)
        return func

    return global_prebuild if project == None else project_prebuild


def postbuild(project=None):
    def global_postbuild(func):
        host = Host()
        host._postbuild.append(func)
        return func

    def project_postbuild(func):
        project._postbuild.append(func)
        return func

    return global_postbuild if project == None else project_postbuild
