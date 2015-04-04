#!/usr/bin/python2.7
# TODO: Find ways to avoid sending consecutive verbatim tweets.

# Python modules
from signal import signal, SIGTERM
import argparse
import atexit
import multiprocessing
import sys
import time
# Homegrown modules
import logger
import mailer
import tweeter
import tweety_libs

# Variables
# Paths
log = "/var/log/mc_tweety_bird.log"
mc_path = "/var/games/minecraft/servers/one/"
latest_log = mc_path + "logs/latest.log"
death_log = mc_path + "plugins/LogAll/AllDeaths.log"
playerdeath_log = mc_path + "plugins/LogAll/PlayerDeaths.log"
base_folder = "/home/mc/python/"
pid_base = "/tmp/tweetybird"
tweet_queue_file_name = base_folder + "tweet_queue"
mail_queue_file_name = base_folder + "mail_queue"
death_messages_file_name = base_folder + "death_messages.txt"
admin_messages_file_name = base_folder + "admin_messages.txt"
avoid_messages_file_name = base_folder + "avoid_messages.txt"
seen_messages_base = base_folder + "seen_messages"
# /Paths
# Mailer settings
recipient = "mark@transcendedlife.local"
sender = "mortimer@transcendedlife.local"
# /Mailer Settings
# Number of death messages to keep in state
# Should hold more than you would expect to happen on a single log iteration
kept_history = 1000
# Number of tweets to send during each pass
tweet_volume = 1
# Time in seconds between log read resets
reset_time = 900

# Parse Command Line Arguments
parser = argparse.ArgumentParser(description = 'Process command line flags.')
parser.add_argument('--read_messages',
                    dest = 'read_messages',
                    action = 'store_true',
                    default = False,
                    help = 'Flag to read messages from log to queue.')
parser.add_argument('--tweet_messages',
                    dest = 'tweet_messages',
                    action = 'store_true',
                    default = False,
                    help = 'Flag to Tweet messages from queue.')
parser.add_argument('--mail_messages',
                    dest = 'mail_messages',
                    action = 'store_true',
                    default = False,
                    help = 'Flag to mail messages from queue.')
args = parser.parse_args()


def ReadMessagesFromLog(watch_file_name, mail_queue_file_name,
    admin_messages_file_name, seen_messages_base):
  """Read Messages from MC Log and write out to queue file(s) based on filters.

  Args:
    watch_file_name: File name to read messages from.
    mail_queue_file_name: File name to write admin messages for mailing.
    admin_messages_file_name: Set of admin messages to look for.
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
  admin_messages = tweety_libs.ReadFileData(admin_messages_file_name, log)
  seen_messages_file_name = seen_messages_base + "_" + thread_name
  seen_messages = tweety_libs.ReadFileData(seen_messages_file_name, log)
  avoid_messages = tweety_libs.ReadFileData(avoid_messages_file_name, log)

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
            and tweety_libs.StringInSet(line, admin_messages)):
          with open(mail_queue_file_name, 'a') as mail_queue:
            mail_queue.write(line)
          seen_messages.add(line)
          logger.logMessage(log, "%s: Message submitted to mail queue." %
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


def ReadDeathMessageLog(watch_file_name, tweet_queue_file_name,
    seen_messages_base):
  """Read Messages from AllDeath.log from LogAll plugin.

  Args:
    watch_file_name: File name to read messages from.
    tweet_queue_file_name: File name to write messages to for later tweeting.
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
            with open(tweet_queue_file_name, 'a') as tweet_queue:
              tweet_queue.write(line.split(":")[3].strip().replace("killed",
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


def ReadPlayerDeathsLog(watch_file_name, tweet_queue_file_name,
    seen_messages_base):
  """Read Messages from PlayerDeaths.log from LogAll plugin.

  Args:
    watch_file_name: File name to read messages from.
    tweet_queue_file_name: File name to write messages to for later tweeting.
    seen_messages_base: Set of messages to filter against to avoid repeats.
  """
  thread_name = "playerdeaths"

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
          with open(tweet_queue_file_name, 'a') as tweet_queue:
            tweet_queue.write(line.split(":")[3].strip() + "\n")
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


def TweetDeathMessages(tweet_queue_file_name, num_tweets):
  """Tweet defined number of messages from queue file.

  Args:
    tweet_queue_file_name: File to pull tweets from.
    num_tweets: Number of tweets to send in a single instance.
  """
  tweet_list = sorted(tweety_libs.ReadFileData(tweet_queue_file_name, log))
  for x in range(0, num_tweets):
    try:
      # Read message and remove from queue
      message = tweet_list.pop(0)
      tweeter.SendTweet(message)
      logger.logMessage(log, "\"%s\" sent to Tweeter." % message)
    except:
      pass
  tweety_libs.WriteFileData(tweet_queue_file_name, tweet_list, 0)


def SendSummaryMail(mail_queue_file_name):
  """Mail administrative messages gathered from log files.

  Args:
    mail_queue_file_name: File to pull messages from.
  """
  timestamp = logger.GetTimeStamp()
  message_list = tweety_libs.ReadFileData(mail_queue_file_name, log)
  if len(message_list) > 0:
    mailer.sendMail(recipient, sender, "Daily MC Log Summary: %s" %
        timestamp, '\r\n'.join(message_list))
    logger.logMessage(log, "Admin Mail Sent.")
    tweety_libs.WriteFileData(mail_queue_file_name, "", 0)


if __name__ == "__main__":
  # Setup signal interrupt
  signal(SIGTERM, lambda signum, stack_frame: exit(1))
  if args.read_messages:
    # read_messages code path
    # Verify existing pid files
    tweety_libs.VerifyPids(pid_base, log)

    # Setup threads
    p_latest = multiprocessing.Process(target=ReadMessagesFromLog,
        args=(latest_log, mail_queue_file_name, admin_messages_file_name,
        seen_messages_base))
    p_alldeaths = multiprocessing.Process(target=ReadDeathMessageLog,
        args=(death_log, tweet_queue_file_name, seen_messages_base))
    p_playerdeaths = multiprocessing.Process(target=ReadPlayerDeathsLog,
        args=(playerdeath_log, tweet_queue_file_name, seen_messages_base))

    # Start threads
    p_latest.start()
    p_alldeaths.start()
    p_playerdeaths.start()

  if args.tweet_messages:
    # tweet_messages code path
    TweetDeathMessages(tweet_queue_file_name, tweet_volume)
  if args.mail_messages:
    # mail_messages code path
    SendSummaryMail(mail_queue_file_name)
  if (not args.read_messages and not args.tweet_messages and not
      args.mail_messages):
    print "No flags declared."
