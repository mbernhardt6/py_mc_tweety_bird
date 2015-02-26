#!/usr/bin/python2.7
#TODO: Need to find and integrate a Twitter Module

#Python modules
import argparse
#Homegrown modules
import filer
import logger

#Variables
log = "/var/log/mc_tweety_bird.log"
mc_log = "/var/games/minecraft/servers/one/logs/latest.log"
base_folder = "/home/mc/python/"
msg_queue = base_folder + "msg_queue"
death_messages_file = base_folder + "death_messages.txt"
seen_messages_file = base_folder = "seen_messages"
tweet_history = 100
tweet_volume = 1

#Parse Command Line Arguments
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

def ReadFileData(target_file_name):
  """Read data from a file ignoring commented out lines.

  Args:
    target_file_name: Filename of file to read.

  Returns:
    Contents of file as a set.
  """
  file_contents = set()
  target_file = open(target_file_name, 'r')
  for line in target_file:
    if line.encode('utf-8')[:1] not '#':
      file_contents.add(line.encode('utf-8'))
  target_file.close()
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

def ReadDeathMessagesFromLog(target_file_name, queue_file_name, death_messages,
    seen_messages):
  """Read Death Messages from MC Log and write out to queue file.

  Args:
    target_file_name: File name to read messages from.
    queue_file_name: File name to write messages to for later tweeting.
    death_messages: Set of messages to look for.
    seen_messages: Set of messages to filter against to avoid repeats.
  """
  message_queue = set()
  log_messages = ReadFileData(target_file_name)
  for message in log_messages:
    if (message not in seen_messages) and (message in death_messages):
      message_queue.add(message)
  WriteFileData(queue_file_name, message_queue, 0)

def TweetDeathMessages(queue_file_name, num_tweets):
  """Tweet defined number of messages from queue file.

  Args:
    queue_file_name: File to pull tweets from.
    num_tweets: Number of tweets to send in a single instance.
  """
  tweet_list = ReadFileData(queue_file_name)
  for x in range(0, num_tweets):
    message = tweet_list.popleft()
    #TODO: Add actual tweet logic.
  WriteFileData(queue_file_name, tweet_list, 0)

if __name__ == "__main__":
  death_messages = ReadFileData(death_messages_file)
  seen_messages = ReadFileData(seen_messages_file)
  if args.read_messages:
    logger.LogMessage("Reading messages from log to queue.", log)
    ReadDeathMessagesFromLog(mc_log, msg_queue, death_messages, seen_messages)
  if args.tweet_messages:
    logger.LogMessage("Tweeting message(s) from queue.", log)
    TweetDeathMessages(msg_queue, tweet_volume)
  WriteFileData(seen_messages_file, seen_messages, tweet_history)