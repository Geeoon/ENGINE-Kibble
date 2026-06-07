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
    def __init__(self, sender_email: str="kibblealert@gmail.com", receiver_email: str="kibblealert@gmail.com"):
        self.sender_email = sender_email
        self.receiver_email = receiver_email

    def alert(self, data: dict, level: LogLevel) -> bool: 
        """
        Send an email alert
        
        :param data: the data to alert on
        :param level: the log level
        :return: True on success, False on error
        """
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"
        password = os.getenv('EMAIL_PASSWD')

        message = MIMEMultipart("alternative")
        message["Subject"] = "Kibble Alert"
        message["From"] = self.sender_email
        message["To"] = self.receiver_email
    
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
            server.login(self.sender_email, password)
            server.sendmail(self.sender_email, self.receiver_email, message.as_string())
        return True

