import smtplib

def sendMail(recipient, sender, subject, message):
  """Wrapper to send mail.

  Args:
    recipient: Recipient of the message.
    sender: Sender of the message.
    subject: Subject of the message.
    message: Message body.
  """
  host = "mail.transcendedlife.local"

  body = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (sender, recipient,
      subject, message)

  smtpObj = smtplib.SMTP(host)
  smtpObj.sendmail(sender, recipient, body)