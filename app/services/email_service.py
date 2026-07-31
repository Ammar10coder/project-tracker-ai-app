import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from app import config


def send_email_with_pdf(pdf_path="daily_report.pdf", recipient_email=None):
    """Sends the generated PDF dashboard as an email attachment via Gmail SMTP."""
    cfg = config.load()
    sender_email = cfg.get("GMAIL_USER")
    sender_password = cfg.get("GMAIL_APP_PASSWORD")

    if not recipient_email:
        recipient_email = cfg.get("REPORT_RECIPIENT_EMAIL") or sender_email

    if not sender_email or not sender_password:
        print("Skipped email dispatch: Gmail user/app password not configured in Settings.")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "Daily Project Status Dashboard Report"

    body = "Hello,\n\nPlease find attached the latest daily project status dashboard report.\n\nBest regards,\nProject Tracker AI"
    msg.attach(MIMEText(body, 'plain'))

    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
            msg.attach(part)
    else:
        print(f"Warning: PDF file {pdf_path} not found. Sending email without attachment.")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"PDF report successfully emailed to {recipient_email}")
        return True
    except Exception as e:
        print(f"Email dispatch failed: {e}")
        return False


send_pdf_email = send_email_with_pdf
send_gmail_report = send_email_with_pdf
