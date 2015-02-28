from twython import Twython
from tweeter_auth import *

def SendTweet(message):
  twitter = Twython(app_key, app_secret, oauth_token, oauth_token_secret)
  twitter.update_status(status=message)