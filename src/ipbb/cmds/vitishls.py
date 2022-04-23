
# Modules
import click
import glob
import shutil
import cerberus
import sh

# Elements
from os.path import join, split, exists, splitext, abspath, basename
from copy import deepcopy

from .schema import project_schema, validate_schema

from ..console import cprint, console
from ..utils import which, SmartOpen, mkdir
from ..utils import ensureNoParsingErrors, ensureNoMissingFiles, logVivadoConsoleError
from ..defaults import kTopEntity
from ..generators.vitishlsproject import VitisHLSProjectGenerator
from ..generators.hlsiprepoxci import HLSIpRepoXciGenerator
from ..tools.xilinx import VitisHLSSession, VitisHLSConsoleError, VivadoSession, VivadoConsoleError


# @device_generation = "UltraScalePlus"
# @device_name = "xcku15p"
# @device_package = "-ffva1760"
# @device_speed = "-2-e"
# @board_name = "serenity-dc-ku15p"

# @top_entity = "add7"
# @vitis_hls.solution = "mysol"
# @vitis_hls.vendor = "cern_cms"
# @vitis_hls.library = "emp_hls_examples"
# @vitis_hls.version = "1.1"
_toolset='vitis_hls'
_schema = deepcopy(project_schema)
_schema.update({
    _toolset: {
        'schema': {
            'solution': {'type': 'string'},
            'ipname': {'type': 'string'},
            'vendor': {'type': 'string', 'required': True},
            'library': {'type': 'string', 'required': True},
            'version': {'type': 'string', 'regex': r'\d\.\d(\.\d)?', 'required': True},
            'cflags': {'type': 'string'},
            'csimflags': {'type': 'string'},
        }
    }
})


# ------------------------------------------------------------------------------
def validate_settings(ictx):

    validate_schema(_schema, ictx.depParser.settings)

# ------------------------------------------------------------------------------
def ensure_vitishls(ictx):

    if ictx.currentproj.settings['toolset'] != _toolset:
        raise click.ClickException(
            f"Work area toolset mismatch. Expected {_toolset}, found '{ictx.currentproj.settings['toolset']}'"
        )

    execs = [ x for x in ['vitis_hls', 'vivado_hls'] if which(x)]
    if not any(execs) :
        # if 'XILINX_VIVADO' not in os.ictxiron:
        raise click.ClickException(
            "Vivado not found. Please source the Vivado environment before continuing."
        )

    return execs[0]

# ------------------------------------------------------------------------------
def vitishls(ictx, proj, verbosity):
    '''Vivado command group'''

    ictx.vivadoHlsEcho = (verbosity == 'all')

    if proj is not None:
        # Change directory before executing subcommand
        from .proj import cd

        cd(ictx, projname=proj, aVerbose=False)

    if ictx.currentproj.name is None:
        raise click.ClickException(
            'Project area not defined. Move to a project area and try again'
        )

    validate_settings(ictx)

    ictx.vitishls_proj_path = join(ictx.currentproj.path, ictx.currentproj.name)
    ictx.vitishls_prod_path = join(ictx.currentproj.path, 'ip')
    ictx.vitishls_solution = ictx.depParser.settings.get(f'{_toolset}.solution', 'sol1')
    
    # Check if vivado is available
    ictx.vitishsl_exec = ensure_vitishls(ictx)

# ------------------------------------------------------------------------------
def genproject(ictx, aToScript, aToStdout):
    '''Make the Vivado project from sources described by dependency files.'''

    lSessionId = 'generate-project'

    lDepFileParser = ictx.depParser

    # Ensure that no parsing errors are present
    ensureNoParsingErrors(ictx.currentproj.name, lDepFileParser)

    # Ensure that all dependencies are resolved
    ensureNoMissingFiles(ictx.currentproj.name, lDepFileParser)

    lVivadoMaker = VitisHLSProjectGenerator(ictx.currentproj, ictx.vitishls_solution)

    lDryRun = aToScript or aToStdout
    lScriptPath = aToScript if not aToStdout else None

    try:
        with (
            VitisHLSSession(executable=ictx.vitishsl_exec, sid=lSessionId, echo=ictx.vivadoHlsEcho) if not lDryRun
            else SmartOpen(lScriptPath)
        ) as lConsole:

            lVivadoMaker.write(
                lConsole,
                lDepFileParser.settings,
                lDepFileParser.packages,
                lDepFileParser.commands,
                lDepFileParser.rootdir,
            )

    except VitisHLSConsoleError as lExc:
        logVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        console.log(
            f"Error caught while generating Vivado TCL commands {lExc}",
            style='red',
        )
        raise click.Abort()

    console.log(
        f"{ictx.currentproj.name}: Project created successfully.",
        style='green',
    )
    # -------------------------------------------------------------------------


# ------------------------------------------------------------------------------
def csynth(ictx):

    lSessionId = 'csynth'

    try:
        with VitisHLSSession(executable=ictx.vitishsl_exec, sid=lSessionId, echo=ictx.vivadoHlsEcho) as lConsole:

            # Open the project
            lConsole(f'open_project {ictx.currentproj.name}')
            lConsole(f'open_solution {ictx.vitishls_solution}')
            lConsole('csynth_design')
# 

    except VitisHLSConsoleError as lExc:
        logVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        console.log("ERROR:", style='red')
        console.print(lExc)
        raise click.Abort()

    console.log(f"{ictx.currentproj.name}: Synthesis completed successfully.", style='green')


# ------------------------------------------------------------------------------
def csim(ictx):

    lSessionId = 'csim'

    try:
        with VitisHLSSession(executable=ictx.vitishsl_exec, sid=lSessionId, echo=ictx.vivadoHlsEcho) as lConsole:

            # Open the project
            lConsole(f'open_project {ictx.currentproj.name}')
            lConsole(f'open_solution {ictx.vitishls_solution}')
            lConsole('csim_design')
# 

    except VitisHLSConsoleError as lExc:
        logVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        console.log("ERROR:", style='red')
        console.print(lExc)
        raise click.Abort()

    console.log(f"{ictx.currentproj.name}: Simulation completed successfully.", style='green')


# ------------------------------------------------------------------------------
def cosim(ictx):
    lSessionId = 'cosim'

    try:
        with VitisHLSSession(executable=ictx.vitishsl_exec, sid=lSessionId, echo=ictx.vivadoHlsEcho) as lConsole:

            # Open the project
            lConsole(f'open_project {ictx.currentproj.name}')
            lConsole(f'open_solution {ictx.vitishls_solution}')
            lConsole('cosim_design')
# 

    except VitisHLSConsoleError as lExc:
        logVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        console.log("ERROR:", style='red')
        console.print(lExc)
        raise click.Abort()

    console.log(f"{ictx.currentproj.name}: Cosimulation completed successfully.", style='green')


# ------------------------------------------------------------------------------
def export_ip(ictx, to_component):
    """
    TODO : allow user to choose what export_desing flow to use
    """
    from ..defaults import kTopEntity

    lSessionId = 'export-ip-catalog'
    
    """
    zipfile name = "<vendor>_<lib>_<top>_<versionmajor>_<versionminor>.zip"
    defaults: 
    - vendor = "xilinx.com" -> "xilinx_com"
    - lib = "hls"
    - version = "1.0"
    - ipname = "top_entity"
    """

    reqsettings = {'vendor', 'library', 'version'}

    lDepFileParser = ictx.depParser
    lSettings = ictx.depParser.settings
    lHLSSettings = lDepFileParser.settings.get(_toolset, {})

    if not lHLSSettings or not reqsettings.issubset(lHLSSettings):
        raise RuntimeError(f"Missing variables required to create an ip repository: {', '.join([f'{_toolset}.{s}' for s in reqsettings.difference(lHLSSettings)])}")

    lIPName = lHLSSettings['ipname'] if 'ipname' in lHLSSettings else lSettings.get('top_entity', kTopEntity)
    lIPVendor = lHLSSettings['vendor']
    lIPLib = lHLSSettings['library']
    lIPVersion = lHLSSettings['version']
    lIpRepoName = f"{lIPVendor.replace('.', '_')}_{lIPLib.replace('.', '_')}_{lIPName}_{lIPVersion.replace('.', '_')}"

    # Check if vitis_hls is accessible
    ensure_vitishls(ictx)

    # -- Export the HSL code as a Xilinx IP catalog
    console.log("Exporting IP catalog", style="blue")
    try:
        with VitisHLSSession(executable=ictx.vitishsl_exec, sid=lSessionId, echo=ictx.vivadoHlsEcho) as lConsole:

            # Open the project
            lConsole(f'open_project {ictx.currentproj.name}')
            lConsole(f'open_solution {ictx.vitishls_solution}')
            lConsole(f'export_design -format ip_catalog -ipname {lIPName} -vendor {lHLSSettings["vendor"]} -library {lHLSSettings["library"]} -version "{lHLSSettings["version"]}"')

    except VitisHLSConsoleError as lExc:
        logVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        console.log("ERROR:", style='red')
        console.print(lExc)
        raise click.Abort()


    lIPCatalogDir = join(ictx.currentproj.name, ictx.vitishls_solution, 'impl', 'ip')
    zips = glob.glob(join(lIPCatalogDir, "*.zip"))

    if len(zips) == 0:
        raise RuntimeError(f"IP catalog file not found in {lIPCatalogDir}")
    elif len(zips) > 1:
        raise RuntimeError(f"Multiple IP catalog file found in {lIPCatalogDir}: {zips}")
    lIPCatalogExportPath = zips.pop()
    lIPCatalogName = basename(lIPCatalogExportPath)
    lIPCatalogRoot, _ = splitext(lIPCatalogName)
    lIPCatalogZip = join(ictx.vitishls_prod_path, lIPCatalogName)
    lXciModName = f"{lIPLib}_{lIPName}"

    # -- Generate an XCI file for the IP
    mkdir(ictx.vitishls_prod_path)
    shutil.copy(lIPCatalogExportPath, lIPCatalogZip)

    console.log(f"{ictx.currentproj.name}: HLS IP catalog exported to {lIPCatalogZip}", style='green')
    console.log("Creating XCI file", style="blue")

    # lXilinxPart = f'{lSettings["device_name"]}{lSettings["device_package"]}{lSettings["device_speed"]}'

    # try:
    #     with VivadoSession(sid=lSessionId) as lVivadoConsole:
    #         lVivadoConsole(f'create_project -in_memory -part {lXilinxPart} -force')
    #         lVivadoConsole(f'set_property ip_repo_paths {lIPCatalogDir} [current_project]')
    #         lVivadoConsole('update_ip_catalog -rebuild')
    #         lVivadoConsole('set repo_path [get_property ip_repo_paths [current_project]]')
    #         ip_vlnv_list = lVivadoConsole(f'foreach n [get_ipdefs -filter REPOSITORY==$repo_path] {{ puts "$n" }}')
    #         if len(ip_vlnv_list) > 1:
    #             raise RuntimeError(f"Found more than 1 core in ip catalog! {', '.join(ip_vlnv_list)}")
    #         vlnv = ip_vlnv_list[0]
    #         lVivadoConsole(f'create_ip -vlnv {vlnv} -module_name {lXciModName} -dir {ictx.vitishls_prod_path}')
    #         lVivadoConsole('report_ip_status')

    # except VivadoConsoleError as lExc:
    #     logVivadoConsoleError(lExc)
    #     raise click.Abort()
    # except RuntimeError as lExc:
    #     console.log("ERROR:", style='red')
    #     console.print(lExc)
    #     raise click.Abort()

    lXciGen = HLSIpRepoXciGenerator(lIPCatalogDir, lXciModName, ictx.vitishls_prod_path)

    try:
        with VivadoSession(sid=lSessionId) as lVivadoConsole:
            lXciGen.write(
                lVivadoConsole,
                lDepFileParser.settings,
                lDepFileParser.packages,
                lDepFileParser.commands,
                lDepFileParser.libs,   
            )

    except VivadoConsoleError as lExc:
        logVivadoConsoleError(lExc)
        raise click.Abort()
    except RuntimeError as lExc:
        console.log("ERROR:", style='red')
        console.print(lExc)
        raise click.Abort()


    dest = to_component if to_component is not None else (ictx.currentproj.settings['topPkg'], ictx.currentproj.settings['topCmp'])

    lIPDest = ictx.pathMaker.getPath(*dest, 'iprepo')
    lIPRepoDest = join(lIPDest, lIPCatalogRoot)

    # Use sh.rm instead?
    sh.rm('-rf', lIPRepoDest)
    mkdir(lIPRepoDest)
    from zipfile import ZipFile

    with ZipFile(lIPCatalogZip, 'r') as zipObj:
        zipObj.extractall(lIPRepoDest)
    console.log(f"{lIPCatalogName} unzipped into {lIPRepoDest}")

    shutil.copy(join(ictx.vitishls_prod_path, lXciModName, f'{lXciModName}.xci'), lIPDest)
    console.log(f"{lXciModName}.xci copied to {lIPDest}")
    console.log(f"{ictx.currentproj.name}: Export completed successfully.", style='green')

   
