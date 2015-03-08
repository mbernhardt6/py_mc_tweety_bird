#!/usr/bin/python2.7
# TODO: Still doesn't catch log rollover correctly

# Python modules
from signal import signal, SIGTERM
import argparse
import atexit
import multiprocessing
import sys
import time
# Homegrown modules
import logger
import tweeter
import tweety_libs

# Variables
log = "/var/log/mc_tweety_bird.log"
mc_path = "/var/games/minecraft/servers/one/"
latest_log = mc_path + "logs/latest.log"
death_log = mc_path + "plugins/LogAll/AllDeaths.log"
base_folder = "/home/mc/python/"
pid_base = "/tmp/tweetybird"
msg_queue_file_name = base_folder + "msg_queue"
death_messages_file_name = base_folder + "death_messages.txt"
seen_messages_base = base_folder + "seen_messages"
# Number of death messages to keep in state
# Should hold more than you would expect to happen on a single log iteration
kept_history = 1000
# Number of tweets to send during each pass
tweet_volume = 1
# Time in seconds between log read resets
reset_time = 800

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


def ReadMessagesFromLog(watch_file_name, queue_file_name,
    death_messages_file_name, seen_messages_base):
  """Read Death Messages from MC Log and write out to queue file.

  Args:
    watch_file_name: File name to read messages from.
    queue_file_name: File name to write messages to for later tweeting.
    death_messages_file_name: Set of messages to look for.
    seen_messages_base: Set of messages to filter against to avoid repeats.
  """
  thread_name = "latest"

  # Setup signal interrupt
  signal(SIGTERM, lambda signum, stack_frame: exit(1))

  # Verify script is not already running
  # SetPid will exit if thread is already running
  pid_file = tweety_libs.SetPid(thread_name, pid_base, log)
  logger.logMessage(log, "%s: Starting thread." % thread_name)

  # Read filter and state data
  death_messages = tweety_libs.ReadFileData(death_messages_file_name, log)
  seen_messages_file_name = seen_messages_base + "_" + thread_name
  seen_messages = tweety_libs.ReadFileData(seen_messages_file_name, log)

  # Set cleanup
  atexit.register(tweety_libs.Cleanup, thread_name, pid_file, log)
  atexit.register(tweety_libs.WriteFileData, seen_messages_file_name,
      sorted(seen_messages), kept_history)

  # Open log file for reading
  watch_file = open(watch_file_name, 'r')
  start_time = time.time()
  read_count = 0

  # Start listening
  try:
    while 1:
      where = watch_file.tell()
      line = watch_file.readline()
      if not line:
        time.sleep(1)
        watch_file.seek(where)
      else:
        read_count += 1
        if (not tweety_libs.StringInSet(line, seen_messages)
            and tweety_libs.StringInSet(line, death_messages)):
          with open(queue_file_name, 'a') as message_queue:
            message_queue.write(line.split('[Server thread/INFO]:')[1].strip() +
                "\n")
          seen_messages.add(line)
          logger.logMessage(log, "%s: Message submitted to tweet queue." %
              thread_name)
      # Reset read position every hour to catch log rollover
      if ((time.time() - start_time) > reset_time):
        logger.logMessage(log, "%s: Reseting log file location. %s lines read."
            % (thread_name, read_count))
        watch_file.close()
        watch_file = open(watch_file_name, 'r')
        watch_file.seek(0, 0)
        start_time = time.time()
        read_count = 0
        tweety_libs.WriteFileData(seen_messages_file_name,
            sorted(seen_messages), kept_history)
  except KeyboardInterrupt:
    tweety_libs.WriteFileData(seen_messages_file_name, sorted(seen_messages),
        kept_history)
    tweety_libs.Cleanup(thread_name, pid_file, log)
  except Exception as e:
    logger.logMessage(log, "WARNING: %s: %s" % (thread_name, e))

  # Write state data and close log file on exit
  tweety_libs.WriteFileData(seen_messages_file_name, sorted(seen_messages),
      kept_history)
  watch_file.close()


def ReadDeathMessageLog(watch_file_name, queue_file_name, seen_messages_base):
  """Read Messages from AllDeath.log from LogAll plugin.

  Args:
    watch_file_name: File name to read messages from.
    queue_file_name: File name to write messages to for later tweeting.
    seen_messages_base: Set of messages to filter against to avoid repeats.
  """
  thread_name = "alldeaths"

  # Setup signal interrupt
  signal(SIGTERM, lambda signum, stack_frame: exit(1))

  # Verify script is not already running
  # SetPid will exit if thread is already running
  pid_file = tweety_libs.SetPid(thread_name, pid_base, log)
  logger.logMessage(log, "%s: Starting thread." % thread_name)

  # Read state data
  seen_messages_file_name = seen_messages_base + "_" + thread_name
  seen_messages = tweety_libs.ReadFileData(seen_messages_file_name, log)

  # Set cleanup
  atexit.register(tweety_libs.Cleanup, thread_name, pid_file, log)
  atexit.register(tweety_libs.WriteFileData, seen_messages_file_name,
      sorted(seen_messages), kept_history)

  # Open log file for reading
  watch_file = open(watch_file_name, 'r')
  start_time = time.time()
  read_count = 0

  # Start listening
  try:
    while 1:
      where = watch_file.tell()
      line = watch_file.readline()
      if not line:
        time.sleep(1)
        watch_file.seek(where)
      else:
        read_count += 1
        if not tweety_libs.StringInSet(line, seen_messages):
          # Validate AllDeaths Message
          if line.split(" ")[2].strip() != line.split(" ")[4].strip():
            with open(queue_file_name, 'a') as message_queue:
              message_queue.write(line.split(":")[3].strip().replace("killed",
                  "killed a") + "\n")
            seen_messages.add(line)
            logger.logMessage(log, "%s: Message submitted to tweet queue." %
                thread_name)
      # Reset read position every hour to catch log rollover
      if ((time.time() - start_time) > reset_time):
        logger.logMessage(log, "%s: Reseting log file location. %s lines read."
            % (thread_name, read_count))
        watch_file.close()
        watch_file = open(watch_file_name, 'r')
        watch_file.seek(0, 0)
        start_time = time.time()
        read_count = 0
        tweety_libs.WriteFileData(seen_messages_file_name,
            sorted(seen_messages), kept_history)
  except KeyboardInterrupt:
    tweety_libs.WriteFileData(seen_messages_file_name, sorted(seen_messages),
        kept_history)
    tweety_libs.Cleanup(thread_name, pid_file, log)
  except Exception as e:
    logger.logMessage(log, "WARNING: %s: %s" % (thread_name, e))

  # Write state data and close log file on exit
  tweety_libs.WriteFileData(seen_messages_file_name, sorted(seen_messages),
      kept_history)
  watch_file.close()


def TweetDeathMessages(queue_file_name, num_tweets):
  """Tweet defined number of messages from queue file.

  Args:
    queue_file_name: File to pull tweets from.
    num_tweets: Number of tweets to send in a single instance.
  """
  tweet_list = sorted(tweety_libs.ReadFileData(queue_file_name, log))
  for x in range(0, num_tweets):
    try:
      # Read message and remove from queue
      message = tweet_list.pop(0)
      tweeter.SendTweet(message)
      logger.logMessage(log, "\"%s\" sent to Tweeter." % message)
    except:
      pass
  tweety_libs.WriteFileData(queue_file_name, tweet_list, 0)


if __name__ == "__main__":
  # Setup signal interrupt
  signal(SIGTERM, lambda signum, stack_frame: exit(1))
  if args.read_messages:
    # read_messages code path
    # Verify existing pid files
    tweety_libs.VerifyPids(pid_base, log)

    # Setup threads
    p_latest = multiprocessing.Process(target=ReadMessagesFromLog, args=(latest_log,
        msg_queue_file_name, death_messages_file_name, seen_messages_base))
    p_alldeaths = multiprocessing.Process(target=ReadDeathMessageLog, args=(death_log,
        msg_queue_file_name, seen_messages_base))

    # Start threads
    p_latest.start()
    p_alldeaths.start()
  if args.tweet_messages:
    # tweet_messages code path
    TweetDeathMessages(msg_queue_file_name, tweet_volume)
  if not args.read_messages and not args.tweet_messages:
    print "No flags declared."
