import os
import sys
import time
import random
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
import openpyxl

from src.config import load_settings, BASE_DIR
from src.validator import is_valid_email, validate_attachments
from src.tracker import DeliveryTracker
from src.mailer import JobMailer
from src.google_auth import (
    get_authorization_url,
    exchange_code_for_tokens,
    get_google_auth_status,
    disconnect_google,
    get_google_credentials
)
from main import load_recipients, normalize_column_name

app = FastAPI(title="Job & Sales Mailer Engine API", version="2.0.0")

# Enable CORS for React frontend (Vite defaults to localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global campaign state manager
class CampaignManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.stop_requested = False
        self.total = 0
        self.current_idx = 0
        self.success_count = 0
        self.failed_count = 0
        self.current_target = ""
        self.current_email = ""
        self.next_send_time = 0.0
        self.logs = []

    def reset(self, total: int):
        with self.lock:
            self.is_running = True
            self.stop_requested = False
            self.total = total
            self.current_idx = 0
            self.success_count = 0
            self.failed_count = 0
            self.current_target = ""
            self.current_email = ""
            self.next_send_time = 0.0
            self.logs = []

    def add_log(self, level: str, message: str):
        with self.lock:
            self.logs.append({
                "timestamp": time.strftime("%H:%M:%S"),
                "level": level,
                "message": message
            })
            if len(self.logs) > 250:
                self.logs.pop(0)

    def request_stop(self):
        with self.lock:
            self.stop_requested = True
            self.add_log("WARNING", "Stop requested. Campaign will halt safely.")

    def finish(self):
        with self.lock:
            self.is_running = False
            self.stop_requested = False
            self.add_log("SUCCESS", f"Campaign finished. Sent: {self.success_count}/{self.current_idx}")

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            now = time.time()
            countdown = max(0, int(self.next_send_time - now)) if self.next_send_time > now else 0
            status_str = "RUNNING" if self.is_running else ("STOPPED" if self.stop_requested else "IDLE")
            return {
                "is_running": self.is_running,
                "status": status_str,
                "total": self.total,
                "current_idx": self.current_idx,
                "success_count": self.success_count,
                "failed_count": self.failed_count,
                "current_target": self.current_target,
                "current_email": self.current_email,
                "countdown": countdown,
                "logs": list(self.logs)
            }

campaign_manager = CampaignManager()


# Preset templates for Job Application and Sales Cold Outreach
DEFAULT_TEMPLATES = {
    "job": {
        "name": "Job Application",
        "subject": "Application for {{ role }} Role - {{ sender_name }}",
        "html": """<p style="margin: 0 0 16px 0;">Dear {{ hr_name }},</p>
<p style="margin: 0 0 16px 0;">
  I am {{ sender_name }} from Koparkhairane, Navi Mumbai, and I am excited to apply for the <strong>{{ role }}</strong> role at <strong>{{ company_name }}</strong>.
</p>
<p style="margin: 0 0 16px 0;">
  I hold a B.Tech in Information Technology with a CGPA of 8.8 from Bharati Vidyapeeth Deemed To Be University. I currently work as an SDE 1 at AINXT Technology Pvt. Ltd., where I develop high-performance dashboards, frontend SDKs, and build reusable UI components using React.js and Angular. I also collaborate with senior developers to follow engineering best practices and maintain clean code quality.
</p>
<p style="margin: 0 0 16px 0;">
  My core technical competencies include <strong>ReactJS, JavaScript, TypeScript, HTML5, CSS3, Angular, Next.js, Redux, Tailwind CSS, ExpressJS, MongoDB</strong>, and RESTful API integration. I also have hands-on experience with Git, GitHub, OpenAI API, Claude, Gemini, AI Agents, and Function Calling.
</p>
<p style="margin: 0 0 16px 0;">
  I am a quick learner with strong problem-solving, adaptability, and critical thinking skills. I would appreciate the opportunity to discuss how my skills and experience can contribute to your engineering goals at {{ company_name }}.
</p>
<p style="margin: 0 0 16px 0;">Best regards,</p>
<p style="margin: 0;">
  <strong>{{ sender_name }}</strong><br>
  {% if phone %}Phone: {{ phone }}<br>{% endif %}
  <a href="{{ linkedin }}" style="color: #4f46e5; text-decoration: underline;">LinkedIn Profile</a> | <a href="{{ github }}" style="color: #4f46e5; text-decoration: underline;">GitHub</a>
</p>""",
        "txt": """Dear {{ hr_name }},

I am {{ sender_name }} from Koparkhairane, Navi Mumbai, and I am excited to apply for the {{ role }} role at {{ company_name }}.

I hold a B.Tech in Information Technology with a CGPA of 8.8 from Bharati Vidyapeeth Deemed To Be University. I currently work as an SDE 1 at AINXT Technology Pvt. Ltd., where I develop dashboards and frontend SDKs and build reusable UI components using React.js and Angular.

My core technical competencies include ReactJS, JavaScript, TypeScript, HTML, CSS, Angular, Next.js, Redux, Tailwind CSS, ExpressJS, MongoDB, and API integration.

I would appreciate the opportunity to discuss how my skills can contribute to your team at {{ company_name }}.

Best regards,

{{ sender_name }}
LinkedIn: {{ linkedin }} | GitHub: {{ github }}"""
    },
    "sales": {
        "name": "B2B Sales & Web Services",
        "subject": "Quick question regarding {{ company_name }}'s web application",
        "html": """<p style="margin: 0 0 16px 0;">Hi {{ hr_name }},</p>
<p style="margin: 0 0 16px 0;">
  I came across <strong>{{ company_name }}</strong> and was really impressed by your recent momentum.
</p>
<p style="margin: 0 0 16px 0;">
  I help modern businesses build lightning-fast web applications, interactive dashboards, and AI integrations using React, Next.js, and Python. We recently helped a client improve page load speeds by 40% and streamline their customer onboarding workflows.
</p>
<p style="margin: 0 0 16px 0;">
  Are you open to a quick 5-minute chat this Thursday to see if we can do something similar for {{ company_name }}?
</p>
<p style="margin: 0 0 16px 0;">
  I have attached a brief overview of our case studies and portfolio for your review.
</p>
<p style="margin: 0 0 16px 0;">Best regards,</p>
<p style="margin: 0;">
  <strong>{{ sender_name }}</strong><br>
  <a href="{{ linkedin }}" style="color: #4f46e5; text-decoration: underline;">LinkedIn</a> | <a href="{{ github }}" style="color: #4f46e5; text-decoration: underline;">GitHub</a>
</p>
<p style="font-size: 11px; color: #888888; margin-top: 30px;">
  If you are not the right person or prefer not to receive updates, reply "Unsubscribe" and I will remove you immediately.
</p>""",
        "txt": """Hi {{ hr_name }},

I came across {{ company_name }} and was really impressed by your recent momentum.

I help modern businesses build lightning-fast web applications, interactive dashboards, and AI integrations using React, Next.js, and Python.

Are you open to a quick 5-minute chat this Thursday to see if we can explore synergies for {{ company_name }}?

Best regards,

{{ sender_name }}
LinkedIn: {{ linkedin }} | GitHub: {{ github }}

(Reply "Unsubscribe" if you prefer not to receive updates.)"""
    }
}


# --- Pydantic Request Models ---
class PreviewRequest(BaseModel):
    recipient: Dict[str, str]
    subject_template: str
    html_template: str
    txt_template: str

class TestEmailRequest(BaseModel):
    test_email: str
    recipient: Optional[Dict[str, str]] = None
    subject_template: Optional[str] = None
    html_template: Optional[str] = None
    txt_template: Optional[str] = None
    attachment_name: Optional[str] = None
    provider: Optional[str] = "auto"  # 'auto', 'google', or 'smtp'

class CampaignStartRequest(BaseModel):
    min_delay: int = 20
    max_delay: int = 40
    batch_limit: int = 50
    subject_template: Optional[str] = None
    html_template: Optional[str] = None
    txt_template: Optional[str] = None
    attachment_name: Optional[str] = None
    provider: Optional[str] = "auto"  # 'auto', 'google', or 'smtp'

class GoogleCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None

class ConfigUpdateRequest(BaseModel):
    sender_name: str
    sender_phone: str
    sender_linkedin: str
    sender_github: str
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


# --- Helper Functions ---
def get_active_recipients_file() -> Optional[Path]:
    data_dir = BASE_DIR / "data"
    excel_path = data_dir / "recipients.xlsx"
    if excel_path.exists():
        return excel_path
    csv_path = data_dir / "recipients.csv"
    if csv_path.exists():
        return csv_path
    return None

def get_attachments_list() -> List[Dict[str, Any]]:
    att_dir = BASE_DIR / "attachments"
    att_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for f in att_dir.iterdir():
        if f.is_file() and not f.name.startswith("."):
            files.append({
                "name": f.name,
                "size_bytes": f.stat().st_size,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))
            })
    return files

def update_env_file(key_values: Dict[str, str]):
    """Safely updates or appends key-value pairs in the .env file and environment."""
    env_path = BASE_DIR / ".env"
    existing_lines = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()

    updated_keys = set()
    new_lines = []
    for line in existing_lines:
        line_clean = line.strip()
        matched = False
        for k, v in key_values.items():
            if line_clean.startswith(f"{k}=") or line_clean == k:
                new_lines.append(f"{k}={v}")
                updated_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in key_values.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")
        os.environ[k] = v

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# --- API Endpoints ---

@app.get("/api/status")
def get_status():
    config = load_settings()
    recipients_file = get_active_recipients_file()
    recipients = []
    if recipients_file:
        try:
            recipients = load_recipients(recipients_file)
        except Exception:
            recipients = []

    history_file = BASE_DIR / "data" / "sent_history.csv"
    total_sent = 0
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            total_sent = max(0, sum(1 for _ in f) - 1)

    has_smtp = bool(config["smtp"]["user"] and config["smtp"]["password"] and config["smtp"]["password"] != "your_16_digit_app_password")
    google_status = get_google_auth_status()

    # Active sender calculation
    active_email = google_status["email"] if google_status.get("is_connected") and google_status.get("email") else config["smtp"]["user"]

    return {
        "smtp_configured": has_smtp,
        "google_auth": google_status,
        "active_sender_email": active_email,
        "sender": config["sender"],
        "smtp_user": config["smtp"]["user"],
        "recipients_file": recipients_file.name if recipients_file else None,
        "total_recipients": len(recipients),
        "total_emails_sent": total_sent,
        "attachments": get_attachments_list()
    }


# --- Google OAuth 2.0 Endpoints ---

@app.get("/api/auth/google/url")
def google_auth_url():
    """Generates the Google OAuth authorization URL for 'Sign in with Google'."""
    res = get_authorization_url()
    return res

@app.get("/api/auth/google/callback")
def google_auth_callback(code: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """Handles the redirect from Google OAuth consent screen."""
    if error:
        return HTMLResponse(f"""
        <html>
        <body style="font-family: system-ui, sans-serif; background: #0b0f19; color: #f43f5e; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
          <div style="text-align: center; padding: 30px; background: rgba(255,255,255,0.05); border-radius: 16px;">
            <h2>Google Sign-in Failed</h2>
            <p>{error}</p>
            <p style="color: #94a3b8; font-size: 13px;">You can close this window and try again.</p>
          </div>
        </body>
        </html>
        """)

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    try:
        token_data = exchange_code_for_tokens(code)
        email = token_data.get("email", "your Google account")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
          <title>Google Sign-in Successful</title>
          <style>
            body {{
              font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
              background: #0b0f19;
              color: #f8fafc;
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
              margin: 0;
            }}
            .card {{
              text-align: center;
              padding: 36px 40px;
              background: #111827;
              border: 1px solid rgba(255, 255, 255, 0.1);
              border-radius: 20px;
              box-shadow: 0 20px 50px rgba(0,0,0,0.6);
              max-width: 400px;
            }}
            .avatar {{
              width: 56px;
              height: 56px;
              border-radius: 50%;
              border: 2px solid #10b981;
              margin-bottom: 16px;
            }}
            .badge {{
              background: rgba(16, 185, 129, 0.15);
              color: #34d399;
              border: 1px solid rgba(16, 185, 129, 0.3);
              padding: 4px 12px;
              border-radius: 9999px;
              font-size: 12px;
              font-weight: 600;
              display: inline-block;
              margin-top: 8px;
            }}
          </style>
        </head>
        <body>
          <div class="card">
            <div style="font-size: 40px; margin-bottom: 10px;">✨</div>
            <h2 style="margin: 0 0 8px 0; font-size: 20px;">Connected Successfully!</h2>
            <p style="color: #94a3b8; font-size: 14px; margin: 0 0 12px 0;">Signed in as <strong>{email}</strong></p>
            <div class="badge">Gmail API Active</div>
            <p style="color: #64748b; font-size: 12px; margin-top: 20px;">Closing window and returning to dashboard...</p>
          </div>
          <script>
            if (window.opener) {{
              window.opener.postMessage({{ type: 'GOOGLE_AUTH_SUCCESS', email: '{email}' }}, '*');
            }}
            setTimeout(() => {{
              if (window.opener) {{
                window.close();
              }} else {{
                window.location.href = '{frontend_url}/';
              }}
            }}, 1500);
          </script>
        </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
        <html>
        <body style="font-family: system-ui, sans-serif; background: #0b0f19; color: #f43f5e; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
          <div style="text-align: center; padding: 30px; background: rgba(255,255,255,0.05); border-radius: 16px;">
            <h2>Authorization Exchange Error</h2>
            <p>{str(e)}</p>
          </div>
        </body>
        </html>
        """)

@app.get("/api/auth/google/status")
def google_status():
    return get_google_auth_status()

@app.post("/api/auth/google/disconnect")
def google_disconnect():
    disconnect_google()
    return {"message": "Google account disconnected. Reverted to SMTP mode."}

@app.post("/api/auth/google/save-credentials")
def save_google_credentials(creds: GoogleCredentialsRequest):
    data = {
        "GOOGLE_CLIENT_ID": creds.client_id.strip(),
        "GOOGLE_CLIENT_SECRET": creds.client_secret.strip()
    }
    if creds.redirect_uri:
        data["GOOGLE_REDIRECT_URI"] = creds.redirect_uri.strip()

    update_env_file(data)
    return {"message": "Google Cloud credentials saved to .env successfully!"}


# --- Templates & Leads Endpoints ---

@app.get("/api/templates")
def get_templates():
    return DEFAULT_TEMPLATES

@app.get("/api/recipients")
def get_recipients():
    file_path = get_active_recipients_file()
    if not file_path:
        return {"filename": None, "recipients": []}
    try:
        recipients = load_recipients(file_path)
        return {
            "filename": file_path.name,
            "total": len(recipients),
            "recipients": recipients
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load recipients: {str(e)}")

@app.post("/api/upload-recipients")
async def upload_recipients(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".xlsx", ".xls", ".csv"]:
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls, or .csv files are supported.")

    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    target_path = data_dir / f"recipients{ext}"

    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)

    try:
        recipients = load_recipients(target_path)
        return {
            "message": f"Successfully loaded {len(recipients)} contacts from {file.filename}",
            "filename": target_path.name,
            "total": len(recipients),
            "sample": recipients[:5]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File uploaded, but parsing failed: {str(e)}")

@app.post("/api/upload-attachment")
async def upload_attachment(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF attachments are currently supported.")

    att_dir = BASE_DIR / "attachments"
    att_dir.mkdir(parents=True, exist_ok=True)
    target_path = att_dir / file.filename

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 15MB limit.")

    with open(target_path, "wb") as f:
        f.write(content)

    return {
        "message": f"Attachment '{file.filename}' uploaded successfully.",
        "filename": file.filename,
        "size_kb": round(len(content) / 1024, 1)
    }

@app.post("/api/preview")
def preview_email(req: PreviewRequest):
    config = load_settings()
    mailer = JobMailer(config)

    from jinja2 import Environment
    env_html = Environment(autoescape=True)
    env_txt = Environment(autoescape=False)

    recipient = req.recipient
    role = (recipient.get("job_role") or "").strip() or config["campaign"].get("default_role", "Front End Developer")
    company = (recipient.get("company_name") or "").strip() or "your organization"
    hr_name = (recipient.get("hr_name") or "").strip() or "Hiring Manager"
    active_sender = mailer.get_active_sender_email()

    context = {
        "hr_name": hr_name,
        "company_name": company,
        "role": role,
        "sender_name": config["sender"].get("name", "Applicant"),
        "sender_user": active_sender,
        "phone": config["sender"].get("phone", ""),
        "linkedin": config["sender"].get("linkedin", ""),
        "github": config["sender"].get("github", ""),
        "portfolio": config["sender"].get("portfolio", ""),
    }

    try:
        subject = env_txt.from_string(req.subject_template).render(context)
        html_body = env_html.from_string(req.html_template).render(context)
        txt_body = env_txt.from_string(req.txt_template).render(context)
        return {
            "subject": subject,
            "html": html_body,
            "text": txt_body,
            "recipient": recipient,
            "sender_user": active_sender
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template render error: {str(e)}")

@app.post("/api/test-email")
def send_test_email(req: TestEmailRequest):
    if not is_valid_email(req.test_email):
        raise HTTPException(status_code=400, detail="Invalid test email address.")

    config = load_settings()
    mailer = JobMailer(config)

    dummy = req.recipient or {
        "hr_name": "Test Recruiter",
        "company_name": "Acme Global",
        "job_role": "Front End Developer"
    }

    from jinja2 import Environment
    env_html = Environment(autoescape=True)
    env_txt = Environment(autoescape=False)

    role = (dummy.get("job_role") or "").strip() or "Front End Developer"
    company = (dummy.get("company_name") or "").strip() or "Acme Global"
    hr_name = (dummy.get("hr_name") or "").strip() or "Test Recruiter"
    active_sender = mailer.get_active_sender_email()

    context = {
        "hr_name": hr_name,
        "company_name": company,
        "role": role,
        "sender_name": config["sender"].get("name", "Applicant"),
        "sender_user": active_sender,
        "phone": config["sender"].get("phone", ""),
        "linkedin": config["sender"].get("linkedin", ""),
        "github": config["sender"].get("github", ""),
        "portfolio": config["sender"].get("portfolio", ""),
    }

    sub_tmpl = req.subject_template or config["campaign"].get("subject_template", "Application for {{ role }} Role")
    html_tmpl = req.html_template or Path(config["base_dir"] / "templates" / "email_template.html").read_text(encoding="utf-8")
    txt_tmpl = req.txt_template or Path(config["base_dir"] / "templates" / "email_template.txt").read_text(encoding="utf-8")

    subject = env_txt.from_string(sub_tmpl).render(context)
    html_body = env_html.from_string(html_tmpl).render(context)
    txt_body = env_txt.from_string(txt_tmpl).render(context)

    att_name = req.attachment_name or "Rohan's Resume.pdf"
    att_path = BASE_DIR / "attachments" / att_name
    attachments = [att_path] if att_path.exists() else []

    content = {"subject": subject, "html": html_body, "text": txt_body}
    msg = mailer.build_message(req.test_email, content, attachments, sender_email=active_sender)

    try:
        res = mailer.send_single_email(req.test_email, msg, provider=req.provider or "auto")
        used_prov = "Gmail API (OAuth)" if res.get("provider") == "google_api" else "SMTP"
        return {"message": f"Test email successfully dispatched to {req.test_email} via {used_prov}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email Send Failed: {str(e)}")


def run_campaign_background(req: CampaignStartRequest):
    config = load_settings()
    mailer = JobMailer(config)
    history_path = BASE_DIR / "data" / "sent_history.csv"
    tracker = DeliveryTracker(history_path, cooldown_days=30)
    cooldown_emails = tracker.get_recently_contacted_emails()

    recipients_file = get_active_recipients_file()
    if not recipients_file:
        campaign_manager.add_log("ERROR", "No recipients file found!")
        campaign_manager.finish()
        return

    recipients = load_recipients(recipients_file)
    max_batch = min(req.batch_limit, len(recipients))
    campaign_manager.reset(max_batch)

    from jinja2 import Environment
    env_html = Environment(autoescape=True)
    env_txt = Environment(autoescape=False)

    sub_tmpl = req.subject_template or config["campaign"].get("subject_template", "Application for {{ role }} Role")
    html_tmpl = req.html_template or Path(config["base_dir"] / "templates" / "email_template.html").read_text(encoding="utf-8")
    txt_tmpl = req.txt_template or Path(config["base_dir"] / "templates" / "email_template.txt").read_text(encoding="utf-8")

    att_name = req.attachment_name or "Rohan's Resume.pdf"
    att_path = BASE_DIR / "attachments" / att_name
    attachments = [att_path] if att_path.exists() else []

    active_sender = mailer.get_active_sender_email()
    google_status = get_google_auth_status()
    channel = "Gmail API" if (req.provider == "google" or (req.provider == "auto" and google_status.get("is_connected"))) else "SMTP"

    campaign_manager.add_log("INFO", f"Launching campaign via [{channel}]. Batch: {max_batch}, Delay: {req.min_delay}-{req.max_delay}s")

    for idx, r in enumerate(recipients[:max_batch], start=1):
        if campaign_manager.stop_requested:
            campaign_manager.add_log("WARNING", "Campaign stopped by user.")
            break

        hr_email = r.get("hr_email", "").strip().lower()
        company = r.get("company_name", "your organization").strip() or "your organization"
        role = r.get("job_role", "Front End Developer").strip() or "Front End Developer"
        hr_name = r.get("hr_name", "Hiring Manager").strip() or "Hiring Manager"

        with campaign_manager.lock:
            campaign_manager.current_idx = idx
            campaign_manager.current_target = company
            campaign_manager.current_email = hr_email

        if not is_valid_email(hr_email):
            campaign_manager.add_log("WARNING", f"[{idx}/{max_batch}] Skipping invalid email: '{hr_email}'")
            continue

        if hr_email in cooldown_emails:
            campaign_manager.add_log("INFO", f"[{idx}/{max_batch}] Skipping {hr_email} ({company}) - already contacted recently.")
            continue

        context = {
            "hr_name": hr_name,
            "company_name": company,
            "role": role,
            "sender_name": config["sender"].get("name", "Applicant"),
            "sender_user": active_sender,
            "phone": config["sender"].get("phone", ""),
            "linkedin": config["sender"].get("linkedin", ""),
            "github": config["sender"].get("github", ""),
            "portfolio": config["sender"].get("portfolio", ""),
        }

        subject = env_txt.from_string(sub_tmpl).render(context)
        html_body = env_html.from_string(html_tmpl).render(context)
        txt_body = env_txt.from_string(txt_tmpl).render(context)

        msg = mailer.build_message(hr_email, {"subject": subject, "html": html_body, "text": txt_body}, attachments, sender_email=active_sender)

        try:
            campaign_manager.add_log("INFO", f"[{idx}/{max_batch}] Sending to {hr_email} ({company})...")
            res = mailer.send_single_email(hr_email, msg, provider=req.provider or "auto")
            prov_used = "Gmail API" if res.get("provider") == "google_api" else "SMTP"
            tracker.log_result(hr_email, company, role, "SUCCESS")
            cooldown_emails.add(hr_email)

            with campaign_manager.lock:
                campaign_manager.success_count += 1

            campaign_manager.add_log("SUCCESS", f"[{idx}/{max_batch}] Delivered to {hr_email} via {prov_used}")

            # Jitter delay
            if idx < max_batch and not campaign_manager.stop_requested:
                delay = random.uniform(req.min_delay, req.max_delay)
                with campaign_manager.lock:
                    campaign_manager.next_send_time = time.time() + delay

                campaign_manager.add_log("INFO", f"Safety cooldown: waiting {delay:.1f}s...")
                
                elapsed = 0.0
                while elapsed < delay:
                    if campaign_manager.stop_requested:
                        break
                    time.sleep(1)
                    elapsed += 1.0

        except Exception as e:
            err = str(e)
            with campaign_manager.lock:
                campaign_manager.failed_count += 1
            campaign_manager.add_log("ERROR", f"[{idx}/{max_batch}] Failed sending to {hr_email}: {err}")
            tracker.log_result(hr_email, company, role, "FAILED", err)

            if "authentication" in err.lower() or "invalid_grant" in err.lower():
                campaign_manager.add_log("ERROR", "Authentication error. Halting campaign.")
                break

    campaign_manager.finish()


@app.post("/api/campaign/start")
def start_campaign(req: CampaignStartRequest, background_tasks: BackgroundTasks):
    status = campaign_manager.get_status()
    if status["is_running"]:
        raise HTTPException(status_code=400, detail="A campaign is already running!")

    background_tasks.add_task(run_campaign_background, req)
    return {"message": "Campaign started in background."}

@app.post("/api/campaign/stop")
def stop_campaign():
    campaign_manager.request_stop()
    return {"message": "Stop requested. Campaign will halt shortly."}

@app.get("/api/campaign/status")
def get_campaign_status():
    return campaign_manager.get_status()

@app.get("/api/history")
def get_history():
    history_file = BASE_DIR / "data" / "sent_history.csv"
    if not history_file.exists():
        return {"total": 0, "rows": []}

    import csv
    rows = []
    with open(history_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    rows.reverse()  # Latest first
    return {"total": len(rows), "rows": rows[:100]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
