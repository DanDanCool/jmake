import jmake
import subprocess
from pathlib import Path

workspace = jmake.Workspace("vulkan")
vulkan = jmake.Project("vulkan", target=jmake.Target.SHARED_LIBRARY)
vulkan["binary_only"] = True

host = jmake.Host()

if host.os == jmake.Platform.WIN32:
    cmd = [ "pwsh", "-Command", "echo", "$env:VK_SDK_PATH" ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    p = Path(res.stdout.replace('\n', '')).absolute()
    vulkan.includes.append(str(p / 'Include'))
    vulkan.libpaths.append(str(p / 'Lib'))
    vulkan.binaries.append('vulkan-1')

workspace.add(vulkan)
