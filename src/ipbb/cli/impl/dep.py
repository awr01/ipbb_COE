# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import
from future.utils import iterkeys, itervalues, iteritems
# ------------------------------------------------------------------------------

# Modules
import click
import os
import sh
import hashlib
import collections
import contextlib
import sys
import re

from os.path import (
    join,
    split,
    exists,
    basename,
    abspath,
    splitext,
    relpath,
    isfile,
    isdir,
)
from ...tools.common import which, SmartOpen
from ..utils import DirSentry, printDictTable
from click import echo, secho, style, confirm
from texttable import Texttable


# ------------------------------------------------------------------------------
def dep(ctx, proj):
    '''Dependencies command group'''

    env = ctx.obj

    lProj = proj if proj is not None else env.currentproj.name
    if lProj is not None:
        # Change directory before executing subcommand
        from .proj import cd

        cd(env, lProj, False)
        return
    else:
        if env.currentproj.name is None:
            raise click.ClickException(
                'Project area not defined. Move into a project area and try again'
            )


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def report(env, filters):
    '''Summarise the dependency tree of the current project'''

    lCmdHeaders = ['path', 'flags', 'package', 'component', 'lib']

    lFilterFormat = re.compile('([^=]*)=(.*)')
    lFilterFormatErrors = []
    lFieldNotFound = []
    lFilters = []

    # print ( filters )

    for f in filters:
        m = lFilterFormat.match(f)
        if not m:
            lFilterFormatErrors.append(f)
            continue

        if m.group(1) not in lCmdHeaders:
            lFieldNotFound.append(m.group(1))
            continue

        try:
            i = lCmdHeaders.index(m.group(1))
            r = re.compile(m.group(2))
            lFilters.append((i, r))
        except RuntimeError as e:
            lFilterFormatErrors.append(f)

    if lFilterFormatErrors:
        raise click.ClickException(
            "Filter syntax errors: "
            + ' '.join(['\'' + e + '\'' for e in lFilterFormatErrors])
        )

    if lFieldNotFound:
        raise click.ClickException(
            "Filter syntax errors: fields not found {}. Expected one of {}".format(
                ', '.join("'" + s + "'" for s in lFieldNotFound),
                ', '.join(("'" + s + "'" for s in lCmdHeaders)),
            )
        )

    # return
    lParser = env.depParser
    secho('* Variables', fg='blue')
    printDictTable(lParser.vars, aHeader=False)

    echo()
    secho('* Parsed commands', fg='blue')

    lPrepend = re.compile('(^|\n)')
    for k in lParser.commands:
        echo('  + {0} ({1})'.format(k, len(lParser.commands[k])))
        if not lParser.commands[k]:
            echo()
            continue

        lCmdTable = Texttable(max_width=0)
        lCmdTable.header(lCmdHeaders)
        lCmdTable.set_deco(Texttable.HEADER | Texttable.BORDER)
        lCmdTable.set_chars(['-', '|', '+', '-'])
        for lCmd in lParser.commands[k]:
            # print(lCmd)
            # lCmdTable.add_row([str(lCmd)])
            lRow = [
                relpath(lCmd.FilePath, env.srcdir),
                ','.join(lCmd.flags()),
                lCmd.Package,
                lCmd.Component,
                # lCmd.Map,
                lCmd.Lib,
            ]

            if lFilters and not all([rxp.match(lRow[i]) for i, rxp in lFilters]):
                continue

            lCmdTable.add_row(lRow)

        echo(lPrepend.sub(r'\g<1>  ', lCmdTable.draw()))
        echo()

    secho('Resolved packages & components', fg='blue')

    lString = ''

    # lString += '+----------------------------------+\n'
    # lString += '|  Resolved packages & components  |\n'
    # lString += '+----------------------------------+\n'
    lString += 'packages: ' + ' '.join(iterkeys(lParser.components)) + '\n'
    lString += 'components:\n'
    for pkg in sorted(lParser.components):
        lString += u'* %s (%d)\n' % (pkg, len(lParser.components[pkg]))
        lSortCmp = sorted(lParser.components[pkg])
        for cmp in lSortCmp[:-1]:
            lString += u'  ├── ' + str(cmp) + '\n'
        lString += u'  └── ' + str(lSortCmp[-1]) + '\n'
    if lParser.missing:

        if lParser.missingPackages:
            secho('Missing packages:', fg='red')
            echo(' '.join(list(lParser.missingPackages)))

        # ------
        lCNF = lParser.missingComponents
        if lCNF:
            secho('Missing components:', fg='red')

            for pkg in sorted(lCNF):
                lString += '+ %s (%d)\n' % (pkg, len(lCNF[pkg]))
                lSortCNF = sorted(lCNF[pkg])
                for cmp in lSortCNF[:-1]:
                    lString += u'  ├──' + str(cmp) + '\n'
                lString += u'  └──' + str(lSortCNF[-1]) + '\n'

        # ------

        # ------
    echo(lString)

    lFNF = lParser.missingFiles

    if lFNF:
        secho('Missing files:', fg='red')

        lFNFTable = Texttable(max_width=0)
        lFNFTable.header(['path expression', 'package', 'component', 'included by'])
        lFNFTable.set_deco(Texttable.HEADER | Texttable.BORDER)

        for pkg in sorted(lFNF):
            lCmps = lFNF[pkg]
            for cmp in sorted(lCmps):
                lPathExps = lCmps[cmp]
                for pathexp in sorted(lPathExps):

                    lFNFTable.add_row(
                        [
                            relpath(pathexp, env.srcdir),
                            pkg,
                            cmp,
                            '\n'.join(
                                [relpath(src, env.srcdir) for src in lPathExps[pathexp]]
                            ),
                        ]
                    )
        echo(lPrepend.sub(r'\g<1>  ', lFNFTable.draw()))


# ------------------------------------------------------------------------------
def ls(env, group, output):
    '''List project files by group

    - setup: Project setup scripts
    - src: Code files
    - addrtab: Address tables 
    - cgpfile: ?
    '''

    with SmartOpen(output) as lWriter:
        for addrtab in env.depParser.commands[group]:
            lWriter(addrtab.FilePath)


# ------------------------------------------------------------------------------
def components(env, output):

    with SmartOpen(output) as lWriter:
        for lPkt, lCmps in iteritems(env.depParser.components):
            lWriter('[' + lPkt + ']')
            for lCmp in lCmps:
                lWriter(lCmp)
            lWriter()


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------


@contextlib.contextmanager
def set_env(**environ):
    """
    Temporarily set the process environment variables.

    >>> with set_env(PLUGINS_DIR=u'test/plugins'):
    ...   "PLUGINS_DIR" in os.environ
    True

    >>> "PLUGINS_DIR" in os.environ
    False

    :type environ: dict[str, unicode]
    :param environ: Environment variables to set
    """
    lOldEnviron = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(lOldEnviron)


# ------------------------------------------------------------------------------
# ----------------------------
def hashAndUpdate0g(
    aFilePath, aChunkSize=0x10000, aUpdateHashes=None, aAlgo=hashlib.sha1
):

    # New instance of the selected algorithm
    lHash = aAlgo()

    # Loop ovet the file content
    with open(aFilePath, "rb") as f:
        for lChunk in iter(lambda: f.read(aChunkSize), b''):
            lHash.update(lChunk)

            # Also update other hashes
            for lUpHash in aUpdateHashes:
                lUpHash.update(lChunk)

    return lHash


# ----------------------------


# ----------------------------
def hashAndUpdate(aPath, aChunkSize=0x10000, aUpdateHashes=None, aAlgo=hashlib.sha1):

    # New instance of the selected algorithm
    lHash = aAlgo()

    if isfile(aPath):
        # Loop ovet the file content
        with open(aPath, "rb") as f:
            for lChunk in iter(lambda: f.read(aChunkSize), b''):
                lHash.update(lChunk)

                # Also update other hashes
                for lUpHash in aUpdateHashes:
                    lUpHash.update(lChunk)
    elif isdir(aPath):
        for root, dirs, files in os.walk(aPath):
            for f in files:
                hashAndUpdate(f, aChunkSize, aUpdateHashes=aUpdateHashes, aAlgo=aAlgo)

    return lHash


# ----------------------------


def hash(env, output, verbose):

    lAlgoName = 'sha1'

    lAlgo = getattr(hashlib, lAlgoName, None)

    # Ensure that the selecte algorithm exists
    if lAlgo is None:
        raise AttributeError('Hashing algorithm {0} is not available'.format(lAlgoName))

    with SmartOpen(output) as lWriter:

        if verbose:
            lTitle = "{0} hashes for project '{1}'".format(
                lAlgoName, env.currentproj.name
            )
            lWriter("# " + '=' * len(lTitle))
            lWriter("# " + lTitle)
            lWriter("# " + "=" * len(lTitle))
            lWriter()

        lProjHash = lAlgo()
        lGrpHashes = collections.OrderedDict()
        for lGrp, lCmds in iteritems(env.depParser.commands):
            lGrpHash = lAlgo()
            if verbose:
                lWriter("#" + "-" * 79)
                lWriter("# " + lGrp)
                lWriter("#" + "-" * 79)
            for lCmd in lCmds:
                lCmdHash = hashAndUpdate(
                    lCmd.FilePath, aUpdateHashes=[lProjHash, lGrpHash], aAlgo=lAlgo
                ).hexdigest()
                if verbose:
                    lWriter(lCmdHash, lCmd.FilePath)

            lGrpHashes[lGrp] = lGrpHash

            if verbose:
                lWriter()

        if verbose:
            lWriter("#" + "-" * 79)
            lWriter("# Per cmd-group hashes")
            lWriter("#" + "-" * 79)
            for lGrp, lHash in iteritems(lGrpHashes):
                lWriter(lHash.hexdigest(), lGrp)
            lWriter()

            lWriter("#" + "-" * 79)
            lWriter("# Global hash for project '" + env.currentproj.name + "'")
            lWriter("#" + "-" * 79)
            lWriter(lProjHash.hexdigest(), env.currentproj.name)

        if not verbose:
            lWriter(lProjHash.hexdigest())

    return lProjHash


# ------------------------------------------------------------------------------
def archive(ctx):
    print('archive')


# ------------------------------------------------------------------------------
