import datetime
import time


def GetTimeStamp():
  """Simple function to return a formatted timestamp.

  Returns:
    Formatted time stamp.
  """
  ts = time.time()
  return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def logMessage(file, message):
  """Logging function.

  Args:
    file: Log file to write to.
    message: Message to write to log.
  """
  timestamp = GetTimeStamp()
  with open(file, "a") as logfile:
    logfile.write("%s - %s\r\n" % (timestamp, message))