import inspect
from pathlib import Path
import os.path

def scriptenv():
    g = inspect.currentframe().f_back.f_back.f_globals
    env = {}
    p = Path(g["__file__"]).absolute()
    env["path"] = p.parent
    return env

def setupenv():
    found = False
    for i in range(32):
        if os.path.exists(".git"):
            found = True
            break
        os.chdir("..")

    if not found:
        print("could not find root directory, quitting...")

