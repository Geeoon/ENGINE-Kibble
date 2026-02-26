"""
EmailAlert derived class from Alert
"""


# TODO: Decide the structure of the email alert
import os
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from Kibble.Alerting import Alert
from Kibble.Logging import LogLevel

class EmailAlert(Alert):
    """
    EmailAlert class for alerting
    """
    def __init__(self):
        pass

    def alert(self, data: dict, level: LogLevel) -> bool: 
        """
        Send an email alert
        
        :param data: the data to alert on
        :type data: dict
        :param level: the log level
        :type level: LogLevel
        :return: True on success, False on error
        :rtype: bool
        """
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"
        password = os.getenv('EMAIL_PASSWD')

        sender_email = "kibblealert@gmail.com"
        receiver_email = "kibblealert@gmail.com"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Kibble Alert"
        message["From"] = sender_email
        message["To"] = receiver_email
    
        text = f"""
            Kibble Alert:
            {data}
            {level.name}
            """
        html = f"""
            <html>
            <body>
                <h1>Kibble Alert</h1>
                <p>{data}</p>
                <p>{level.name}</p>
            </body>
            </html>
            """
        
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        
        message.attach(part1)
        message.attach(part2)
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        return True

