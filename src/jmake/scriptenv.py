import inspect
import argparse
from pathlib import Path
import os.path
import sys

from . import jmake

def setupenv(needpath=True):
    found = False
    for i in range(32):
        if os.path.exists(".git"):
            found = True
            break
        os.chdir("..")

    if not found:
        print("could not find root directory, quitting...")

    host = jmake.Env()
    host.mode = 'generate' if len(sys.argv) <= 1 else sys.argv[1]

    if needpath:
        g = inspect.currentframe().f_back.f_globals
        p = Path(g["__file__"]).absolute()
        host.paths.append(p.parent)
        host.module = p
