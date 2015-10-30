import smtplib
from gmail_auth import *
from simplecrypt import decrypt

def sendMail(recipient, sender, subject, message):
  """Wrapper to send mail.

  Args:
    recipient: Recipient of the message.
    sender: Sender of the message.
    subject: Subject of the message.
    message: Message body.
  """
  host = "smtp.gmail.com:587"

  body = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (sender, recipient,
      subject, message)

  password = decrypt('password', ciphertext)

  smtpObj = smtplib.SMTP(host)
  smtpObj.starttls()
  smtpObj.login(username,password)
  smtpObj.sendmail(sender, recipient, body)
  smtpObj.quit()
