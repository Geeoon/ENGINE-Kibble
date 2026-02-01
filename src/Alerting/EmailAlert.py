"""
EmailAlert derived class from Alert
https://realpython.com/python-send-email/#make-a-csv-file-with-relevant-personal-info
"""

# TODO: Modify kibblealert@gmail.com google account to 
# allow apps to access it

from .Alert import Alert
from Logging.Logger import LogLevel

import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailAlert(Alert):
    """
    EmailAlert class for alerting
    """
    def __init__(self):
        pass

    def alert(self, data: dict, level: LogLevel) -> bool: 
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"
        password = input("Type your password and press enter: ") # TODO: Use environment variables

        sender_email = "kibblealert@gmail.com"
        receiver_email = "your@gmail.com" # Add email addresses here
        message = """\
            Subject: Test email
            
            Level: {level}
            Data: {data}
            """

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)
        return True

