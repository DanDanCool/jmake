import jmake.py
from pathlib import Path
from uuid import uuid1


class Generator:
    def generate(self, workspace):
        pass


class XMLWriter:
    def __init__():
        elements = []
        data = """<?xml version="1.0" encoding="utf-8"?>"""

    def wrap(self, element):
        return "<" + element + ">"

    def unwrap(self, element):
        return "</" + element + ">"

    def push(self, element, properties=""):
        pad = "  " * len(elements)
        elements.append(element)

        element += " " + properties
        data += "\n" + pad + wrap(element.rstrip())

    def pop(self, element):
        while len(elements):
            item = elements.pop()
            pad = "  " * len(elements)
            data += "\n" + pad + unwrap(item)
            if item == element:
                break

    def item(self, element, value, label=""):
        pad = "  " * len(elements)
        left = element + " " + label
        data += "\n" + pad + wrap(left.rstrip()) + value + unwrap(element)

    def single(self, value):
        pad = "  " * len(elements)
        data += "\n" + pad + wrap(value + "/")


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
                jmake.Target.EXECUTABLE: ".exe"
                jmake.Target.SHARED_LIBRARY: ".dll"
                jmake.Target.STATIC_LIBRARY: ".lib"
                }
        self._uuid = {}

    def vcxproj(self, project):
        writer = XMLWriter()
        header = "DefaultTargets=\"Build\" ToolsVersion=\"" + self._version[jmake.host.vs] + "\"
        xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\""
        writer.push("Project", header)

        options = project.options(self._workspace._configs)

        writer.push("ItemGroup", "Label=\"ProjectConfigurations\"")
        for name, config in project._filters:
            properties = "Include=\"" + name.capitalize() + "|x64\""
            writer.push("ProjectConfiguration", properties)
            writer.item("Configuration", name.capitalize())
            writer.item("Platform", "x64")
            writer.pop("ProjectConfiguration")
        writer.pop("ItemGroup")

        uuid = self._uuid[project._name]
        writer.push("PropertyGroup", "Label=\"Globals\"")
        writer.item("ProjectGuid", "{" + uuid + "}")
        writer.item("VCProjectVersion", self._version[jmake.host.vs])
        writer.item("Keyword", "Win32Proj")
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

        for config in self._workspace.configs:
            condition = "Condition=\"'$(Configuration)|$(Platform)'=='" + config.capitalize() + "|x64'\""
            writer.push("PropertyGroup", condition + " Label=\"Configuration\"")
            writer.item("ConfigurationType", target)
            writer.item("PlatformToolset", self._toolset[jmake.host.vs])
            writer.item("UseDebugLibraries", str(options[config]["debug"]).lower())
            writer.item("CharacterSet", "Unicode")

        writer.single("Import Project=\"$(VCTargetsPath)\\Microsoft.Cpp.props\"")
        writer.push("ImportGroup", "Label=\"ExtensionSettings\"")
        writer.pop("ImportGroup")
        writer.push("ImportGroup", "Label=\"PropertySheets\"")
        label = "Project=\"$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props\"
        Condition=\"exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')\" Label=\"LocalAppDataPlatform\""
        writer.single("Import", label)
        writer.pop("ImportGroup")

        writer.push("PropertyGroup")
        for config in self._workspace.configs:
            outpath = str(Path(self._workspace.bin + "/" conf).absolute()) + "\\" + config.capitalize() + "\\"
            intpath = project._name + ".dir\\" + config.capitalize() + "\\"
            condition = "Condition=\"'$(Configuration)|$(Platform)'=='" + config.capitalize() + "|x64'\""
            writer.item("OutDir", outpath, condition)
            writer.item("IntDir", intpath, condition)
            writer.item("TargetName", project._name, condition)
            writer.item("TargetExt", self._ext[project._target], condition)
            writer.item("LinkIncremental", str(options[config]["debug"]).lower, condition)
            writer.item("GenerateManifest", "true", condition)
        writer.pop("PropertyGroup")

        for config in _self._workspace._configs:
            condition = "Condition='$(Configuration)|$(Platform)'==" + "'" + config.capitalize() + "|x64" "'"
            writer.push("ItemDefinitionGroup", condition)
            writer.push("ClCompile")
            include = "%(AdditionalIncludeDirectories)"
            for directory in options[config]["includes"]:
                p = Path(directory).absolute()
                include += ";" + str(p)
            writer.item("AdditionalIncludeDirectories", include)
            writer.item("AssemblerListingLocation", "$(IntDir)")
            writer.item("ExceptionHandling", "Sync")
            writer.item("LanguageStandard", self._lang[self._workspace.lang])
            writer.item("PrecompiledHeader", "NotUsing")

            runtime = "MultiThreaded"
            if config["debug"]:
                runtime += "Debug"
            if config["libc"] == "mtd":
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
                    value = "\"" + value "\"" if type(value) == str else str(value)
                    tmp = define + "=" + value
                preprocessor += ";" + tmp
            writer.item("PreprocessorDefinitions", preprocessor)
            writer.item("ObjectFileName", "$(IntDir)")
            writer.pop("ClCompile")

            writer.push("Link")
            deps = "$(CoreLibraryDependencies);%(AdditionalDependencies)"
            for dependency in options[config]["depends"]:
                deps += ";" + dependency + ".lib"
            writer.item("AdditionalDependencies", deps)

            libdirs = "%(AdditionalLibraryDirectories)"
            for path in options[config]["libpaths"]:
                libdirs += ";" + path
            writer.item("AdditionalLibraryDirectories", libdirs)
            writer.item("GenerateDebugInformation", str(options[config]["debug"]).lower())
            writer.item("IgnoreSpecificDefaultLibraries", "%(IgnoreSpecificDefaultLibraries)")

            path = Path(self._workspace.bin).absolute() / config.capitalize()
            writer.item("ImportLibrary", str(path / (project._name + ".lib")))
            writer.item("ProgramDataBaseFile", str(path / (project._name + ".pdb")))
            writer.item("SubSystem", "Console")
            writer.pop("Link")

            writer.push("PreBuildEvent")
            command = "python3 ../" + self._workspace._name + ".py prebuild -c " + config
            writer.item("Command", command)
            writer.item("Message", "jmake prebuild step config=" + config)
            writer.pop("PreBuildEvent")

            writer.push("PostBuildEvent")
            command = "python3 ../" + self._workspace._name + ".py postbuild -c " + config
            writer.item("Command", command)
            writer.item("Message", "jmake postbuild step config=" + config)
            writer.pop("PostBuildEvent")

            writer.push("ProjectReference")
            writer.item("LinkLibraryDependencies", "false")
            writer.pop("ProjectReference")

            writer.pop("ItemDefinitionGroup")

        writer.push("ItemGroup")
        for fname in project._files:
            p = Path(self._workspace.src + "/" + fname).absolute()
            element = "ClCompile" if p.suffix in [".cpp", ".c"] else "ClInclude"
            writer.single(element + " Include=\"" + str(p) + "\"")
        writer.pop("ItemGroup")

        writer.push("ItemGroup")
        for dep in project._dependencies:
            if type(dep) != jmake.Project:
                continue
            writer.push("ProjectReference")
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
        for project in workspace:
            names = "\"" + project._name + "\", \"" + project._name + ".vcxproj\", \"{" + self._uuid[project._name] + "}\""
            section = "\nProject(\"{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}\") = " + names
            deps = [ dependency for dependency in project._dependencies if type(dependency) == jmake.Project ]
            if len(deps):
                section += "\n\tProjectSection(ProjectDependencies) = postProject"
                for dependency in deps:
                    uuid = "{" + self._uuid[project._name] + "}"
                    section += "\n\t\t" + uuid + " = " + uuid
                section += "\n\tEndProjectSection"
            section += "\nEndProject"
            data += section
        data += "\nGlobal"
        data += "\n\tGlobalSection(SolutionConfigurationPlatforms) = preSolution"
        for config in workspace._configs:
            config = config.capitalize() + "|x64"
            data += "\n\t\t" + config + " = " + config
        data += "\n\tEndGlobalSection"
        data += "\n\tGlobalSection(ProjectConfigurationPlatforms) = postSolution"
        for project in workspace:
            uuid = "{" + self._uuid[project._name] + "}"
            for config in workspace._configs:
                config = config.capitalize() + "|x64"
                data += "\n\t\t" + uuid + "." + config + ".ActiveCfg = " + config
                data += "\n\t\t" + uuid + "." + config + ".Build.0 = " + config
        data += "\n\tEndGlobalSection"
        data += "\n\tGlobalSection(ExtensibilityGlobals) = postSolution"
        data += "\n\t\tSolutionGuid = {" + str(uuid1()) + "}"
        data += "\n\tEndGlobalSection"
        data += "\n\tGlobalSection(ExtensibilityAddIns) = postSolution"
        data += "\n\tEndGlobalSection"
        data += "\nEndGlobal"
        return data

    def generate(self, workspace):
        self._uuid = {}
        self._workspace = workspace
        for project in workspace._projects:
            self._uuid[project._name] = str(uuid1())
        for project in workspace._projects:
            data = self.vcxproj(project)
            path = Path(workspace.bin) / (project._name + ".vcxproj")
            path.write_text(data)
        data = self.sln(workspace)
        path = Path(workspace.bin) / (workspace._name + ".sln")
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
