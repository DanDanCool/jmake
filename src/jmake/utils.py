from pathlib import Path
import argparse
import importlib
import subprocess
from . import builtin
from . import jmake
from . import generator
from . import scriptenv


def glob(dname, expr):
    env = scriptenv.scriptenv()
    p = env["path"] / dname
    return [ str(path.absolute()) for path in p.glob(expr) ]


def fullpath(dname):
    env = scriptenv.scriptenv()
    if type(dname) != list:
        dname = [dname]
    return [ str(env["path"] / path) for path in dname ]


def package(name, url=None, branch=None):
    if not url:
        return builtin.package_builtin(name)

    host = jmake.Host()
    path = Path(host.lib) / name
    if not path.exists():
        cmd = [ "git", "submodule", "update", "--init", "--recursive" ]
        subprocess.run(cmd)
    if not path.exists():
        cmd = [ "git", "submodule", "add" ]
        if branch:
            cmd.extend([ "-b", branch ])
        cmd.extend([ url, str(path / name) ])
        print(cmd)
        subprocess.run(cmd)

    path = f"{host.lib}.{name}.{name}"
    m = importlib.import_module(path)
    return m.workspace


def _build(workspace, args):
    env = scriptenv.scriptenv()
    gitfolder = env["path"] / ".git"
    if not gitfolder.is_dir():
        return


def _generate(workspace, args):
    host = jmake.Host();
    print("generating make files for " + host.generator)

    host = jmake.Host()
    gen = generator.factory(host.generator)
    gen.generate(workspace)


def _prebuild_events(workspace, args):
    scriptenv.setupenv()
    print("running prebuild events...")
    workspace[args.p].prebuild()


def _postbuild_events(workspace, args):
    scriptenv.setupenv()
    print("running postbuild events...")
    workspace[args.p].postbuild()


def generate(workspace, parser=None, subparser=None):
    env = scriptenv.scriptenv()
    gitfolder = env["path"] / ".git"
    if not gitfolder.is_dir():
        return

    if not parser:
        parser = argparse.ArgumentParser(description='build script')
        subparser = parser.add_subparsers()
    parser.set_defaults(func=_generate)

    build_parser = subparser.add_parser('build')
    build_parser.set_defaults(func=_build)

    gen_parser = subparser.add_parser('generate')
    gen_parser.set_defaults(func=_generate)

    pre_parser = subparser.add_parser('prebuild')
    pre_parser.add_argument('-c')
    pre_parser.add_argument('-p')
    pre_parser.set_defaults(func=_prebuild_events)

    post_parser = subparser.add_parser('postbuild')
    post_parser.add_argument('-c')
    post_parser.add_argument('-p')
    post_parser.set_defaults(func=_postbuild_events)

    args = parser.parse_args()
    args.func(workspace, args)

