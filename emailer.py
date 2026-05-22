"""Send an HTML email via Gmail SMTP using an App Password."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_ADDRESS = "abakakayan@gmail.com"
RECIPIENTS = ["abakakayan@gmail.com", "ky337@rutgers.edu"]
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_newsletter(html_body: str, subject: str, app_password: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(RECIPIENTS)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_ADDRESS, app_password)
        server.sendmail(GMAIL_ADDRESS, RECIPIENTS, msg.as_string())
