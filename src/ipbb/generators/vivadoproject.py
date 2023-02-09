
import time
import os
import collections
import copy

from string import Template as tmpl
from ..defaults import kTopEntity
from os.path import abspath, join, split, splitext


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class VivadoProjectGenerator(object):
    """
    Attributes:
        filesets (obj:`dict`): extension-to-fileset association
    """

    # filetypes = {
    #     'ip' : ('.xci', '.xcix'),
    #     'constr' : ('.xdc', '.tcl'),
    #     'design' : ('.vhd', '.vhdl', '.v', '.sv', '.xci', '.xcix', '.ngc', '.edn', '.edf', '.mem', '.mif'),
    # }

    @staticmethod
    def fileset(aSrcCmd):
        name, ext = splitext(aSrcCmd.filepath)

        lFileSet = None
        if ext in ('.xci', '.xcix'):
            lFileSet = 'sources_1'

        elif ext in ('.xdc', '.tcl'):
            lFileSet = 'constrs_1'

        elif ext in ('.vhd', '.vhdl', '.v', '.vh', '.sv', '.ngc', '.edn', '.edf', '.mem', '.mif'):
            if aSrcCmd.useInSynth:
                lFileSet = 'sources_1'
            elif aSrcCmd.useInSim:
                lFileSet = 'sim_1'

        return lFileSet

    reqsettings = {'device_name', 'device_package', 'device_speed'}

    # --------------------------------------------------------------
    def __init__(self, aProjInfo, aIPCachePath=None, aTurbo=True):
        self.projInfo = aProjInfo
        self.ipCachePath = aIPCachePath
        self.turbo = aTurbo

    # --------------------------------------------------------------
    def write(self, aOutput, aSettings, aComponentPaths, aCommandList, aLibs):

        if not self.reqsettings.issubset(aSettings):
            raise RuntimeError(f"Missing required variables: {', '.join(self.reqsettings.difference(aSettings))}")
        lXilinxPart = f'{aSettings["device_name"]}{aSettings["device_package"]}{aSettings["device_speed"]}'

        # ----------------------------------------------------------
        write = aOutput

        lWorkingDir = abspath(join(self.projInfo.path, self.projInfo.name))
        lTopEntity = aSettings.get('top_entity', kTopEntity)

        lSimTopEntity = aSettings.get('vivado.sim_top_entity', None)
        # ----------------------------------------------------------

        write('# Autogenerated project build script')
        write(time.strftime("# %c"))
        write()

        write(
            f'create_project {self.projInfo.name} {lWorkingDir} -part {lXilinxPart} -force'
        )

        if 'board_part' in aSettings:
            write(f'set_property -name "board_part" -value "{aSettings["board_part"]}" -objects [current_project]')
        if 'dsa_board_id' in aSettings:
            write(f'set_property -name "dsa.board_id" -value "{aSettings["dsa_board_id"]}" -objects [current_project]')


        # Add ip repositories to the project variable
        write('set_property ip_repo_paths {{{}}} [current_project]'.format(
            ' '.join(map( lambda c: c.filepath, aCommandList['iprepo']))
        ))

        for util in (c for c in aCommandList['util']):
            write(f'add_files -norecurse -fileset utils_1 {util.filepath}')

        write('if {[string equal [get_filesets -quiet constrs_1] ""]} {create_fileset -constrset constrs_1}')
        write('if {[string equal [get_filesets -quiet sources_1] ""]} {create_fileset -srcset sources_1}')

        for setup in (c for c in aCommandList['setup'] if not c.finalize):
            write(f'source {setup.filepath}')

        lIPNames = []

        lSrcs = aCommandList['src']

        # Grouping commands here, where the order matters only for constraint files
        lSrcCommandGroups = {}

        for src in lSrcs:
            #
            # TODO: rationalise the file-type base file handling
            #     Now it's split betweem the following is statement and
            #     the fileset method
            #

            # Extract path tokens
            _, basename = split(src.filepath)
            name, ext = splitext(basename)

            # local list of commands
            lCommands = []

            if ext in ('.xci', '.xcix'):

                t = 'ip'
                c = f'import_files -norecurse -fileset {self.fileset(src)} $files'
                f = src.filepath

                lCommands += [(t, c, f)]

                lIPNames.append(name)
                # lXciTargetFiles.append(lTargetFile)

            # elif ext in ('.bd'):
            #     c = f'import_files -norecurse -fileset {self.fileset(src)} $files'
            #     f = src.filepath
            # #     import_files -norecurse ${core_dir}/${BD_FILE}
            # #     set WRAPPER_FILE [make_wrapper -files [get_files $BD_FILE] -top]
            # #     add_files -norecurse $WRAPPER_FILE
            # # }

            else:

                t = 'add'
                c = f'add_files -norecurse -fileset {self.fileset(src)} $files'
                f = src.filepath
                lCommands += [(t, c, f)]

                if ext in ('.vhd', '.vhdl') and src.vhdl2008 :
                    t = 'prop'
                    c = 'set_property FILE_TYPE {VHDL 2008} [get_files {$files}]'
                    f = src.filepath
                    lCommands += [(t, c, f)]

                if ext == '.tcl':
                    t = 'prop'
                    c = 'set_property USED_IN implementation [get_files {$files}]'
                    f = src.filepath
                    lCommands += [(t, c, f)]

                if src.lib:
                    t = 'prop'
                    c = f'set_property library {src.lib} [ get_files {{$files}} ]'
                    f = src.filepath
                    lCommands += [(t, c, f)]

            for t, c, f in lCommands:
                # turbo mode: group commands together
                defdict = collections.OrderedDict()
                if self.turbo:
                    lSrcCommandGroups.setdefault(t, defdict).setdefault(c,[]).append(f)
                
                # single mode: execute immediately
                else:
                    write(tmpl(c).substitute(files=f))


        if self.turbo:
            cmd_types = ['ip', 'add', 'prop']
            if not set(lSrcCommandGroups.keys()).issubset(cmd_types):
                raise RuntimeError(f"Command group mismatch {' '.join(lSrcCommandGroups.keys())}")
            for t in cmd_types:
                for c, f in lSrcCommandGroups.get(t,{}).items():
                    write(tmpl(c).substitute(files=' '.join(f)))

        write(f'set_property top {lTopEntity} [get_filesets sources_1]')
        if lSimTopEntity:
            write(f'set_property top {lSimTopEntity} [get_filesets sim_1]')

        if self.ipCachePath:
            write(f'config_ip_cache -import_from_project -use_cache_location {abspath(self.ipCachePath)}')

        for i in lIPNames:
            write(f'upgrade_ip [get_ips {i}]')

        for i in lIPNames:
            write(f'delete_ip_run [get_ips {i}]')
            write(f'generate_target all [get_ips {i}]')
            write(f'create_ip_run [get_ips {i}]')

        for setup in (c for c in aCommandList['setup'] if c.finalize):
            write(f'source {setup.filepath}')

        write('close_project')
    # --------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
