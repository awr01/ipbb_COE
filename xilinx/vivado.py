import logging
import pexpect
import sys
import re
import collections
import subprocess
import os.path

#------------------------------------------------
# This is for when python 2.7 will become available
# pexpect.spawn(...,preexec_fn=on_parent_exit('SIGTERM'))
import signal
from ctypes import cdll

# Constant taken from http://linux.die.net/include/linux/prctl.h
PR_SET_PDEATHSIG = 1

class PrCtlError(Exception):
    pass

def on_parent_exit(signame):
    """
    Return a function to be run in a child process which will trigger
    SIGNAME to be sent when the parent process dies
    """
    signum = getattr(signal, signame)
    def set_parent_exit_signal():
        # http://linux.die.net/man/2/prctl
        result = cdll['libc.so.6'].prctl(PR_SET_PDEATHSIG, signum)
        if result != 0:
            raise PrCtlError('prctl failed with error code %s' % result)
    return set_parent_exit_signal
#------------------------------------------------


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class Batch(object):
  """docstring for Batch"""

  reInfo = re.compile('^INFO:')
  reWarn = re.compile('^WARNING:')
  reError = re.compile('^ERROR:')

  def __init__(self, script):
    super(Batch, self).__init__()

    lBasename, lExt = os.path.splitext(script)

    if lExt != '.tcl':
      raise RuntimeError('Bugger off!!!')

    self._script = script
    self._log = 'vivado_{0}.log'.format(lBasename)

    cmd = 'vivado -mode batch -source {0} -log {1} -nojournal'.format(self._script, self._log)
    process = subprocess.Popen(cmd.split())
    process.wait()

    self.errors = []
    self.info = []
    self.warnings = []

    with  open(self._log) as lLog:
      for i,l in enumerate(lLog):
        if self.reError.match(l): self.errors.append( (i,l) )
        elif self.reWarn.match(l): self.warnings.append( (i,l) )
        elif self.reInfo.match(l): self.info.append( (i,l) )
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class ConsoleError(Exception):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
        command -- input command in which the error occurred
    """

    def __init__(self, errors, command):
        self.errors = errors
        self.command = command
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
class Console(object):
  """docstring for Vivado"""

  __reCharBackspace = re.compile(".\b")
  __reError = re.compile('^ERROR:')
  
  #--------------------------------------------------------------
  def __init__(self):
    super(Console, self).__init__()
    self._log = logging.getLogger('Vivado')
    self._log.debug('Starting Vivado')
    self._me = pexpect.spawn('vivado -mode tcl',maxread=1)
    self._me.logfile = sys.stdout
    self._me.delaybeforesend = 0.00 #1
    self.__expectPrompt()
    self._log.debug('Vivado up and running')
    # Method mapping
    isAlive = self._me.isalive

  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def __del__(self):
    self.quit()
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def quit(self):
    # Return immediately of already dead
    if not self._me.isalive():
      self._log.debug('Vivado has already been stopped')
      return

    self._log.debug('Shutting Vivado down')
    try:
      self.execute('quit')
    except pexpect.ExceptionPexpect as e:
      pass

    # Just in case
    self._me.terminate(True)
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def __send(self, aText):

    self._me.sendline(aText)
    #--------------------------------------------------------------
    # Hard check: First line of output must match the injected command
    self._me.expect(['\r\n',pexpect.EOF])
    lCmdRcvd = self.__reCharBackspace.sub('',self._me.before)
    lCmdSent = aText
    if lCmdRcvd != lCmdSent:
      #--------------------------------------------------------------
      # Find where the 2 strings don't match
      print len(lCmdRcvd), len(lCmdSent)
      for i in xrange(min(len(lCmdRcvd), len(lCmdSent))):
          r = lCmdRcvd[i]
          s = lCmdSent[i]
          # print i, '\t', r, ord(r), ord(r) > 128, '\t', s, ord(s), ord(s) > 128 
          print i, '\t', r, s, r==s, ord(r)

      print ''.join([str(i%10) for i in xrange(len(lCmdRcvd))])
      print lCmdRcvd
      print ''.join([str(i%10) for i in xrange(len(lCmdSent))])
      print lCmdSent
      #--------------------------------------------------------------
      raise RuntimeError('Command and first output line don\'t match Sent=\'{0}\', Rcvd=\'{1}\''.format(lCmdSent,lCmdRcvd))
    #--------------------------------------------------------------

  def __expectPrompt(self, aMaxLen=100):
    # lExpectList = ['\r\n','Vivado%\t', 'ERROR:']
    lCpl = self._me.compile_pattern_list(['\r\n','Vivado%\t'])
    lIndex = None
    lBuffer = collections.deque([],aMaxLen)
    lErrors = []

    #--------------------------------------------------------------
    while True:
      # Search for newlines, prompt, end-of-file
      # lIndex = self._me.expect(['\r\n','Vivado%\t', 'ERROR:', pexpect.EOF])
      lIndex = self._me.expect_list(lCpl)
      # print '>',self._me.before


      #----------------------------------------------------------
      # Break if prompt 
      if lIndex == 1:
        break
      #----------------------------------------------------------

      # Store the output in the circular buffer
      lBuffer.append(self._me.before)

      if self.__reError.match(self._me.before):
        lErrors.append(self._me.before)
    #--------------------------------------------------------------

    return lBuffer,(lErrors if lErrors else None)
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def execute(self, aCmd, aMaxLen=1):
    if not isinstance(aCmd,str):
      raise TypeError('expected string')

    self.__send(aCmd)
    lBuffer,lErrors = self.__expectPrompt(aMaxLen)
    print lBuffer, lErrors
    import pdb; pdb.set_trace()
    if lErrors is not None:
      raise ConsoleError(lErrors, aCmd)
    return list(lBuffer)
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def executeMany(self, aCmds, aMaxLen=1):
    if not isinstance(aCmd,list):
      raise TypeError('expected list')

    lOutput = []
    for lCmd in lCmds:
      self.__send(lCmd)
      lOutput.extend(self.__expectPrompt(aMaxLen))
    return lOutput
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def openHw(self):
    return self.execute('open_hw')
  #--------------------------------------------------------------
      
  #--------------------------------------------------------------
  def connect(self,uri):
    return self.execute('connect_hw_server -url %s' % uri)
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def getHwTargets(self):
    return self.execute('get_hw_targets')[0].split()
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def openHwTarget(self, target):
    return self.execute('open_hw_target {{{0}}}'.format(target))
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def getHwDevices(self):
      return self.execute('get_hw_devices')[0].split()
  #--------------------------------------------------------------

  #--------------------------------------------------------------
  def programDevice(self, device, bitfile):
      from os.path import abspath, normpath

      bitpath = abspath(normpath(bitfile))

      self._log.debug('Programming %s with %s',device, bitfile)

      self.execute('current_hw_device {0}'.format(device))
      self.execute('refresh_hw_device -update_hw_probes false [current_hw_device]')
      self.execute('set_property PROBES.FILE {{}} [current_hw_device]')
      self.execute('set_property PROGRAM.FILE {{{0}}} [current_hw_device]'.format(bitpath))
      self.execute('program_hw_devices [current_hw_device]')
  #--------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

