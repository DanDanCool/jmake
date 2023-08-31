import os
import os.path
from pathlib import Path
import argparse
import importlib
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


def package(name, url, branch=None):
    host = jmake.Host()
    if not os.path.exists(host.lib + "/" + name):
        os.system("git submodule update --init --recursive")
    if not os.path.exists(host.lib + "/" + name):
        branch = "-b " + branch + " " if branch else ""
        cmd = "git submodule add " + branch + url + " lib/" + name
        print(cmd)
        os.system(cmd)

    path = host.lib + "." + name + "." + name
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


def _prebuild_events(workspace, args):
    scriptenv.setupenv()
    print("hello from prebuild")


def _postbuild_events(workspace, args):
    scriptenv.setupenv()
    print("hello from postbuild")


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

