from __future__ import print_function

# Import click for ansi colors
import click

from .tools import findFileInParents
from os import walk
from os.path import join, split, exists, splitext, basename
from ..depparser.Pathmaker import Pathmaker
from ..depparser.DepFileParser import DepFileParser

# Constants
kWorkAreaCfgFile = '.ipbbwork'
kProjAreaCfgFile = '.ipbbproj'
kSourceDir = 'src'
kProjDir = 'proj'


# ------------------------------------------------------------------------------
class Environment(object):
    """docstring for Environment"""

    _verbosity = 0

    # ----------------------------------------------------------------------------
    def __init__(self):
        super(Environment, self).__init__()

        self._autodetect()
    # ------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------
    def _clear(self):
        self.workPath = None
        self.workCfgFile = None

        self.project = None
        self.projectPath = None
        self.projectFile = None
        self.projectConfig = None

        self.pathMaker = None
        self.depParser = None
    # ------------------------------------------------------------------------------

    # ----------------------------------------------------------------------------
    def _autodetect(self):

        self._clear()

        lWorkAreaPath = findFileInParents(kWorkAreaCfgFile)

        # Stop here is no signature is found
        if not lWorkAreaPath:
            return

        self.workPath, self.workCfgFile = split(lWorkAreaPath)
        self.pathMaker = Pathmaker(self.src, self._verbosity)

        lProjectPath = findFileInParents(kProjAreaCfgFile)

        # Stop here if no project file is found
        if not lProjectPath:
            return

        self.projectPath, self.projectFile = split(lProjectPath)
        self.project = basename(self.projectPath)

        # Import project settings
        import json
        with open(lProjectPath, 'r') as lProjectFile:
            self.projectConfig = json.load(lProjectFile)

        self.depParser = DepFileParser(
            self.projectConfig['toolset'],
            self.pathMaker,
            aVerbosity=self._verbosity
        )

        try:
            self.depParser.parse(
                self.projectConfig['topPkg'],
                self.projectConfig['topCmp'],
                self.projectConfig['topDep']
            )
        except IOError as e:
            pass
    # ----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    def __str__(self):
        return self.__repr__() + '''({{
    working area path: {workPath}
    project area: {project}
    configuration: {projectConfig}
    pathMaker: {pathMaker}
    parser: {depParser}
    }})'''.format(**(self.__dict__))
    # -----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    @property
    def src(self):
        return join(self.workPath, kSourceDir) if self.workPath is not None else None
    # -----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    @property
    def proj(self):
        return join(self.workPath, kProjDir) if self.workPath is not None else None
    # -----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    def getSources(self):
        return next(walk(self.src))[1]
    # -----------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    def getProjects(self):
        return [
            lProj for lProj in next(walk(self.proj))[1]
            if exists(join(self.proj, lProj, kProjAreaCfgFile))
        ]
    # -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

