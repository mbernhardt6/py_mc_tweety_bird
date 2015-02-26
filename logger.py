import datetime
import time

def logMessage(file, message):
  ts = time.time()
  timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
  with open(file, "a") as logfile:
    logfile.write("%s - %s\r\n" % (timestamp, message))