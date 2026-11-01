# Automated Job Application Mailer - Architecture & Execution Plan

A robust, personalized, and anti-spam automated email dispatcher built in Python for job seekers to reach recruiters and hiring managers with resume attachments.

---

## 1. System Architecture

```
                    ┌────────────────────────────┐
                    │     recipients.csv         │
                    │ (HR Name, Email, Company)  │
                    └─────────────┬──────────────┘
                                  │
┌──────────────────┐              ▼              ┌──────────────────────┐
│  .env / config   ├────► [ Validation & Guard ] ◄────┤ templates/email.html │
│ (SMTP & Sender)  │      (Duplicate check,      │    │ (Jinja2 Template)    │
└──────────────────┘       email verification)   └──────────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │    MIME Message Builder    │
                    │  (HTML body + Resume.pdf)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │ SMTP Engine & Rate Limiter │
                    │ (Random delay, Gmail/TLS)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │  sent_log.csv / Console    │
                    │    (Audit & Delivery log)  │
                    └────────────────────────────┘
```

---

## 2. Recommended Project Structure

```text
job-application-mailer/
├── .env                     # Secure credentials (App Password, sender email)
├── .env.example             # Template for environment variables
├── requirements.txt         # Project dependencies
├── config.yaml              # General configuration (delay intervals, sender profile)
├── PLAN.md                  # Project blueprint & documentation
├── data/
│   ├── recipients.csv       # Recruiter contact list
│   └── sent_history.csv     # Auto-generated ledger to prevent duplicate sends
├── attachments/
│   └── Resume.pdf           # Resume or portfolio attachments
├── templates/
│   ├── email_template.html  # Personalized HTML email format
│   └── email_template.txt   # Plain text fallback for high deliverability
├── src/
│   ├── __init__.py
│   ├── config.py            # Loads and validates configuration
│   ├── mailer.py            # SMTP transport and MIME assembly
│   ├── tracker.py           # Deduplication checker and history logging
│   └── validator.py         # Recruiter email validation & file size checks
└── main.py                  # CLI entrypoint (Supports --dry-run and --send)
```

---

## 3. Core Modules & Implementation Details

### Step 1: Configuration & Security
- **Credentials Isolation**: Store sensitive information in `.env` (never commit to version control).
- **Authentication**:
  - For **Gmail**: Use a Google **16-character App Password** (requires 2-Factor Authentication enabled).
  - For **Outlook / Custom SMTP**: Host, Port (587 for TLS, 465 for SSL), Username, and Password.

### Step 2: Recruiter Data Management (`data/recipients.csv`)
Columns supported:
- `company_name`: Target company (e.g., *Google*, *Microsoft*, *Startup XYZ*)
- `hr_name`: Recruiter/Hiring Manager name (e.g., *Sarah* or fallback to *Hiring Team*)
- `hr_email`: Target email address
- `job_role`: Target position (e.g., *Full Stack Developer*, *Data Scientist*)
- `custom_intro`: (Optional) Customized sentence for why you are a fit for this specific company

### Step 3: Templating Engine (Jinja2)
- **Dynamic Subject Line**:
  `Application for {{ job_role }} - {{ sender_name }} ({{ years_of_experience }} Yrs Exp)`
- **Body Personalization**:
  - Salutation: `Hi {{ hr_name }},`
  - Company Reference: `I noticed an opening for {{ job_role }} at {{ company_name }}...`
  - Portfolio / GitHub / LinkedIn links styled cleanly.
- Dual format support: Multipart MIME (`text/plain` + `text/html`) to guarantee high inbox placement and low spam scores.

### Step 4: Multi-Attachment Handler
- Uses Python `email.mime.application.MIMEApplication` and `email.mime.multipart.MIMEMultipart`.
- Automatic attachment checks:
  - File presence verification.
  - File size safety check (capped under 15MB to prevent ISP rejection).
  - Proper MIME headers (`Content-Disposition: attachment; filename="Resume_Rohan.pdf"`).

### Step 5: Anti-Spam & Deliverability Safeguards
- **Dry-Run Mode (`--dry-run`)**:
  Renders the emails and previews them in console or exports preview HTML files without sending any actual emails.
- **Randomized Jitter Delays**:
  Sleeps for a random duration (e.g., 25–50 seconds) between successive emails to mimic human behavior and evade automated spam traps.
- **Deduplication Engine**:
  Reads `sent_history.csv` before dispatching. If `hr_email` was already contacted within the last *N* days, it skips them automatically.
- **Batch Quota Throttling**:
  Hard limit on daily emails (e.g., maximum 50 emails per run) to maintain sender domain reputation.

### Step 6: Tracking & Audit Log
- Records delivery status with columns:
  `timestamp, hr_email, company_name, job_role, status, error_message`
- Real-time terminal output with colored status indicators (`[SUCCESS]`, `[SKIPPED]`, `[FAILED]`).

---

## 4. CLI Usage Examples

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test email rendering without sending (Dry Run)
python main.py --dry-run

# 3. Send application to a single test email first
python main.py --test-email your_test_email@gmail.com

# 4. Run the full campaign safely
python main.py --send
```

---

## 5. Security & Deliverability Best Practices

1. **Avoid spam triggers**: Keep subject lines professional and avoid buzzwords like *"URGENT"*, *"HIRE ME IMMEDIATELY"*, or excessive exclamation marks.
2. **Warm up your email**: Do not send 200 emails in the first hour from a brand new email account. Start with 15–20/day.
3. **Use clear attachment names**: Name your PDF `Resume_<YourName>_<Role>.pdf` rather than `Resume_final_v3.pdf`.
