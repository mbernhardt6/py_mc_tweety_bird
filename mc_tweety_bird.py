#!/usr/bin/python2.7
# TODO: Still doesn't catch log rollover correctly

# Python modules
from signal import signal, SIGTERM
import atexit
import argparse
import os
import sys
import time
# Homegrown modules
import filer
import logger
import tweeter

# Variables
log = "/var/log/mc_tweety_bird.log"
mc_log = "/var/games/minecraft/servers/one/logs/latest.log"
base_folder = "/home/mc/python/"
msg_queue_file = base_folder + "msg_queue"
death_messages_file = base_folder + "death_messages.txt"
seen_messages_file = base_folder + "seen_messages"
# Number of death messages to keep in state
# Should hold more than you would expect to happen on a single log iteration
tweet_history = 1000
# Number of tweets to send during each pass
tweet_volume = 1
# Time in seconds between log read resets
reset_time = 3600

# Parse Command Line Arguments
parser = argparse.ArgumentParser(description='Process command line flags.')
parser.add_argument('--read_messages',
                    dest='read_messages',
                    action='store_true',
                    default=False,
                    help='Flag to read messages from log to queue.')
parser.add_argument('--tweet_messages',
                    dest='tweet_messages',
                    action='store_true',
                    default=False,
                    help='Flag to Tweet messages from queue.')
args = parser.parse_args()


def StringInSet(test_string, test_set):
  """Check if a string contains any string from a set of strings.

  Args:
    test_string: String to check against.
    test_set: Set to test against.

  Returns:
    Boolean if one of set is found or not.
  """
  for item in test_set:
    if item in test_string:
      return True
  return False


def ReadFileData(target_file_name):
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


def ReadDeathMessagesFromLog(log_file_name, queue_file_name,
    death_messages_file, seen_messages_file):
  """Read Death Messages from MC Log and write out to queue file.

  Args:
    log_file_name: File name to read messages from.
    queue_file_name: File name to write messages to for later tweeting.
    death_messages: Set of messages to look for.
    seen_messages: Set of messages to filter against to avoid repeats.
  """
  # Read filter and state data
  death_messages = ReadFileData(death_messages_file)
  seen_messages = ReadFileData(seen_messages_file)
  # Open log file for reading
  log_file = open(log_file_name, 'r')
  start_time = time.time()
  read_count = 0
  try:
    while 1:
      where = log_file.tell()
      line = log_file.readline()
      if not line:
        time.sleep(1)
        log_file.seek(where)
      else:
        read_count += 1
        if (not StringInSet(line, seen_messages)
            and StringInSet(line, death_messages)):
          with open(queue_file_name, 'a') as message_queue:
            message_queue.write(line)
          seen_messages.add(line)
          logger.logMessage(log, "Message submitted to tweet queue.")
      # Reset read position every hour to catch log rollover
      if ((time.time() - start_time) > reset_time):
        logger.logMessage(log, "Reseting log file location. %s line(s) read." %
            read_count)
        log_file.close()
        log_file = open(log_file_name, 'r')
        log_file.seek(0, 0)
        start_time = time.time()
        read_count = 0
        WriteFileData(seen_messages_file, sorted(seen_messages), tweet_history)
  except:
    logger.logMessage(log, "WARNING: Error detected while reading messages.")
  # Write state data and close log file on exit
  WriteFileData(seen_messages_file, sorted(seen_messages), tweet_history)
  log_file.close()


def TweetDeathMessages(queue_file_name, num_tweets):
  """Tweet defined number of messages from queue file.

  Args:
    queue_file_name: File to pull tweets from.
    num_tweets: Number of tweets to send in a single instance.
  """
  tweet_list = sorted(ReadFileData(queue_file_name))
  for x in range(0, num_tweets):
    try:
      # Read message and remove from queue
      raw_message = tweet_list.pop(0)
      # Format message for tweet
      message = raw_message.split('[Server thread/INFO]:')[1].strip()
      tweeter.SendTweet(message)
      logger.logMessage(log, "Update sent to Tweeter.")
    except:
      logger.logMessage(log, "Unable to find message to tweet.")
  WriteFileData(queue_file_name, tweet_list, 0)


def Cleanup():
  """pid file cleanup for abnormal script termination.

  Called with no arguments, removes pid file when script is abnormally
  terminated.
  """
  logger.logMessage(log, "WARNING: Abnormal termination detected.")
  try:
    os.unlink(pidfile)
    logger.logMessage(log, "pid file successfully removed.")
  except:
    logger.logMessage(log, "WARNING: Unable to remove pid file.")


if __name__ == "__main__":
  # Setup signal interrupt
  signal(SIGTERM, lambda signum, stack_frame: exit(1))
  if args.read_messages:
    # read_messages code path
    # Set pid details
    pid = str(os.getpid())
    pidfile = "/tmp/tweetybird.pid"
    # Verify script is not already running
    if os.path.isfile(pidfile):
      logger.logMessage(log, "%s exists, exiting." % pidfile)
    else:
      # Set pid file
      file(pidfile, 'w').write(pid)
      # Set cleanup for abnormal termination
      atexit.register(Cleanup)
      logger.logMessage(log, "Reading messages from log to queue.")
      ReadDeathMessagesFromLog(mc_log, msg_queue_file, death_messages_file,
          seen_messages_file)
  if args.tweet_messages:
    # tweet_messages code path
    TweetDeathMessages(msg_queue_file, tweet_volume)