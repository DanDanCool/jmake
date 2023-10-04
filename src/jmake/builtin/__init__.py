import importlib
from pathlib import Path

def package_builtin(name):
    p = Path(__file__).parent / f"{name}.py"
    if not p.exists():
        return None
    path = f"jmake.builtin.{name}"
    m = importlib.import_module(path)
    return m.workspace
