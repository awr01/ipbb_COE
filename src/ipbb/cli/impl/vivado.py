from __future__ import print_function, absolute_import
from future.utils import iterkeys, itervalues, iteritems
# ------------------------------------------------------------------------------

# Modules
import click
import os
import ipbb
import sys
import sh
import time
import types
import socket
import yaml
import re

# Elements
from os.path import join, split, exists, splitext, abspath, basename
from click import echo, secho, style, confirm
from texttable import Texttable
from collections import OrderedDict

from .dep import hash

from ...tools.common import which, SmartOpen
from ..utils import DirSentry, ensureNoMissingFiles, echoVivadoConsoleError

from ...depparser.VivadoProjectMaker import VivadoProjectMaker
from ...tools.xilinx import VivadoOpen, VivadoConsoleError, VivadoSnoozer


# ------------------------------------------------------------------------------
def ensureVivado(env):
    if env.currentproj.settings['toolset'] != 'vivado':
        raise click.ClickException(
            "Work area toolset mismatch. Expected 'vivado', found '%s'"
            % env.currentproj.settings['toolset']
        )

    if not which('vivado'):
        # if 'XILINX_VIVADO' not in os.environ:
        raise click.ClickException(
            "Vivado not found. Please source the Vivado environment before continuing."
        )


# ------------------------------------------------------------------------------
def vivado(ctx, proj, verbosity):
    '''Vivado command group'''

    env = ctx.obj

    env.vivadoEcho = (verbosity == 'all')

    # lProj = proj if proj is not None else env.currentproj.name
    if proj is not None:
        # Change directory before executing subcommand
        from .proj import cd

        cd(env, projname=proj, aVerbose=False)
        return
    else:
        if env.currentproj.name is None:
            raise click.ClickException(
                'Project area not defined. Move to a project area and try again'
            )


# ------------------------------------------------------------------------------
def makeproject(env, aReverse, aOptimise, aToScript, aToStdout):
    '''Make the Vivado project from sources described by dependency files.'''

    lSessionId = 'make-project'

    # Check if vivado is around
    ensureVivado(env)

    lDepFileParser = env.depParser

    # Ensure thay all dependencies have been resolved
    ensureNoMissingFiles(env.currentproj.name, lDepFileParser)

    lVivadoMaker = VivadoProjectMaker(aReverse, aOptimise)

    lDryRun = aToScript or aToStdout

    try:
        with (
            VivadoOpen(lSessionId, echo=env.vivadoEcho)
            if not lDryRun
            else SmartOpen(
                # Dump to script
                aToScript
                if not aToStdout
                # Dump to terminal
                else None
            )
        ) as lConsole:

            lVivadoMaker.write(
                lConsole,
                lDepFileParser.vars,
                lDepFileParser.components,
                lDepFileParser.commands,
                lDepFileParser.libs,
            )

    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        secho(
            "Error caught while generating Vivado TCL commands:\n" + "\n".join(lExc),
            fg='red',
        )
        raise click.Abort()
    # -------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def checksyntax(env):

    lSessionId = 'chk-syn'

    lStopOn = ['HDL 9-806', 'HDL 9-69']  # Syntax errors  # Type not declared

    # Check
    lVivProjPath = join(env.currentproj.path, 'top', 'top.xpr')
    if not exists(lVivProjPath):
        raise click.ClickException("Vivado project %s does not exist" % lVivProjPath)

    ensureVivado(env)

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:

            # Open the project
            lConsole('open_project {}'.format(lVivProjPath))

            # Change message severity to ERROR for the isses we're interested in
            # lConsole(['set_msg_config -id "{}" -new_severity "ERROR"'.format(e) for e in lStopOn])
            lConsole.changeMsgSeverity(lStopOn, 'ERROR')

            # Execute the syntax check
            lConsole('check_syntax')

    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()

    secho(
        "\n{}: Synthax check completed successfully.\n".format(env.currentproj.name),
        fg='green',
    )


# -------------------------------------
# def getSynthRunProps(aConsole):
#     '''Retrieve the status of synthesis runs
    
#     Helper function
    
#     Args:
#         aConsole (obj:`VivadoConsole`): Vivado Wrapper
    
#     Returns:
#         TYPE: Description
#     '''

#     '''
#     To find OOC runs
#      "BlockSrcs" == [get_property FILESET_TYPE [get_property SRCSET [get_runs <run_name>]]]
#     '''

#     with VivadoSnoozer(aConsole):
#         lSynthesisRuns = aConsole('get_runs -filter {IS_SYNTHESIS}')[0].split()
#         lRunProps = {}

#         lProps = ['STATUS', 'PROGRESS', 'STATS.ELAPSED']

#         for lRun in lSynthesisRuns:
#             lValues = aConsole(
#                 [
#                     'get_property {0} [get_runs {1}]'.format(lProp, lRun)
#                     for lProp in lProps
#                 ]
#             )
#             lRunProps[lRun] = dict(zip(lProps, lValues))
#     return lRunProps


# # -------------------------------------
# def formatRunProps(aProps):
#     lProps = aProps.itervalues().next().keys()

#     lSummary = Texttable(max_width=0)
#     lSummary.set_deco(Texttable.HEADER | Texttable.BORDER)
#     lSummary.add_row(['Run'] + lProps)
#     for lRun in sorted(aProps):
#         lInfo = aProps[lRun]
#         lSummary.add_row([lRun] + [lInfo[lProp] for lProp in lProps])

#     return lSummary.draw()

# -------------------------------------
def synth(env, aJobs, aUpdateInt):
    '''Run synthesis'''

    lSessionId = 'synth'

    # Check
    lVivProjPath = join(env.currentproj.path, 'top', 'top.xpr')
    if not exists(lVivProjPath):
        raise click.ClickException("Vivado project %s does not exist" % lVivProjPath)

    ensureVivado(env)

    lArgs = []

    if aJobs is not None:
        lArgs += ['-jobs {}'.format(aJobs)]

    lOOCRegex = re.compile(r'.*_synth_\d+')
    lSynthRun = 'synth_1'

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:

            # Open the project
            lConsole('open_project {}'.format(lVivProjPath))

            with VivadoSnoozer(lConsole):
                lRunProps = { k: v for k, v in iteritems(readRunInfo(lConsole)) if lOOCRegex.match(k) }

            # Reset all OOC synthesis which might are stuck in a running state
            lIPRunsToReset = [
                k for k, v in iteritems(lRunProps)
                if v['STATUS'].startswith('Running')
            ]

            for run in lIPRunsToReset:
                secho(
                    'IP run {} found in running state. Resetting.'.format(run),
                    fg='yellow',
                )
                lConsole('reset_run {}'.format(run))

            lConsole([
                ' '.join(['reset_run', lSynthRun]),
                ' '.join(['launch_runs', lSynthRun] + lArgs)])

            # 
            if not aUpdateInt:
                secho("Run monitoring disabled", fg='cyan')
                lConsole(['wait_on_run synth_1'])
            else:
                secho("Starting run monitoring loop, update interval: {} min(s)".format(aUpdateInt), fg='cyan')
                while True:

                    with VivadoSnoozer(lConsole):
                        lRunProps = readRunInfo(lConsole)

                    lOOCRunProps = { k: v for k, v in iteritems(lRunProps) if lOOCRegex.match(k) }

                    secho('\n' + makeRunsTable(lOOCRunProps).draw(), fg='cyan')

                    lSynthProps = { k: v for k, v in iteritems(lRunProps) if k == lSynthRun }

                    secho('\n' + makeRunsTable(lSynthProps).draw(), fg='cyan')

                    lRunsInError = [ k for k, v in iteritems(lRunProps) if v['STATUS'] == 'synth_design ERROR']
                    if lRunsInError:
                        raise RuntimeError("Detected runs in ERROR {}. Exiting".format(', '.join(lRunsInError)))

                    # Synthesis finished, get out of there
                    if lRunProps['synth_1']['PROGRESS'] == '100%':
                        break

                    lConsole(['wait_on_run synth_1 -timeout {}'.format(aUpdateInt)])

    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        secho(
            "ERROR: \n" + "\n".join(lExc),
            fg='red',
        )
        raise click.Abort()

    secho(
        "\n{}: Synthesis completed successfully.\n".format(env.currentproj.name),
        fg='green',
    )


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def impl(env, jobs):
    '''Launch an implementation run'''

    lSessionId = 'impl'

    # Check
    lVivProjPath = join(env.currentproj.path, 'top', 'top.xpr')
    if not exists(lVivProjPath):
        raise click.ClickException(
            "Vivado project %s does not exist" % lVivProjPath
        )

    ensureVivado(env)

    # List of vivado message that are expected to result into an error.
    lStopOn = ['Timing 38-282']  # Force error when timing is not met

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:

            # Open the project
            lConsole('open_project {}'.format(lVivProjPath))

            # Change message severity to ERROR for the isses we're interested in
            lConsole.changeMsgSeverity(lStopOn, "ERROR")

            lConsole(
                [
                    'reset_run impl_1',
                    'launch_runs impl_1'
                    + (' -jobs {}'.format(jobs) if jobs is not None else ''),
                    'wait_on_run impl_1',
                ]
            )
    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()

    secho(
        "\n{}: Implementation completed successfully.\n".format(env.currentproj.name),
        fg='green',
    )


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# def orderconstr(env, order):
#     '''Reorder constraint set'''

#     lSessionId = 'order-constr'
#     # Check
#     lVivProjPath = join(env.currentproj.path, 'top', 'top.xpr')
#     if not exists(lVivProjPath):
#         raise click.ClickException(
#             "Vivado project %s does not exist" % lVivProjPath
#         )

#     ensureVivado(env)

#     lDepFileParser = env.depParser
#     lConstrSrc = [
#         src.FilePath
#         for src in lDepFileParser.commands['src']
#         if splitext(src.FilePath)[1] in ['.tcl', '.xdc']
#     ]
#     lCmdTemplate = (
#         'reorder_files -fileset constrs_1 -after [get_files {0}] [get_files {1}]'
#     )

#     lConstrOrder = lConstrSrc if order else [f for f in reversed(lConstrSrc)]
#     # echo('\n'.join( ' * {}'.format(style(c, fg='blue')) for c in lConstrOrder ))

#     try:
#         with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:
#             # Open vivado project
#             lConsole('open_project {}'.format(lVivProjPath))
#             # lConstraints = lConsole('get_files -of_objects [get_filesets constrs_1]')[0].split()
#             # print()
#             # print('\n'.join( ' * {}'.format(c) for c in lConstraints ))

#             lCmds = [
#                 lCmdTemplate.format(lConstrOrder[i], lConstrOrder[i + 1])
#                 for i in xrange(len(lConstrOrder) - 1)
#             ]
#             lConsole(lCmds)

#             lConstraints = lConsole('get_files -of_objects [get_filesets constrs_1]')[
#                 0
#             ].split()

#         echo('\nNew constraint order:')
#         echo('\n'.join(' * {}'.format(style(c, fg='blue')) for c in lConstraints))

#     # 'reorder_files -fileset constrs_1 -before [get_files {0}] [get_files {1}]'.format(,to)
#     except VivadoConsoleError as lExc:
#         echoVivadoConsoleError(lExc)
#         raise click.Abort()

#     secho("\n{}: Constraint order set to.\n".format(env.currentproj.name), fg='green')


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def resource_usage(env):

    lSessionId = 'usage'

    # Check
    lVivProjPath = join(env.currentproj.path, 'top', 'top.xpr')
    if not exists(lVivProjPath):
        raise click.ClickException("Vivado project %s does not exist" % lVivProjPath)

    ensureVivado(env)

    lCmds = [
        'open_project %s' % lVivProjPath, 'open_run impl_1',
        'report_utilization -hierarchical -hierarchical_depth 1 -hierarchical_percentages'
        ]

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:
            lConsole(lCmds)
            # lConsole(lImplCmds)
    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()


# ------------------------------------------------------------------------------
def bitfile(env):
    '''Create a bitfile'''

    lSessionId = 'bitfile'

    # if env.currentproj.name is None:
    #     raise click.ClickException(
    #         'Project area not defined. Move into a project area and try again')

    # Check
    lVivProjPath = join(env.currentproj.path, 'top', 'top.xpr')
    if not exists(lVivProjPath):
        raise click.ClickException("Vivado project %s does not exist" % lVivProjPath)

    ensureVivado(env)

    lOpenCmds = ['open_project %s' % lVivProjPath]

    lBitFileCmds = ['launch_runs impl_1 -to_step write_bitstream', 'wait_on_run impl_1']

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:
            lConsole(lOpenCmds)
            lConsole(lBitFileCmds)
    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()

    secho(
        "\n{}: Bitfile successfully written.\n".format(env.currentproj.name), fg='green'
    )


# ------------------------------------------------------------------------------
def readRunInfo(aConsole, aProps=None):
    lInfos = {}
    lProps = aProps if aProps is not None else [
        'STATUS',
        'NEEDS_REFRESH',
        'PROGRESS',
        # 'IS_IMPLEMENTATION',
        # 'IS_SYNTHESIS',
        'STATS.ELAPSED',
        # 'STATS.ELAPSED',
    ]

    # Gather data about existing runs
    lRuns = aConsole('get_runs')[0].split()

    for lRun in sorted(lRuns):

        lCmds = [
            'get_property {0} [get_runs {1}]'.format(lProp, lRun)
            for lProp in lProps
        ]
        lValues = aConsole(lCmds)
        lInfos[lRun] = OrderedDict(zip(lProps, lValues))

    return lInfos

# ------------------------------------------------------------------------------
def makeRunsTable(lInfos):
    lSummary = Texttable(max_width=0)
    if not lInfos:
        return lSummary

    # lSummary.set_deco(Texttable.HEADER | Texttable.BORDER)
    lSummary.set_deco(Texttable.HEADER | Texttable.BORDER)
    lSummary.set_chars( ['-', '|', '+', '-'] )
    lSummary.header(['Run'] + list(next(iter(itervalues(lInfos)))))
    for lRun in sorted(lInfos):
        lInfo = lInfos[lRun]
        lSummary.add_row([lRun] + list(itervalues(lInfo)))

    return lSummary


# ------------------------------------------------------------------------------
def status(env):
    '''Show the status of all runs in the current project.'''

    lSessionId = 'status'

    # if env.currentproj.name is None:
    #     raise click.ClickException(
    #         'Project area not defined. Move into a project area and try again')

    ensureVivado(env)

    lOpenCmds = ['open_project %s' % join(env.currentproj.path, 'top', 'top')]

    lInfos = {}
    lProps = [
        'STATUS',
        'NEEDS_REFRESH',
        'PROGRESS',
        # 'IS_IMPLEMENTATION',
        # 'IS_SYNTHESIS',
        'STATS.ELAPSED',
    ]

    lOOCRegex = re.compile(r'.*_synth_\d+')
    lRunRegex = re.compile(r'(synth|impl)_\d+')

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:
            echo('Opening project')

            with VivadoSnoozer(lConsole):
                lConsole(lOpenCmds)
                lInfos = readRunInfo(lConsole, lProps)

    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()

    echo()

    lOocTable = makeRunsTable({ k: v for k, v in iteritems(lInfos) if lOOCRegex.match(k)})
    secho("Out of context runs", fg='blue')
    echo(lOocTable.draw())
    echo()
    secho("Design runs", fg='blue')
    aaa = makeRunsTable({ k: v for k, v in iteritems(lInfos) if lRunRegex.match(k)})
    echo(aaa.draw())
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def reset(env):
    '''Reset synth and impl runs'''

    lSessionId = 'reset'

    # if env.currentproj.name is None:
    #     raise click.ClickException(
    #         'Project area not defined. Move into a project area and try again')

    ensureVivado(env)

    lOpenCmds = ['open_project %s' % join(env.currentproj.path, 'top', 'top')]

    lResetCmds = ['reset_run synth_1', 'reset_run impl_1']

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:
            lConsole(lOpenCmds)
            lConsole(lResetCmds)
    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()

    secho(
        "\n{}: synth_1 and impl_1 successfully reset.\n".format(env.currentproj.name),
        fg='green',
    )


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def package(ctx, aTag):
    '''Package bitfile with address table and file list

    '''

    env = ctx.obj

    ensureVivado(env)

    lTopProjPath = 'top'

    if not exists(lTopProjPath):
        secho('Vivado project does not exist. Creating the project...', fg='yellow')
        makeproject(env, True, True, None, False)

    lBitPath = join(lTopProjPath, 'top.runs', 'impl_1', 'top.bit')
    if not exists(lBitPath):
        secho('Bitfile does not exist. Attempting a build ...', fg='yellow')
        bitfile(env)

    lPkgPath = 'package'
    lSrcPath = join(lPkgPath, 'src')

    # Cleanup first
    sh.rm('-rf', lPkgPath, _out=sys.stdout)

    # Create the folders
    try:
        os.makedirs(join(lSrcPath, 'addrtab'))
    except OSError:
        pass

    # -------------------------------------------------------------------------
    # Generate a json signature file

    secho("Generating summary files", fg='blue')

    # -------------------------------------------------------------------------

    lHash = hash(env, output=join(lSrcPath, 'hashes.txt'), verbose=True)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    lSummary = dict(env.currentproj.settings)
    lSummary.update(
        {
            'time': socket.gethostname().replace('.', '_'),
            'build host': time.strftime("%a, %d %b %Y %H:%M:%S +0000"),
            'md5': lHash.hexdigest(),
        }
    )

    with open(join(lSrcPath, 'summary.txt'), 'w') as lSummaryFile:
        yaml.safe_dump(lSummary, lSummaryFile, indent=2, default_flow_style=False)
    echo()
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Copy bitfile and address table into the packaging area
    secho("Collecting bitfile", fg='blue')
    sh.cp('-av', lBitPath, lSrcPath, _out=sys.stdout)
    echo()

    secho("Collecting addresstable", fg='blue')
    for addrtab in env.depParser.commands['addrtab']:
        sh.cp('-av', addrtab.FilePath, join(lSrcPath, 'addrtab'), _out=sys.stdout)
    echo()
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Tar everything up
    secho("Generating tarball", fg='blue')

    lTgzBaseName = '_'.join(
        [env.currentproj.settings['name']]
        + ([aTag] if aTag is not None else [])
        + [socket.gethostname().replace('.', '_'), time.strftime('%y%m%d_%H%M')]
    )
    lTgzPath = join(lPkgPath, lTgzBaseName + '.tgz')

    # Zip everything
    sh.tar(
        'cvfz',
        abspath(lTgzPath),
        '-C',
        lPkgPath,
        '--transform',
        's|^src|' + lTgzBaseName + '|',
        'src',
        _out=sys.stdout,
    )
    echo()

    secho(
        "Package " + style('%s' % lTgzPath, fg='green') + " successfully created.",
        fg='green',
    )
    # -------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def archive(ctx):

    lSessionId = 'archive'

    env = ctx.obj

    ensureVivado(env)

    lOpenCmds = ['open_project %s' % join(env.currentproj.path, 'top', 'top')]
    lArchiveCmds = [
        'archive_project %s -force'
        % join(
            env.currentproj.path, '{}.xpr.zip'.format(env.currentproj.settings['name'])
        )
    ]

    try:
        with VivadoOpen(lSessionId, echo=env.vivadoEcho) as lConsole:
            lConsole(lOpenCmds)
            lConsole(lArchiveCmds)
    except VivadoConsoleError as lExc:
        echoVivadoConsoleError(lExc)
        raise click.Abort()


# ------------------------------------------------------------------------------
