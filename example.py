import jmake

jmake.setupenv() # REQUIRED

workspace = jmake.Workspace("hello")
workspace.bin = "bin"

lib = jmake.Project("library", target=jmake.Target.SHARED_LIBRARY)

# import from github
premake = jmake.package("premake", "premake/premake-core", branch="4.x")

# append "**/" to recurse
libfiles = jmake.glob("src", "*.h")
lib.add(libfiles)
lib.depend(premake)

lib.compile("/experimental:c11atomics")
lib.link("/export")

debug = lib.filter("debug")
debug.define("Debug", True)
debug["optimization"] = False
debug["debug"] = True

exe = jmake.Project("executable", target=jmake.Target.EXECUTABLE)
exe.depend(lib)

workspace.add(lib)
workspace.add(exe)

@jmake.prebuild(lib)
def copyfiles(project):
    host = jmake.Host()
    if host.os == "windows":
        pass

jmake.generate(workspace)
