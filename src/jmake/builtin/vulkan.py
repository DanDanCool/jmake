import subprocess
from pathlib import Path

from .. import jmake

workspace = jmake.Workspace("vulkan")
vulkan = jmake.Project("vulkan", target=jmake.Target.SHARED_LIBRARY)
vulkan["binary_only"] = True

def findvulkan(proj):
    host = jmake.Host()
    if host.mode != 'generate':
        return

    if host.os == jmake.Platform.WIN32:
        cmd = [ "pwsh", "-Command", "echo", "$env:VK_SDK_PATH" ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        p = Path(res.stdout.replace('\n', '')).absolute()
        vulkan.export(includes=str(p / 'Include'), binaries='vulkan-1', libpaths=str(p / 'Lib'))

findvulkan(vulkan)
workspace.add(vulkan) # we suggest not including a jmake.generate in binary only projects
