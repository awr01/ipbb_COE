from __future__ import print_function, absolute_import

from .utils import validateComponent

# Modules
import click

# ------------------------------------------------------------------------------
@click.command('init', short_help="Initialise a new working area.")
@click.argument('workarea')
@click.pass_obj
def init(env, workarea):
    '''Initialise a new firmware development area'''
    from .impl.repo import init
    init(env, workarea)
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
@click.group('add', short_help="Add source packages.")
@click.pass_obj
def add(env):
    '''Add a new package to the source area'''
    # -------------------------------------------------------------------------
    # Must be in a build area
    from .impl.repo import add
    add(env)


# ------------------------------------------------------------------------------
@add.command('git', short_help="Add new source package from a git repository")
@click.argument('repo')
@click.option('-b', '--branch', default=None, help='Git branch or tag to clone')
@click.option('-d', '--dest', default=None, help="Destination directory")
@click.pass_obj
def git(env, repo, branch, dest):
    '''Add a git repository to the source area'''
    from .impl.repo import git
    git(env, repo, branch, dest)


# ------------------------------------------------------------------------------
@add.command('svn', short_help="Add new source package from a svn repository.")
@click.argument('repo')
@click.option('-d', '--dest', default=None, help='Destination folder')
@click.option('-r', '--rev', type=click.INT, default=None, help='SVN revision')
@click.option('-n', '--dryrun', is_flag=True, help='Dry run')
@click.option('-s', '--sparse', default=None, multiple=True, help='List of subdirectories to check out.')
@click.pass_obj
def svn(env, repo, dest, rev, dryrun, sparse):
    '''Add a svn repository REPO to the source area'''
    from .impl.repo import svn
    svn(env, repo, dest, rev, dryrun, sparse)


# ------------------------------------------------------------------------------
@add.command('tar', short_help="Add new source package from tarball.")
@click.argument('repo')
@click.option('-d', '--dest', default=None, help='Destination folder')
@click.option('-s', '--strip', type=int, default=None, help='Strip <n> level of directories when unpacking.')
@click.pass_obj
def tar(env, repo, dest, strip):
    '''Add a tarball-ed package to the source area'''
    from .impl.repo import tar
    tar(env, repo, dest, strip)


# ------------------------------------------------------------------------------
@click.group('srcs', short_help="Utility commands to handle source packagess.")
@click.pass_obj
def srcs(env):
    pass

# ------------------------------------------------------------------------------
@srcs.command('info', short_help="Information of the status of source packages.")
@click.pass_obj
def info(env):
    from .impl.repo import info
    info(env)


# ------------------------------------------------------------------------------
@srcs.command('create-component', short_help="Information of the status of source packages.")
@click.argument('component', callback=validateComponent)
@click.pass_obj
def create_component(env, component):
    from .impl.repo import create_component
    create_component(env, component)


# ------------------------------------------------------------------------------
@srcs.command('run', short_help="Run stuff")
@click.option('-p', '--pkg', default=None)
@click.argument('cmd', nargs=1)
@click.argument('args', nargs=-1)
@click.pass_obj
def run(env, pkg, cmd, args):
    from .impl.repo import run
    run(env, pkg, cmd, args)


# ------------------------------------------------------------------------------
@srcs.command('find', short_help="Find src files.")
@click.pass_obj
def find(env):
    from .impl.repo import find
    find(env)
