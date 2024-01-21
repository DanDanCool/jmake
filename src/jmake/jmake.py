from enum import Enum
import sys
import os
import platform


Target = Enum('Target', [
    'EXECUTABLE',
    'SHARED_LIBRARY',
    'STATIC_LIBRARY',
    'HEADER_LIBRARY'
    ])


Platform = Enum('Platform', [
    'UNKNOWN',
    'WIN32',
    'LINUX'
    ])


class Env:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Env, cls).__new__(cls)
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
        self.bin = "bin"
        self.config = "debug"
        self.mode = None
        self.paths = [] # stack of paths
        self.module = ''


class Project:
    def __init__(self, name, target):
        host = Env()
        self._module = host.module # internal use for caching

        self._name = name
        self._target = target
        self._files = []
        self._modules = [] # list of tuple(fname: str, public: bool)
        self._defines = {}
        self._dependencies = []
        self._include_dirs = []
        self._library_dirs = []
        self._compile = []
        self._link = []

        # for binary only projects
        self.includes = []
        self.binaries = []
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

    def add_module(self, modules, public=False):
        if type(modules) == str:
            self._modules.append((modules, public))
        if type(modules) == list:
            self._modules.extend([ (module, public) for module in modules ])

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
        if type(dependency) in [ str, Project ]:
            self._dependencies.append(dependency)
        if type(dependency) == list:
            self._dependencies.extend(dependency)
        if type(dependency) == Workspace:
            self._dependencies.extend(dependency.libraries())

    def export(self, includes=None, binaries=None, libpaths=None, append=False):
        if includes:
            if type(includes) != list:
                includes = [ includes ]
            if append:
                self.includes.extend(includes)
            else:
                self.includes = includes
        if binaries:
            if type(binaries) != list:
                binaries = [ binaries ]
            if append:
                self.binaries.extend(binaries)
            else:
                self.binaries = binaries
        if libpaths:
            if type(libpaths) != list:
                libpaths = [ libpaths ]
            if append:
                self.libpaths.extend(binaries)
            else:
                self.libpaths = libpaths

    def filter(self, config):
        f = Project(config, self._target)
        f._options = self._options.copy()
        self._filters[config] = f
        return f

    def dependencies(self):
        dependencies = set()
        for dependency in self._dependencies:
            dependencies.add(dependency)
            if type(dependency) == Project and dependency._target == Target.STATIC_LIBRARY:
                dependencies |= dependency.dependencies()
        return dependencies

    def options(self, configs):
        opt = {}
        for config in configs:
            projfilter = self._filters[config] if config in self._filters else self
            opt[config] = projfilter._options | {}
            opt[config]["defines"] = self._defines | projfilter._defines
            inc = self._include_dirs + (projfilter._include_dirs if config in self._filters else [])
            lib = self._library_dirs + (projfilter._library_dirs if config in self._filters else [])
            dep = []
            mod = {}
            for dependency in self.dependencies():
                if type(dependency) == str:
                    dep.append(dependency)
                if type(dependency) == Project:
                    inc.extend(dependency.includes)
                    dep.extend(dependency.binaries)
                    lib.extend(dependency.libpaths)
                    if valid_dependency_project(dependency):
                        dep.append(dependency._name)
                    mod[dependency._name] = [ module for module, public in dependency._modules if public ]

            opt[config]["includes"] = inc
            opt[config]["libpaths"] = lib
            opt[config]["depends"] = dep
            opt[config]["modules"] = mod
            opt[config]["compile"] = self._compile
            opt[config]["link"] = self._link

        # remove duplicated file names
        unique = { fname for fname in self._files }
        self._files = [ fname for fname in unique ]
        return opt

    def define(self, key, value):
        self._defines[key] = value

    def prebuild(self, config):
        for func in self._prebuild:
            func(self)
        if config in self._filters:
            self._filters[config].prebuild(config)

    def postbuild(self, config):
        for func in self._postbuild:
            func(self)
        if config in self._filters:
            self._filters[config].postbuild(config)

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
        self._always_build = []
        self._configs = ["debug", "release"]
        self.lang = "cpp17"
        self.libc = "mt"

    def add(self, project):
        if type(project) == Project:
            project = [ project ]
        self._always_build.extend(project)
        self._add(project)

    def _add(self, project):
        if type(project) == Project:
            project = [ project ]

        for p in project:
            if p._name in self._projects:
                continue
            self._projects[p._name] = p

            deps = [ dep for dep in p._dependencies if valid_dependency_project(dep) ]
            self._add(deps)

    def libraries(self):
        targets = [ Target.SHARED_LIBRARY, Target.STATIC_LIBRARY, Target.HEADER_LIBRARY ]
        libs = [project for project in self._projects.values() if project._target in targets ]
        return libs

    def __getitem__(self, key):
        return self._projects[key]


# check if a dependency is a valid project
def valid_dependency_project(project):
    if type(project) != Project: return False
    return (not project['binary_only']) and (project._target != Target.HEADER_LIBRARY)


def prebuild(project=None):
    def global_prebuild(func):
        host = Env()
        host._prebuild.append(func)
        return func

    def project_prebuild(func):
        project._prebuild.append(func)
        return func

    return global_prebuild if project == None else project_prebuild


def postbuild(project=None):
    def global_postbuild(func):
        host = Env()
        host._postbuild.append(func)
        return func

    def project_postbuild(func):
        project._postbuild.append(func)
        return func

    return global_postbuild if project == None else project_postbuild
