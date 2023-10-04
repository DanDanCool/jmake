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
        vulkan.includes.append(str(p / 'Include'))
        vulkan.libpaths.append(str(p / 'Lib'))
        vulkan.binaries.append('vulkan-1')

findvulkan(vulkan)
workspace.add(vulkan)
