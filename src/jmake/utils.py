from pathlib import Path
import argparse
import importlib
import subprocess
import hashlib
import re
from . import builtin
from . import jmake
from . import generator
from . import scriptenv


def glob(dname, expr):
    if type(expr) != list:
        expr = [ expr ]
    host = jmake.Env()
    p = host.paths[-1] / dname

    res = []
    for e in expr:
        res.extend([ str(path.absolute()) for path in p.glob(e) ])
    return res


# return a path expansion relative to the calling source file
def fullpath(dname):
    host = jmake.Env()
    if type(dname) != list:
        dname = [dname]
    return [ str(host.paths[-1] / path) for path in dname ]


# return a path expansion relative to the project root directory containing the .git folder
def rootpath(dname):
    host = jmake.Env()
    if type(dname) != list:
        dname = [dname]
    return [ str(host.paths[0] / path) for path in dname ]


# note: local packages must have an empty .git file/folder so setupenv works correctly
def package(name, url=None, branch=None):
    if 'builtin/' in name:
        return builtin.package_builtin(name)

    host = jmake.Env()
    path = Path(rootpath(host.lib)[0]) / name
    if url:
        if not path.exists():
            cmd = [ "git", "submodule", "update", "--init", "--recursive" ]
            subprocess.run(cmd)
        if not path.exists():
            cmd = [ "git", "submodule", "add" ]
            if branch:
                cmd.extend([ "-b", branch ])
            cmd.extend([ url, str(path) ])
            subprocess.run(cmd)
    else:
        if not path.exists():
            print(f"error, local package '{name}' specified but not found")
            return None

    path = f"{host.lib}.{name}.{name}"

    size = len(host.paths)
    m = importlib.import_module(path)
    if len(host.paths) > size:
        host.paths.pop() # cleanup paths

    return m.workspace


# added for cmake compatibility
def configure_file(fname_in, fname_out, opts={}):
    host = jmake.Env()
    if host.mode != 'generate':
        return

    lines = []
    with open(fname_in) as f:
        lines = f.readlines()

    p = re.compile('@(\w+)@')
    for i, line in enumerate(lines):
        if not '#cmakedefine' in line:
            matches = p.findall(line)
            for m in matches:
                if m not in opts:
                    print(f"possible error on line {i}, {m} not found in opts\n{lines[i]}")
                    continue
                line = line.replace(f"@{m}@", str(opts[m]))
            lines[i] = line
            continue

        tokens = line.expandtabs(1).split(' ')
        varname = ''
        for token in tokens:
            if token == '': continue
            valid = True
            for discard in ['#cmakedefine']:
                if discard in token:
                    valid = False
                    break
            if not valid: continue
            varname = token
            break
        if varname == '':
            print(f"possible error on line {i}, variable name not found\n{line}")
            continue
        lines[i] = f"#define {varname} {opts[varname]}" if varname in opts else ''

    data = ''.join(lines)
    p = Path(fname_out)
    if p.is_file():
        # we cannot use file_digest due to encoding differences on windows
        with open(p, 'r') as f:
            compare = hashlib.md5(bytes(f.read(), 'utf-8'))
        digest = hashlib.md5(bytes(data, 'utf-8'))
        if digest.hexdigest() == compare.hexdigest():
            return

    with open(p, 'w') as f:
        count = f.write(data)
        print(f"configured {fname_in}, wrote {count} bytes to {fname_out}")

def _build(workspace, args):
    host = jmake.Env()
    gitfolder = host.paths[-1] / ".git"
    if not gitfolder.is_dir():
        return


def _generate(workspace, args):
    host = jmake.Env();
    print("generating make files for " + host.generator)

    gen = generator.factory(host.generator)
    gen.generate(workspace)


def _prebuild_events(workspace, args):
    scriptenv.setupenv(False)
    print("running prebuild events...")
    host = jmake.Env()
    host.config = args.c
    workspace[args.p].prebuild(args.c)


def _postbuild_events(workspace, args):
    scriptenv.setupenv(False)
    print("running postbuild events...")
    host = jmake.Env()
    host.config = args.c
    workspace[args.p].postbuild(args.c)


def generate(workspace, parser=None, subparser=None):
    host = jmake.Env()
    gitfolder = host.paths[-1] / ".git"
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

