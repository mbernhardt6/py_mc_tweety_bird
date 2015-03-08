# Python modules
import glob
import os
import sys
# Homegrown modules
import filer
import logger


def StringInSet(test_string, test_set):
  """Check if a string contains any string from a set of strings.

  Args:
    test_string: String to check against.
    test_set: Set to test against.

  Returns:
    Boolean if one of set is found or not.
  """
  for item in test_set:
    if len(item) > 0:
      if item in test_string:
        return True
  return False


def ReadFileData(target_file_name, log):
  """Read data from a file ignoring commented out lines.

  Args:
    target_file_name: Filename of file to read.

  Returns:
    Contents of file as a set.
  """
  file_contents = set()
  try:
    target_file = open(target_file_name, 'r')
    for line in target_file:
      if line.encode('utf-8')[:1] != '#':
        file_contents.add(line.encode('utf-8').replace('\n', ''))
    target_file.close()
  except:
    logger.logMessage(log, "WARNING: Unspecified error processing %s" %
        target_file_name)
  return file_contents


def WriteFileData(target_file_name, file_contents, line_count):
  """Write data to a file.

  Args:
    file_contents: Content to be written to file as set.
    target_file_name: Filename of file to write.
    line_count: Number of files at end of file to retain. 0 skips trimming file.
  """
  target_file = open(target_file_name, 'w')
  for line in file_contents:
    target_file.write(line + '\n')
  target_file.close()
  if line_count > 0:
    filer.tailFile(target_file_name, line_count)


def SetPid(thread_name, pid_base, log):
  """Function to handle cehcking and setting pid files.

  If pid file doesn't exist this function will set it and return the path to the
  parent script. If the pid file already exists this function will exit out of
  the script.

  Args:
    thread_name: Identifier for each thread/function.

  Returns:
    path of pid file.
  """
  pid = str(os.getpid())
  pid_file = pid_base + "_" + thread_name + ".pid"
  if os.path.isfile(pid_file):
    logger.logMessage(log, "%s exists, exiting." % pid_file)
    sys.exit()
  else:
    file(pid_file, 'w').write(pid)
    return pid_file


def Cleanup(thread_name, pid_file, log):
  """pid file cleanup for abnormal script termination.

  Args:
    thread_name: Human readable name for thread being cleaned up.
    pid_file: File to check during cleanup.
  """
  logger.logMessage(log, "%s: Starting cleanup." % thread_name)
  try:
    os.unlink(pid_file)
    logger.logMessage(log, "%s pid file successfully removed." % thread_name)
  except:
    logger.logMessage(log, "WARNING: Unable to remove %s pid file." %
        thread_name)


def VerifyPids(pid_base, log):
  """Find pid's from pid_files and check if processes are still running.

  Remove pid_files for any processes that are no longer active.

  Args:
    pid_base: Path and beginning of pid_file used in setting pid_files.
    log: Log file location.
  """
  pid_wildcard = pid_base + "_*.pid"
  for pid_file in glob.glob(pid_wildcard):
    pid = ReadFileData(pid_file, log)
    try:
      os.getpgid(int(list(pid)[0]))
    except:
      try:
        os.unlink(pid_file)
      except:
        pass