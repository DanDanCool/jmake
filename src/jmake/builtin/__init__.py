import importlib
from pathlib import Path

def builtin(name):
    p = Path(__file__).parent / f"{name}.py"
    if not p.exists():
        return None
    path = f"jmake.builtin.{name.split('/')[-1]}"
    m = importlib.import_module(path)
    return m.workspace
