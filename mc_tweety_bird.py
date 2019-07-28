#!/usr/bin/python2.7
# TODO: Find ways to avoid sending consecutive verbatim tweets.

# Python modules
from signal import signal, SIGTERM
import argparse
import atexit
import multiprocessing
import os
import sys
import time
# Homegrown modules
import logger
import mailer
import tweeter
import tweety_libs

# Variables
# Log File
log = "/home/minecraft/scripts/mc_tweety_bird/mc_tweety_bird.log"
# Paths
mc_path = "/home/minecraft/"
latest_log = mc_path + "logs/latest.log"
death_log = mc_path + "plugins/LogAll/AllDeaths.log"
playerdeath_log = mc_path + "plugins/LogAll/PlayerDeaths.log"
base_folder = "/home/minecraft/scripts/mc_tweety_bird/"
pid_base = "/tmp/tweetybird"
recycle_file = base_folder + "recycle"
tweet_queue_file_name = base_folder + "tweet_queue"
admin_queue_file_name = base_folder + "admin_queue"
mod_queue_file_name = base_folder + "mod_queue"
admin_messages_file_name = base_folder + "admin_messages.txt"
mod_messages_file_name = base_folder + "mod_messages.txt"
excluded_messages_file_name = base_folder + "excluded_messages.txt"
seen_messages_base = base_folder + "seen_messages"
# /Paths
# Mailer settings
recipient = "mbernhardt6@gmail.com"
sender = "mbernhardt6@gmail.com"
# /Mailer Settings
# Number of death messages to keep in state
kept_history = 200
# Number of tweets to send during each pass
tweet_volume = 1
hash_tag = ""
# Time in seconds between log read resets
reset_time = 300

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
parser.add_argument('--admin_messages',
                    dest = 'admin_messages',
                    action = 'store_true',
                    default = False,
                    help = 'Flag to mail admin messages from queue.')
parser.add_argument('--mod_messages',
                    dest = 'mod_messages',
                    action = 'store_true',
                    default = False,
                    help = 'Flag to mail mod messages from queue.')
args = parser.parse_args()


def ReadMessagesFromLog(watch_file_name,
                        mail_queue_file_name,
                        mod_queue_file_name,
                        admin_messages_file_name,
                        mod_messages_file_name,
                        excluded_messages_file_name,
                        seen_messages_base):
  """Read Messages from MC Log and write out to queue file(s) based on filters.

  Args:
    watch_file_name: File name to read messages from.
    mail_queue_file_name: File name to write admin messages for mailing.
    mod_queue_file_name: File name to write mod messages for mailing.
    admin_messages_file_name: Set of admin messages to look for.
    mod_messages_file_name: Set of mod messages to look for.
    excluded_messages_file_name: Set of messsages to ignore.
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
  admin_messages = tweety_libs.ReadFileData(admin_messages_file_name, log)
  mod_messages = tweety_libs.ReadFileData(mod_messages_file_name, log)
  excluded_messages = tweety_libs.ReadFileData(excluded_messages_file_name, log)
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
  last_read = 0

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
        if ((not tweety_libs.StringInSet(line, seen_messages)) and
            (not tweety_libs.StringInSet(line.lower(), excluded_messages))):
          if tweety_libs.StringInSet(line, admin_messages):
            with open(mail_queue_file_name, 'a') as mail_queue:
              mail_queue.write(line)
            seen_messages.add(line)
            logger.logMessage(log, "%s: Message submitted to admin mail queue." %
                thread_name)
          if tweety_libs.StringInSet(line, mod_messages):
            with open(mod_queue_file_name, 'a') as mod_queue:
              mod_queue.write(line)
            seen_messages.add(line)
            logger.logMessage(log, "%s: Message submitted to mod mail queue." %
                thread_name)
      # Reset read position to catch log rollover
      if ((time.time() - start_time) > reset_time):
        logger.logMessage(log, "%s: Reseting log file location. %s lines read."
            % (thread_name, read_count))
        watch_file.close()
        if read_count < last_read:
          logger.logMessage(log, "Suspect %s log roll. Blanking seen messages."
              % thread_name)
          seen_messages.clear()
        watch_file = open(watch_file_name, 'r')
        watch_file.seek(0, 0)
        start_time = time.time()
        last_read = read_count
        read_count = 0
        tweety_libs.WriteFileData(seen_messages_file_name,
            sorted(seen_messages), kept_history)
      # Check for recycle file
      if (os.path.isfile(recycle_file)):
        logger.logMessage(log, "Recycle file detected: %s" % thread_name)
        break
  except KeyboardInterrupt:
    logger.logMessage(log, "Keyboard Interrupt Detected. %s" % thread_name)
  except Exception as e:
    logger.logMessage(log, "WARNING: %s: %s" % (thread_name, e))

  # Write state data and close log file on exit
  tweety_libs.WriteFileData(seen_messages_file_name, sorted(seen_messages),
      kept_history)
  watch_file.close()
  tweety_libs.Cleanup(thread_name, pid_file, log)


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
      # Reset read position to catch log rollover
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
      # Check for recycle file
      if (os.path.isfile(recycle_file)):
        logger.logMessage(log, "Recycle file detected: %s" % thread_name)
        break
  except KeyboardInterrupt:
    logger.logMessage(log, "Keyboard Interrupt Detected. %s" % thread_name)
  except Exception as e:
    logger.logMessage(log, "WARNING: %s: %s" % (thread_name, e))

  # Write state data and close log file on exit
  tweety_libs.WriteFileData(seen_messages_file_name, sorted(seen_messages),
      kept_history)
  watch_file.close()
  tweety_libs.Cleanup(thread_name, pid_file, log)


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
      # Reset read position to catch log rollover
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
      # Check for recycle file
      if (os.path.isfile(recycle_file)):
        logger.logMessage(log, "Recycle file detected: %s" % thread_name)
        break
  except KeyboardInterrupt:
    logger.logMessage(log, "Keyboard Interrupt Detected. %s" % thread_name)
  except Exception as e:
    logger.logMessage(log, "WARNING: %s: %s" % (thread_name, e))

  # Write state data and close log file on exit
  tweety_libs.WriteFileData(seen_messages_file_name, sorted(seen_messages),
      kept_history)
  watch_file.close()
  tweety_libs.Cleanup(thread_name, pid_file, log)


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
      tweeter.SendTweet("%s %s" % (message, hash_tag))
      logger.logMessage(log, "\"%s\" sent to Tweeter." % message)
    except:
      pass
  tweety_libs.WriteFileData(tweet_queue_file_name, tweet_list, 0)


def SendSummaryMail(mail_queue_file_name, mail_type):
  """Mail administrative messages gathered from log files.

  Args:
    mail_queue_file_name: File to pull messages from.
    mail_type: Type of mail being sent.
  """
  timestamp = logger.GetTimeStamp()
  message_list = tweety_libs.ReadFileData(mail_queue_file_name, log)
  if len(message_list) > 0:
    if mail_type == 'admin':
      subject = ("MC Admin Log Summary: %s" % timestamp)
    else:
      subject = ("MC Mod Message: %s" % timestamp)
    mailer.sendMail(recipient, sender, subject,
                    '\r\n'.join(sorted(message_list)))
    logger.logMessage(log, "%s Mail Sent." % mail_type)
    tweety_libs.WriteFileData(mail_queue_file_name, "", 0)


if __name__ == "__main__":
  # Setup signal interrupt
  signal(SIGTERM, lambda signum, stack_frame: exit(1))
  if args.read_messages:
    # read_messages code path
    # Remove recycle file if it exists
    if (os.path.isfile(recycle_file)):
      logger.logMessage(log, "Removing recycle file.")
      try:
        os.remove(recycle_file)
      except:
        logger.logMessage(log, "WARNING: Unable to remove recycle file.")

    # Verify existing pid files
    tweety_libs.VerifyPids(pid_base, log)

    # Setup threads
    p_latest = multiprocessing.Process(target=ReadMessagesFromLog,
        args=(latest_log,
              admin_queue_file_name,
              mod_queue_file_name,
              admin_messages_file_name,
              mod_messages_file_name,
              excluded_messages_file_name,
              seen_messages_base)
        )
    p_alldeaths = multiprocessing.Process(target=ReadDeathMessageLog,
        args=(death_log,
              tweet_queue_file_name,
              seen_messages_base)
        )
    p_playerdeaths = multiprocessing.Process(target=ReadPlayerDeathsLog,
        args=(playerdeath_log,
              tweet_queue_file_name,
              seen_messages_base)
        )

    # Start threads
    p_latest.start()
    # Tweeting functionality is turned off.
    # p_alldeaths.start()
    # p_playerdeaths.start()

  if args.tweet_messages:
    # tweet_messages code path
    TweetDeathMessages(tweet_queue_file_name, tweet_volume)
  if args.admin_messages:
    # admin_messages code path
    SendSummaryMail(admin_queue_file_name, 'admin')
  if args.mod_messages:
    # mod_messages code path
    SendSummaryMail(mod_queue_file_name, 'mod')
  if (not args.read_messages
      and not args.tweet_messages
      and not args.admin_messages
      and not args.mod_messages):
    print "No flags declared."
