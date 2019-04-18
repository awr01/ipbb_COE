from __future__ import print_function, absolute_import


# Modules
import click


# ------------------------------------------------------------------------------
@click.group()
@click.pass_context
def debug(ctx):
    """Collection of debug/utility commands
    
    Args:
        ctx (`obj`): Click context object.
    """
    from .impl.debug import debug
    debug(ctx)


# ------------------------------------------------------------------------------
@debug.command('dump')
@click.pass_context
def dump(ctx):
    from .impl.debug import dump
    dump(ctx)


# ------------------------------------------------------------------------------
@debug.command('ipy')
@click.pass_context
def ipy(ctx):
    """Loads the ipbb environment and opens a python shell
    
    Args:
        ctx (`obj:Context`): Click context object.
    """
    from .impl.debug import ipy
    ipy(ctx)


# ------------------------------------------------------------------------------
@debug.command('test-vivado-formatter')
@click.pass_context
def test_vivado_formatter(ctx):
    """Test vivado formatter
    
    Args:
        ctx (`obj:Context`): Click context object.
    """
    from .impl.debug import test_vivado_formatter
    test_vivado_formatter(ctx)


# ------------------------------------------------------------------------------
@debug.command('test-vivado-console')
@click.pass_context
def test_vivado_console(ctx):
    """Test Vivado console
    
    Args:
        ctx (`obj:Context`): Click context object.
    """
    from .impl.debug import test_vivado_console
    test_vivado_console(ctx)
