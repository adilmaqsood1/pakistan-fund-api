import os
import json
import smtplib
import logging
import httpx
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger("contact")

router = APIRouter(prefix="/contact", tags=["Contact"])

SUBMISSIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "contact_submissions.json")

class ContactSubmission(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    organization: Optional[str] = "Individual Investor"

def save_submission_locally(data_dict: dict):
    submissions = []
    if os.path.exists(SUBMISSIONS_FILE):
        try:
            with open(SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
                submissions = json.load(f)
        except Exception:
            submissions = []
    submissions.append(data_dict)
    try:
        with open(SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(submissions, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write contact submission locally: {e}")

def send_email_via_brevo(submission: ContactSubmission, client_ip: str) -> bool:
    from dotenv import load_dotenv
    load_dotenv(override=True)

    smtp_server = os.getenv("SMTP_SERVER", os.getenv("SMTP_Server", "smtp-relay.brevo.com")).strip()
    smtp_port = int(os.getenv("SMTP_PORT", os.getenv("Port", "587")))
    smtp_login = os.getenv("SMTP_LOGIN", os.getenv("Login", "")).strip()
    raw_password = os.getenv("SMTP_PASSWORD", os.getenv("api_key", "")).strip()
    # Remove spaces from Gmail App Passwords if present
    smtp_password = raw_password.replace(" ", "") if ("gmail.com" in smtp_server or len(raw_password) == 19) else raw_password
    brevo_api_key = os.getenv("BREVO_API_KEY", "").strip()
    recipient = os.getenv("CONTACT_RECIPIENT_EMAIL", "adilmaqsood501@gmail.com").strip()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"FundGPT Dashboard Access Registration: {submission.full_name}"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
          <h2 style="color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; margin-top: 0;">🚀 New FundGPT Dashboard Registration</h2>
          <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
            <tr>
              <td style="padding: 10px; font-weight: bold; color: #94a3b8; width: 35%;">Full Name:</td>
              <td style="padding: 10px; color: #f8fafc;">{submission.full_name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; font-weight: bold; color: #94a3b8;">Email Address:</td>
              <td style="padding: 10px; color: #38bdf8;"><a href="mailto:{submission.email}" style="color: #38bdf8; text-decoration: none;">{submission.email}</a></td>
            </tr>
            <tr>
              <td style="padding: 10px; font-weight: bold; color: #94a3b8;">Phone / WhatsApp:</td>
              <td style="padding: 10px; color: #f8fafc;">{submission.phone}</td>
            </tr>
            <tr>
              <td style="padding: 10px; font-weight: bold; color: #94a3b8;">Organization / Role:</td>
              <td style="padding: 10px; color: #f8fafc;">{submission.organization or 'Individual Investor'}</td>
            </tr>
            <tr>
              <td style="padding: 10px; font-weight: bold; color: #94a3b8;">Registered At:</td>
              <td style="padding: 10px; color: #f8fafc;">{now_str} (PKT)</td>
            </tr>
            <tr>
              <td style="padding: 10px; font-weight: bold; color: #94a3b8;">Client IP:</td>
              <td style="padding: 10px; color: #cbd5e1;">{client_ip}</td>
            </tr>
          </table>
          <hr style="border: none; border-top: 1px solid #334155; margin: 20px 0;" />
          <p style="font-size: 12px; color: #64748b; margin-bottom: 0;">Sent automatically by Pakistan Fund & ETF API (FundGPT Gateway).</p>
        </div>
      </body>
    </html>
    """

    # 1. Try Brevo HTTP API v3 if API key or SMTP key is configured
    api_key_to_use = brevo_api_key or (smtp_password if (smtp_password.startswith("xkeysib-") or smtp_password.startswith("xsmtpsib-")) else "")
    if api_key_to_use:
        try:
            sender_email = smtp_login if ("@" in smtp_login and not smtp_login.endswith("@smtp-brevo.com")) else recipient
            headers = {
                "accept": "application/json",
                "api-key": api_key_to_use,
                "content-type": "application/json"
            }
            payload = {
                "sender": {"name": "FundGPT Gateway", "email": sender_email},
                "to": [{"email": recipient, "name": "Adil Maqsood"}],
                "subject": subject,
                "htmlContent": html_content
            }
            with httpx.Client(timeout=5.0) as client:
                resp = client.post("https://api.brevo.com/v3/smtp/email", headers=headers, json=payload)
                if resp.status_code in [200, 201, 202]:
                    logger.info(f"Successfully sent contact email to {recipient} via Brevo HTTP API v3")
                    return True
                else:
                    logger.warning(f"Brevo HTTP API v3 returned status {resp.status_code}: {resp.text}")
        except Exception as e_api:
            logger.warning(f"Brevo HTTP API delivery attempt failed: {e_api}")

    # 2. Try standard SMTP (Brevo, Gmail, Outlook, or Custom SMTP)
    if smtp_login and smtp_password:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            sender_addr = smtp_login if "@" in smtp_login else f"noreply@{smtp_server}"
            msg["From"] = f"FundGPT Access <{sender_addr}>"
            msg["To"] = recipient
            msg.attach(MIMEText(html_content, "html"))

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=5.0) as server:
                    server.login(smtp_login, smtp_password)
                    server.sendmail(sender_addr, [recipient], msg.as_string())
            else:
                with smtplib.SMTP(smtp_server, smtp_port, timeout=5.0) as server:
                    server.starttls()
                    server.login(smtp_login, smtp_password)
                    server.sendmail(sender_addr, [recipient], msg.as_string())

            logger.info(f"Successfully sent contact email to {recipient} via SMTP {smtp_server}:{smtp_port}")
            return True
        except smtplib.SMTPResponseException as e_smtp:
            if e_smtp.smtp_code == 535:
                logger.warning(
                    f"SMTP Auth Failed (535): Invalid credentials for {smtp_login} on {smtp_server}. "
                    "Please set valid SMTP_LOGIN and SMTP_PASSWORD (or BREVO_API_KEY / Gmail App Password) in your .env file."
                )
            elif "Unauthorized IP address" in str(e_smtp) or e_smtp.smtp_code == 525:
                logger.error("Brevo SMTP IP Restriction: Please allow server IP or clear Authorized IP restriction in Brevo Dashboard (https://app.brevo.com/settings/keys/smtp).")
            else:
                logger.warning(f"SMTP error {e_smtp.smtp_code}: {e_smtp.smtp_error}")
        except Exception as e1:
            logger.warning(f"SMTP {smtp_server}:{smtp_port} failed: {e1}")
    else:
        logger.warning(
            "SMTP credentials not configured. Please set SMTP_LOGIN, SMTP_PASSWORD, or BREVO_API_KEY in your .env file. "
            "Submission saved to local audit log (contact_submissions.json)."
        )

    return False

@router.post("")
def submit_contact_form(data: ContactSubmission, request: Request):
    client_ip = request.client.host if request.client else "Unknown"

    record = {
        "full_name": data.full_name,
        "email": data.email,
        "phone": data.phone,
        "organization": data.organization,
        "timestamp": datetime.now().isoformat(),
        "client_ip": client_ip
    }

    # Save to local audit file
    save_submission_locally(record)

    # Attempt email delivery via Brevo
    email_delivered = send_email_via_brevo(data, client_ip)

    return {
        "status": "success",
        "email_delivered": email_delivered,
        "message": "Verification submitted successfully. Access granted to dashboard for 24 hours.",
        "recipient": os.getenv("CONTACT_RECIPIENT_EMAIL", "adilmaqsood501@gmail.com")
    }
