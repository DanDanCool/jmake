import os
import os.path
from pathlib import Path
import argparse
import importlib
from . import jmake
from . import generator


def glob(dname, expr):
    p = Path(dname)
    return [ path.name for path in p.glob(expr) ]


def package(url, branch=None):
    stem = str.split(name, sep='/')[-1]
    host = jmake.Host()
    if not os.path.exists(host.lib + "/" + stem):
        os.system("git submodule update --init --recursive")
    if not os.path.exists(host.lib + "/" + stem):
        branch = "-b " + branch if branch else ""
        cmd = "git submodule add " + branch + repo + " " + host.lib
        os.system(cmd)

    path = host.lib + "." + stem + "." + stem + ".py"
    m = importlib.import_module(path)
    return m.workspace


def _build(workspace, args):
    if not os.path.exists(".git"):
        return


def _generate(workspace, args):
    if not os.path.exists(".git"):
        return

    host = jmake.Host()
    gen = generator.factory(host.generator)
    for w in workspace:
        gen.generate(w)


def _setup_env():
    found = False
    for i in range(32):
        if os.path.exists(".git"):
            found = True
            break
        os.chdir("..")

    if not found:
        print("could not find root directory, quitting...")


def _prebuild_events(workspace, args):
    _setup_env()


def _postbuild_events(workspace, args):
    _setup_env()


def generate(workspace):
    if type(workspace) == jmake.Workspace:
        workspace = [ workspace ]

    parser = argparse.ArgumentParser(description='build script')
    subparser = parser.add_subparsers()

    build_parser = subparser.add_parser('build')
    build_parser.set_defaults(func=_build)

    gen_parser = subparser.add_parser('generate')
    gen_parser.set_defaults(func=_generate)

    pre_parser = subparser.add_parser('prebuild')
    pre_parser.add_argument('-c')
    pre_parser.set_defaults(func=_prebuild_events)

    post_parser = subparser.add_parser('postbuild')
    post_parser.add_argument('-c')
    post_parser.set_defaults(func=_postbuild_events)

    args = parser.parse_args()
    args.func(workspace, args)

