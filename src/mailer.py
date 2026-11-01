import os
import smtplib
import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from jinja2 import Environment, FileSystemLoader

from src.google_auth import get_valid_access_token, get_google_auth_status

class JobMailer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_cfg = config["smtp"]
        self.sender_cfg = config["sender"]
        self.campaign_cfg = config["campaign"]
        self.base_dir = config["base_dir"]

        # Set up Jinja2 environment (autoescape enabled for HTML, disabled for text)
        template_dir = self.base_dir / "templates"
        self.jinja_env_html = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
        self.jinja_env_txt = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)

        self.html_template = self.jinja_env_html.get_template(
            Path(config["paths"].get("template_html", "templates/email_template.html")).name
        )
        self.txt_template = self.jinja_env_txt.get_template(
            Path(config["paths"].get("template_txt", "templates/email_template.txt")).name
        )

    def get_active_sender_email(self) -> str:
        """Determines active sender email: Google OAuth account if connected, else SMTP user."""
        google_status = get_google_auth_status()
        if google_status.get("is_connected") and google_status.get("email"):
            return google_status["email"]
        return self.smtp_cfg.get("user", "")

    def render_content(self, recipient: Dict[str, str], sender_email: Optional[str] = None) -> Dict[str, str]:
        """Renders subject, html body, and plain text body using Jinja2."""
        role = (recipient.get("job_role") or "").strip() or self.campaign_cfg.get("default_role", "Front End Developer")
        company = (recipient.get("company_name") or "").strip() or "your organization"
        hr_name = (recipient.get("hr_name") or "").strip() or "Hiring Manager"
        custom_intro = (recipient.get("custom_intro") or "").strip()
        experience = self.campaign_cfg.get("years_of_experience", "1+")

        active_sender = sender_email or self.get_active_sender_email()

        context = {
            "hr_name": hr_name,
            "company_name": company,
            "role": role,
            "custom_intro": custom_intro,
            "experience": experience,
            "sender_name": self.sender_cfg.get("name", "Applicant"),
            "sender_user": active_sender,
            "phone": self.sender_cfg.get("phone", ""),
            "linkedin": self.sender_cfg.get("linkedin", ""),
            "github": self.sender_cfg.get("github", ""),
            "portfolio": self.sender_cfg.get("portfolio", ""),
        }

        # Subject line rendering
        subject_template_str = self.campaign_cfg.get(
            "subject_template", "Application for {{ role }} - {{ sender_name }}"
        )
        subject_template = self.jinja_env_txt.from_string(subject_template_str)
        subject = subject_template.render(context)

        html_body = self.html_template.render(context)
        txt_body = self.txt_template.render(context)

        return {
            "subject": subject,
            "html": html_body,
            "text": txt_body,
            "role": role,
            "company": company,
            "hr_name": hr_name
        }

    def build_message(self, recipient_email: str, content: Dict[str, str], attachment_paths: List[Path], sender_email: Optional[str] = None) -> MIMEMultipart:
        """Constructs a multipart MIME email with alternative content and binary attachments."""
        active_sender = sender_email or self.get_active_sender_email()
        sender_name = self.sender_cfg.get("name", "Applicant")

        msg = MIMEMultipart("mixed")
        msg["From"] = f"{sender_name} <{active_sender}>"
        msg["To"] = recipient_email
        msg["Subject"] = content["subject"]

        # Alternative part for plain text and HTML
        msg_body = MIMEMultipart("alternative")
        part_text = MIMEText(content["text"], "plain", "utf-8")
        part_html = MIMEText(content["html"], "html", "utf-8")
        msg_body.attach(part_text)
        msg_body.attach(part_html)
        msg.attach(msg_body)

        # Attachments
        for path in attachment_paths:
            with open(path, "rb") as f:
                part_attach = MIMEApplication(f.read(), Name=path.name)
            part_attach["Content-Disposition"] = f'attachment; filename="{path.name}"'
            msg.attach(part_attach)

        return msg

    def send_via_gmail_api(self, recipient_email: str, msg: MIMEMultipart, access_token: str) -> Dict[str, Any]:
        """Dispatches an email through Google's official Gmail REST API."""
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {"raw": raw_message}

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message") or resp.text
            except Exception:
                pass
            raise ValueError(f"Gmail API dispatch error: {err_msg}")

        return resp.json()

    def send_via_smtp(self, recipient_email: str, msg: MIMEMultipart) -> None:
        """Connects and sends a single email over traditional SMTP."""
        host = self.smtp_cfg["host"]
        port = self.smtp_cfg["port"]
        user = self.smtp_cfg["user"]
        password = self.smtp_cfg["password"]

        if not user or not password or password == "your_16_digit_app_password":
            raise ValueError(
                "SMTP credentials are not configured! Please edit your .env file with your real email and App Password."
            )

        server = None
        try:
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=30)
            else:
                server = smtplib.SMTP(host, port, timeout=30)
                server.ehlo()
                server.starttls()
                server.ehlo()

            server.login(user, password)
            server.sendmail(user, [recipient_email], msg.as_string())
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    def send_single_email(self, recipient_email: str, msg: MIMEMultipart, provider: str = "auto") -> Dict[str, Any]:
        """Sends an email using the selected provider ('google', 'smtp', or 'auto')."""
        if provider in ("google", "auto"):
            access_token = get_valid_access_token()
            if access_token:
                res = self.send_via_gmail_api(recipient_email, msg, access_token)
                return {"provider": "google_api", "id": res.get("id")}
            elif provider == "google":
                raise ValueError("Google account is not connected! Please click 'Sign in with Google' first.")

        # Default fallback: SMTP
        self.send_via_smtp(recipient_email, msg)
        return {"provider": "smtp"}
