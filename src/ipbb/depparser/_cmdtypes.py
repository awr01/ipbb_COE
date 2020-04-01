from __future__ import print_function, absolute_import

# -----------------------------------------------------------------------------
class Command(object):
    """Container class for dep commands parsed form dep files

    Attributes:
        cmd       (str): command directive
        FilePath  (str): absolute, normalised path to the command target.
        Package   (str): package the target belongs to.
        Component (str): component withon 'Package' the target belongs to
    """

    # --------------------------------------------------------------
    def __init__(self, aCmd, aFilePath, aPackage, aComponent, aCd):
        super(Command, self).__init__()
        self.cmd = aCmd
        self.FilePath = aFilePath
        self.Package = aPackage
        self.Component = aComponent
        self.cd = aCd

    # --------------------------------------------------------------
    def __str__(self):

        lFlags = self.flags()
        return '{ \'%s\', flags: %s, component: \'%s:%s\' }' % (
            self.FilePath, ''.join(lFlags) if lFlags else 'none', self.Package, self.Component
        )

    # --------------------------------------------------------------
    def __eq__(self, other):
        return (self.FilePath == other.FilePath)

    # --------------------------------------------------------------
    def flags(self):
        return None

    __repr__ = __str__


# -----------------------------------------------------------------------------
class SrcCommand(Command):
    """Container class for dep commands parsed form dep files

    Attributes:
        cmd       (str):  command directive
        FilePath  (str):  absolute, normalised path to the command target.
        Package   (str):  package the target belongs to.
        Component (str):  component withon 'Package' the target belongs to
        Lib       (str):  library the file will be added to
        TopLevel  (bool): addrtab-only flag, identifies address table as top-level
        Vhdl2008  (bool): src-only flag, toggles the vhdl 2008 syntax for .vhd files
    """
    # --------------------------------------------------------------
    def __init__(self, aCmd, aFilePath, aPackage, aComponent, aCd, aLib, aVhdl2008):
        super(SrcCommand, self).__init__(aCmd, aFilePath, aPackage, aComponent, aCd)

        self.Lib = aLib
        self.Vhdl2008 = aVhdl2008

    # --------------------------------------------------------------
    def flags(self):
        lFlags = []
        if self.Vhdl2008:
            lFlags.append('vhdl2008')
        return lFlags

    # --------------------------------------------------------------
    def __eq__(self, other):
        return (self.FilePath == other.FilePath) and (self.Lib == other.Lib)


# -----------------------------------------------------------------------------
class SetupCommand(Command):
    """Container class for dep commands parsed form dep files

    Attributes:
        cmd       (str):  command directive
        FilePath  (str):  absolute, normalised path to the command target.
        Package   (str):  package the target belongs to.
        Component (str):  component withon 'Package' the target belongs to
        Finalise  (bool): setup-only flag, identifies setup scripts to be executed at the end
    """
    # --------------------------------------------------------------
    def __init__(self, aCmd, aFilePath, aPackage, aComponent, aCd, aFinalise):
        super(SetupCommand, self).__init__(aCmd, aFilePath, aPackage, aComponent, aCd)

        self.Finalise = aFinalise

    # --------------------------------------------------------------
    def flags(self):
        return ['finalise'] if self.Finalise else []


# -----------------------------------------------------------------------------
class AddrtabCommand(Command):
    """Container class for dep commands parsed form dep files

    Attributes:
        cmd       (str):  command directive
        FilePath  (str):  absolute, normalised path to the command target.
        Package   (str):  package the target belongs to.
        Component (str):  component withon 'Package' the target belongs to
        TopLevel  (bool): addrtab-only flag, identifies address table as top-level
    """
    # --------------------------------------------------------------
    def __init__(self, aCmd, aFilePath, aPackage, aComponent, aCd, aTopLevel):
        super(AddrtabCommand, self).__init__(aCmd, aFilePath, aPackage, aComponent, aCd)
        self.TopLevel = aTopLevel

    # --------------------------------------------------------------
    def flags(self):
        return ['toplevel'] if self.TopLevel else []


# -----------------------------------------------------------------------------
class IncludeCommand(Command):
    """docstring for IncludeCommand"""
    def __init__(self, aCmd, aFilePath, aPackage, aComponent, aCd, aDepFileObj=None):
        super(IncludeCommand, self).__init__(aCmd, aFilePath, aPackage, aComponent, aCd)
        self.depfile = aDepFileObj