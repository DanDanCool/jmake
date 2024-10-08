from pathlib import Path
from uuid import uuid4
from hashlib import file_digest

from . import jmake
import jmllib


class Generator:
    def generate(self, workspace):
        pass


def get_cached(projects):
    dirty = {}
    host = jmake.Env()
    p = Path(host.bin) / 'jmake/cache.jml'
    if not p.is_file():
        for project in projects:
            with open(project._module, 'rb') as f:
                digest = file_digest(f, 'md5')
            dirty[project._name] = {
                    'uuid': str(uuid4()).upper(),
                    'hash': digest.hexdigest()
                    }
        p.parent.mkdir(exist_ok=True)
        p.write_text(jmllib.dumps(dirty))

        for v in dirty.values():
            v['dirty'] = True

        dirty['regenerate'] = True
        return dirty

    with open(p) as f:
        cache = jmllib.load(f)

    all = { 'regenerate': False }

    for project in projects:
        with open(project._module, 'rb') as f:
            digest = file_digest(f, 'md5')
        if project._name not in cache:
            dirty[project._name] = {
                'uuid': str(uuid4()).upper(),
                'hash': digest.hexdigest()
                    }
            all[project._name] = { 'dirty': True } | dirty[project._name]
            all['regenerate'] = True
            continue
        if cache[project._name]['hash'] != digest.hexdigest():
            dirty[project._name] = {
                'uuid': cache[project._name]['uuid'],
                'hash': digest.hexdigest()
                    }
            all[project._name] = { 'dirty': True } | dirty[project._name]
        else:
            all[project._name] = { 'dirty': False } | cache[project._name]
    if len(dirty):
        p.write_text(jmllib.dumps(cache | dirty))
    return all


class XMLWriter:
    def __init__(self):
        self.elements = []
        self.data = """<?xml version="1.0" encoding="utf-8"?>"""

    def wrap(self, element):
        return "<" + element + ">"

    def unwrap(self, element):
        return "</" + element + ">"

    def push(self, element, properties=""):
        pad = "  " * len(self.elements)
        self.elements.append(element)

        element += " " + properties
        self.data += "\n" + pad + self.wrap(element.rstrip())

    def pop(self, element):
        while len(self.elements):
            item = self.elements.pop()
            pad = "  " * len(self.elements)
            self.data += "\n" + pad + self.unwrap(item)
            if item == element:
                break

    def item(self, element, value, label=""):
        pad = "  " * len(self.elements)
        left = element + " " + label
        self.data += "\n" + pad + self.wrap(left.rstrip()) + value + self.unwrap(element)

    def single(self, value):
        pad = "  " * len(self.elements)
        self.data += "\n" + pad + self.wrap(value + "/")


class VSGenerator(Generator):
    def __init__(self):
        self._workspace = None
        self._version = {
                "vs22": "17.0",
                "vs19": "16.0"
                }
        self._toolset = {
                "vs22": "v143",
                "vs19": "v142"
                }
        self._defines = [ "WIN32", "_WINDOWS" ]
        self._lang = {
                "cpp14": "stdcpp14",
                "cpp17": "stdcpp17",
                "cpp20": "stdcpp20",
                "cpp": "stdcpplatest",
                "c11": "stdc11",
                "c17": "stdc17"
                }
        self._ext = {
                jmake.Target.EXECUTABLE: ".exe",
                jmake.Target.SHARED_LIBRARY: ".dll",
                jmake.Target.STATIC_LIBRARY: ".lib"
                }
        self._uuid = {}

    def vcxproj(self, project):
        writer = XMLWriter()
        host = jmake.Env()
        xmlns =  "\" xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\""
        header = "DefaultTargets=\"Build\" ToolsVersion=\"" + self._version[host.vs] + xmlns
        writer.push("Project", header)
        writer.push("PropertyGroup")
        writer.item("PreferredToolArchitecture", project['cpu'])
        writer.pop("PropertyGroup")

        options = project.options(self._workspace._configs)

        writer.push("ItemGroup", "Label=\"ProjectConfigurations\"")
        for config in self._workspace._configs:
            properties = f"Include=\"{config.capitalize()}|{project['cpu']}\""
            writer.push("ProjectConfiguration", properties)
            writer.item("Configuration", config.capitalize())
            writer.item("Platform", project['cpu'])
            writer.pop("ProjectConfiguration")
        writer.pop("ItemGroup")

        uuid = self._uuid[project._name]
        writer.push("PropertyGroup", "Label=\"Globals\"")
        writer.item("ProjectGuid", "{" + uuid + "}")
        writer.item("VCProjectVersion", self._version[host.vs])
        writer.item("Keyword", "Win32Proj")
        writer.item("Platform", project['cpu'])
        writer.item("ProjectName", project._name)
        writer.pop("PropertyGroup")

        writer.single("Import Project=\"$(VCTargetsPath)\\Microsoft.Cpp.default.props\"")

        target = ""
        if project._target == jmake.Target.EXECUTABLE:
            target = "Application"
        elif project._target == jmake.Target.SHARED_LIBRARY:
            target = "DynamicLibrary"
        elif project._target == jmake.Target.STATIC_LIBRARY:
            target = "StaticLibrary"

        for config in self._workspace._configs:
            condition = f"Condition=\"'$(Configuration)|$(Platform)'=='{config.capitalize()}|{project['cpu']}'\""
            writer.push("PropertyGroup", condition + " Label=\"Configuration\"")
            writer.item("ConfigurationType", target)
            writer.item("PlatformToolset", self._toolset[host.vs])
            writer.item("CharacterSet", "Unicode")
            writer.pop("PropertyGroup")

        writer.single("Import Project=\"$(VCTargetsPath)\\Microsoft.Cpp.props\"")
        writer.push("ImportGroup", "Label=\"ExtensionSettings\"")
        writer.pop("ImportGroup")
        writer.push("ImportGroup", "Label=\"PropertySheets\"")
        label = "Project=\"$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props\""
        condition = " Condition=\"exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')\" Label=\"LocalAppDataPlatform\""
        writer.single("Import " + label + condition)
        writer.pop("ImportGroup")

        writer.push("PropertyGroup")
        for config in self._workspace._configs:
            outpath = str(Path(host.bin).absolute() / config.capitalize()) + "\\"
            intpath = project._name + ".dir\\" + config.capitalize() + "\\"
            condition = f"Condition=\"'$(Configuration)|$(Platform)'=='{config.capitalize()}|{project['cpu']}'\""
            writer.item("OutDir", outpath, condition)
            writer.item("IntDir", intpath, condition)
            writer.item("TargetName", project._name, condition)
            writer.item("TargetExt", self._ext[project._target], condition)
            writer.item("LinkIncremental", str(options[config]["debug"]).lower(), condition)
            writer.item("GenerateManifest", "true", condition)
        writer.pop("PropertyGroup")

        for config in self._workspace._configs:
            condition = f"Condition=\"'$(Configuration)|$(Platform)'=='{config.capitalize()}|{project['cpu']}'\""
            writer.push("ItemDefinitionGroup", condition)
            writer.push("ClCompile")

            include = [ "%(AdditionalIncludeDirectories)" ] + [ str(Path(dir).absolute()) for dir in options[config]['includes'] ]
            writer.item("AdditionalIncludeDirectories", ';'.join(include))

            module = []
            for lib, modules in options[config]['modules'].items():
                p = Path(host.bin).absolute() / f"{lib}.dir" / config.capitalize()
                for m in modules:
                    pm = Path(m[0]).absolute()
                    module.append(f"{pm.stem}={str(p / pm.name)}.ifc")
            writer.item('AdditionalModuleDependencies', ';'.join(module))

            compile_options = [ "%(AdditionalOptions)" ] + options[config]['compile']
            writer.item("AdditionalOptions", ' '.join(compile_options))

            writer.item("AssemblerListingLocation", "$(IntDir)")
            writer.item("ExceptionHandling", "Sync")
            optimize = "Disabled" if options[config]["debug"] else "MaxSpeed"
            writer.item("Optimization", optimize)
            if "cpp" in self._workspace.lang:
                writer.item("LanguageStandard", self._lang[self._workspace.lang])
            else:
                writer.item("LanguageStandard_C", self._lang[self._workspace.lang])
            writer.item("PrecompiledHeader", "NotUsing")

            runtime = "MultiThreaded"
            if options[config]["debug"]:
                runtime += "Debug"
            if self._workspace.libc == "mtd":
                runtime += "DLL"
            writer.item("RuntimeLibrary", runtime)
            writer.item("RuntimeTypeInfo", str(options[config]["rtti"]).lower())
            writer.item("UseFullPaths", "false")
            writer.item("WarningLevel", "Level" + str(options[config]["warn"]))

            preprocessor = "%(PreprocessorDefinitions)"
            for define in self._defines:
                preprocessor += ";" + define
            debug = "_DEBUG" if options[config]["debug"] else "NDEBUG"
            preprocessor = preprocessor + ";" + debug
            for define, value in options[config]["defines"].items():
                tmp = define
                if value:
                    value = "\"" + value + "\"" if type(value) == str else str(value)
                    tmp = define + "=" + value
                preprocessor += ";" + tmp
            writer.item("PreprocessorDefinitions", preprocessor)
            # as we use the full path we cannot use RelativeDir
            writer.item("ObjectFileName", "$(IntDir)/%(Directory)")
            writer.pop("ClCompile")

            writer.push("Link")
            deps = "$(CoreLibraryDependencies);%(AdditionalDependencies)"
            for dependency in options[config]["depends"]:
                lib = f"{dependency}.lib"
                if dependency in self._workspace._projects:
                    lib = f"{config.capitalize()}\\{lib}"
                deps += ";" + lib
            writer.item("AdditionalDependencies", deps)

            libdirs = "%(AdditionalLibraryDirectories)"
            for path in options[config]["libpaths"]:
                libdirs += ";" + path
            writer.item("AdditionalLibraryDirectories", libdirs)
            writer.item("GenerateDebugInformation", str(options[config]["debug"]).lower())
            writer.item("IgnoreSpecificDefaultLibraries", "%(IgnoreSpecificDefaultLibraries)")

            path = Path(host.bin).absolute() / config.capitalize()
            writer.item("ImportLibrary", str(path / (project._name + ".lib")))
            writer.item("ProgramDataBaseFile", str(path / (project._name + ".pdb")))
            writer.item("SubSystem", "Console")
            writer.pop("Link")

            writer.push("PreBuildEvent")
            command = f"python {str(Path(self._workspace._name + '.py').absolute())} prebuild -c {config} -p {project._name}"
            writer.item("Command", command)
            writer.item("Message", "jmake prebuild step config=" + config)
            writer.pop("PreBuildEvent")

            writer.push("PostBuildEvent")
            command = f"python {str(Path(self._workspace._name + '.py').absolute())} postbuild -c {config} -p {project._name}"
            writer.item("Command", command)
            writer.item("Message", "jmake postbuild step config=" + config)
            writer.pop("PostBuildEvent")

            writer.push("ProjectReference")
            writer.item("LinkLibraryDependencies", "false")
            writer.pop("ProjectReference")

            writer.pop("ItemDefinitionGroup")

        writer.push("ItemGroup")
        for fname in project._files:
            p = Path(fname).absolute()
            element = "ClCompile" if p.suffix in [".cpp", ".c"] else "ClInclude"
            writer.single(element + " Include=\"" + str(p) + "\"")

        bmipublic = False
        for fname, public in project._modules:
            p = Path(fname).absolute()
            writer.push('ClCompile', f"Include=\"{str(p)}\"")
            writer.item('CompileAs', 'CompileAsCppModule')
            writer.pop('ClCompile')
            bmipublic = bmipublic or public
        writer.pop("ItemGroup")

        if bmipublic:
            writer.push('PropertyGroup')
            writer.item('AllProjectBMIsArePublic', 'true')
            writer.pop('PropertyGroup')

        writer.push("ItemGroup")
        for dep in project._dependencies:
            if not jmake.valid_dependency_project(dep): continue
            vcxproj = Path(host.bin).absolute() / (dep._name + ".vcxproj")
            writer.push("ProjectReference", "Include=\"" + str(vcxproj) + "\"")
            writer.item("Project", "{" + self._uuid[dep._name] + "}")
            writer.item("Name", dep._name)
            writer.pop("ProjectReference")
        writer.pop("ItemGroup")

        writer.single("Import Project=\"$(VCTargetsPath)\\Microsoft.Cpp.Targets\"")
        writer.push("ImportGroup", "Label=\"ExtensionTargets\"")
        writer.pop("ImportGroup")
        writer.pop("Project")
        return writer.data

    def sln(self, workspace):
        data = """
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
        """
        for project in workspace._projects.values():
            names = "\"" + project._name + "\", \"" + project._name + ".vcxproj\", \"{" + self._uuid[project._name] + "}\""
            section = "\nProject(\"{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}\") = " + names
            deps = [ dependency for dependency in project._dependencies if jmake.valid_dependency_project(dependency) ]
            section += "\n\tProjectSection(ProjectDependencies) = postProject"
            for dependency in deps:
                uuid = "{" + self._uuid[dependency._name] + "}"
                section += "\n\t\t" + uuid + " = " + uuid
            section += "\n\tEndProjectSection"
            section += "\nEndProject"
            data += section
        data += "\nGlobal"
        data += "\n\tGlobalSection(SolutionConfigurationPlatforms) = preSolution"
        for config in workspace._configs:
            config = config.capitalize()
            data += "\n\t\t" + config + " = " + config
        data += "\n\tEndGlobalSection"
        data += "\n\tGlobalSection(ProjectConfigurationPlatforms) = postSolution"
        for project in workspace._projects.values():
            uuid = "{" + self._uuid[project._name] + "}"
            for config in workspace._configs:
                conf1 = config.capitalize()
                conf2 = f"{config.capitalize()}|{project['cpu']}"
                data += "\n\t\t" + uuid + "." + conf1 + ".ActiveCfg = " + conf2
                data += "\n\t\t" + uuid + "." + conf1 + ".Build.0 = " + conf2
        data += "\n\tEndGlobalSection"
        data += "\n\tGlobalSection(ExtensibilityGlobals) = postSolution"
        data += "\n\t\tSolutionGuid = {" + str(uuid4()) + "}"
        data += "\n\tEndGlobalSection"
        data += "\n\tGlobalSection(ExtensibilityAddIns) = postSolution"
        data += "\n\tEndGlobalSection"
        data += "\nEndGlobal"
        return data

    def generate(self, workspace):
        self._uuid = {}
        self._workspace = workspace

        host = jmake.Env()
        Path(host.bin).mkdir(exist_ok=True)

        cache = get_cached(workspace._projects.values())
        for project in workspace._always_build:
            cache[project._name]['dirty'] = True

        for project in workspace._projects.values():
            self._uuid[project._name] = cache[project._name]['uuid']
        for project in workspace._projects.values():
            if not jmake.valid_dependency_project(project) or not cache[project._name]['dirty']:
                continue
            data = self.vcxproj(project)
            path = Path(host.bin).absolute() / (project._name + ".vcxproj")
            path.write_text(data)
        if cache['regenerate']:
            data = self.sln(workspace)
            path = Path(host.bin).absolute() / (workspace._name + ".sln")
            path.write_text(data)


class MakeGenerator(Generator):
    def __init__(self):
        pass

    def generate(self, workspace):
        pass


def factory(name):
    if name == "vs":
        return VSGenerator()
    elif name == "make":
        return MakeGenerator()
    return None
