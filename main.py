import argparse
import csv
import random
import re
import sys
import time
from pathlib import Path
from typing import List, Dict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None

from src.config import load_settings
from src.validator import is_valid_email, validate_attachments
from src.tracker import DeliveryTracker
from src.mailer import JobMailer

def log_info(msg: str):
    if console:
        console.print(f"[cyan][INFO][/cyan] {msg}")
    else:
        print(f"[INFO] {msg}")

def log_success(msg: str):
    if console:
        console.print(f"[bold green][SUCCESS][/bold green] {msg}")
    else:
        print(f"[SUCCESS] {msg}")

def log_warning(msg: str):
    if console:
        console.print(f"[bold yellow][WARNING][/bold yellow] {msg}")
    else:
        print(f"[WARNING] {msg}")

def log_error(msg: str):
    if console:
        console.print(f"[bold red][ERROR][/bold red] {msg}")
    else:
        print(f"[ERROR] {msg}")


def normalize_column_name(header: str) -> str:
    """Normalizes various user column names to internal standard keys."""
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", str(header)).lower()
    if cleaned in ["hremail", "email", "emailid", "emailaddress", "recruiteremail", "mail"]:
        return "hr_email"
    if cleaned in ["companyname", "company", "organization", "firm", "companytitle"]:
        return "company_name"
    if cleaned in ["hrname", "name", "recruitername", "contactperson", "recruiter", "person"]:
        return "hr_name"
    if cleaned in ["jobrole", "role", "position", "designation", "jobtitle", "job"]:
        return "job_role"
    if cleaned in ["customintro", "intro", "customnote", "note"]:
        return "custom_intro"
    return header.strip()


def load_recipients(file_path: Path) -> List[Dict[str, str]]:
    """Reads recipients list from either Excel (.xlsx, .xls) or CSV (.csv)."""
    if not file_path.exists():
        raise FileNotFoundError(f"Recipients file not found at: {file_path}")

    recipients = []
    suffix = file_path.suffix.lower()

    if suffix in [".xlsx", ".xls"]:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                return []
            raw_headers = [str(c).strip() if c is not None else "" for c in rows[0]]
            headers = [normalize_column_name(h) for h in raw_headers]

            for row_vals in rows[1:]:
                if not any(row_vals):
                    continue
                row_dict = {}
                for h, val in zip(headers, row_vals):
                    if h:
                        row_dict[h] = str(val).strip() if val is not None else ""
                if row_dict.get("hr_email"):
                    recipients.append(row_dict)
        except Exception as e:
            raise RuntimeError(f"Error reading Excel file {file_path.name}: {e}")

    else:
        # Default to CSV
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
            if not rows:
                return []
            raw_headers = [str(c).strip() for c in rows[0]]
            headers = [normalize_column_name(h) for h in raw_headers]

            for row_vals in rows[1:]:
                if not any(row_vals):
                    continue
                row_dict = {}
                for h, val in zip(headers, row_vals):
                    if h:
                        row_dict[h] = str(val).strip() if val is not None else ""
                if row_dict.get("hr_email"):
                    recipients.append(row_dict)

    return recipients


def run_dry_run(mailer: JobMailer, recipients: List[Dict[str, str]], attachment_paths: List[Path]):
    """Renders preview emails without sending anything."""
    log_info("Running in DRY-RUN mode. No emails will be sent.")
    
    if not recipients:
        log_warning("No recipients found in the CSV file.")
        return

    sample_recipient = recipients[0]
    content = mailer.render_content(sample_recipient)

    # Save a rendered preview HTML file for visual verification
    preview_file = mailer.base_dir / "preview_rendered.html"
    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(content["html"])

    log_success(f"Rendered HTML preview exported to: {preview_file}")

    if console:
        table = Table(title="[bold blue]Sample Rendered Application Email[/bold blue]")
        table.add_column("Field", style="bold magenta", width=16)
        table.add_column("Content", style="green")

        table.add_row("To", sample_recipient["hr_email"])
        table.add_row("Company", sample_recipient.get("company_name", "N/A"))
        table.add_row("HR Name", sample_recipient.get("hr_name", "N/A"))
        table.add_row("Subject", content["subject"])
        table.add_row("Attachments", ", ".join([p.name for p in attachment_paths]))

        console.print(table)
        console.print(Panel(content["text"], title="[bold cyan]Plain Text Body Preview[/bold cyan]", border_style="cyan"))
    else:
        print(f"\n--- PREVIEW FOR: {sample_recipient['hr_email']} ---")
        print(f"Subject: {content['subject']}")
        print(f"Attachments: {[p.name for p in attachment_paths]}")
        print("\n" + content["text"] + "\n-----------------------------------\n")

    log_info(f"Total valid recipients queued: {len(recipients)}")
    log_info("To send emails, re-run with: python main.py --send")


def run_test_email(mailer: JobMailer, test_email: str, attachment_paths: List[Path]):
    """Sends a single test email with attachments to verify SMTP and inbox formatting."""
    log_info(f"Sending test email to: {test_email}")
    dummy_recipient = {
        "hr_name": "Test Recruiter",
        "company_name": "Acme Innovations",
        "job_role": "Senior Python Developer",
        "custom_intro": "This is a live test of your automated job application system."
    }

    content = mailer.render_content(dummy_recipient)
    msg = mailer.build_message(test_email, content, attachment_paths)

    try:
        mailer.send_single_email(test_email, msg)
        log_success(f"Test email successfully sent to {test_email}! Check your inbox and spam folder.")
    except Exception as e:
        log_error(f"Failed to send test email: {e}")


def run_campaign(mailer: JobMailer, tracker: DeliveryTracker, recipients: List[Dict[str, str]], 
                 attachment_paths: List[Path], limit: int, safety_cfg: dict):
    """Executes the live campaign with deduplication, safety delays, and quotas."""
    cooldown_emails = tracker.get_recently_contacted_emails()
    min_delay = safety_cfg.get("min_delay_seconds", 20)
    max_delay = safety_cfg.get("max_delay_seconds", 45)
    max_batch = min(limit or safety_cfg.get("max_batch_size", 50), len(recipients))

    log_info(f"Starting live dispatch. Maximum batch limit: {max_batch}")
    log_info(f"Anti-spam delay configured: between {min_delay}s and {max_delay}s per email.")

    processed_count = 0
    success_count = 0

    for idx, recipient in enumerate(recipients, start=1):
        if processed_count >= max_batch:
            log_warning(f"Reached batch limit of {max_batch}. Stopping for today.")
            break

        hr_email = recipient.get("hr_email", "").strip().lower()
        company = recipient.get("company_name", "Unknown")
        role = recipient.get("job_role", "Software Engineer")

        # 1. Validation
        if not is_valid_email(hr_email):
            log_warning(f"[{idx}/{len(recipients)}] Skipping invalid email: '{hr_email}' ({company})")
            continue

        # 2. Deduplication check
        if hr_email in cooldown_emails:
            log_warning(f"[{idx}/{len(recipients)}] Skipping {hr_email} ({company}) - already contacted within cooldown window.")
            continue

        # 3. Render and Build
        content = mailer.render_content(recipient)
        msg = mailer.build_message(hr_email, content, attachment_paths)

        # 4. Dispatch
        log_info(f"[{idx}/{len(recipients)}] Dispatching to {hr_email} ({company} - {role})...")
        try:
            mailer.send_single_email(hr_email, msg)
            tracker.log_result(hr_email, company, role, "SUCCESS")
            cooldown_emails.add(hr_email)
            success_count += 1
            processed_count += 1
            log_success(f"Sent successfully to {hr_email}")

            # Sleep jitter (only if there are more emails to send)
            if processed_count < max_batch and idx < len(recipients):
                sleep_duration = random.uniform(min_delay, max_delay)
                log_info(f"Waiting {sleep_duration:.1f} seconds to protect sender domain reputation...")
                time.sleep(sleep_duration)

        except Exception as e:
            err_msg = str(e)
            log_error(f"Failed sending to {hr_email}: {err_msg}")
            tracker.log_result(hr_email, company, role, "FAILED", err_msg)
            # If credentials fail, abort immediately to prevent repeated lockouts
            if "authentication" in err_msg.lower() or "username and password not accepted" in err_msg.lower():
                log_error("Aborting campaign: Authentication failed. Please verify your .env credentials.")
                break

    log_success(f"Campaign run complete! Successfully sent: {success_count}/{processed_count} emails.")


def main():
    parser = argparse.ArgumentParser(description="Automated Job Application Mailer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Render and preview emails without sending.")
    group.add_argument("--test-email", type=str, help="Send a single test application to your own email address.")
    group.add_argument("--send", action="store_true", help="Execute the real campaign sending to contacts in recipients.csv.")

    parser.add_argument("--file", type=str, default=None, help="Path to custom Excel (.xlsx/.xls) or CSV (.csv) file.")
    parser.add_argument("--limit", type=int, default=None, help="Override maximum emails to send during this run.")
    args = parser.parse_args()

    # Load configuration
    try:
        config = load_settings()
    except Exception as e:
        log_error(f"Configuration error: {e}")
        sys.exit(1)

    # Validate attachments
    valid_attachments, attachment_errors = validate_attachments(config["base_dir"], config["attachments"])
    if attachment_errors:
        for err in attachment_errors:
            log_warning(err)
        if not valid_attachments:
            log_error("No valid attachments found. Please place your Resume in the attachments folder.")
            sys.exit(1)

    mailer = JobMailer(config)

    # Single test email
    if args.test_email:
        if not is_valid_email(args.test_email):
            log_error(f"Invalid test email address: {args.test_email}")
            sys.exit(1)
        run_test_email(mailer, args.test_email, valid_attachments)
        return

    # Locate recipients file (supports --file, or data/recipients.xlsx, or data/recipients.csv)
    if args.file:
        recipients_path = Path(args.file)
        if not recipients_path.is_absolute():
            recipients_path = config["base_dir"] / recipients_path
    else:
        excel_default = config["base_dir"] / "data" / "recipients.xlsx"
        if excel_default.exists():
            recipients_path = excel_default
        else:
            recipients_path = config["base_dir"] / config["paths"].get("recipients_csv", "data/recipients.csv")

    log_info(f"Loading recipients from: {recipients_path.name}")
    try:
        recipients = load_recipients(recipients_path)
    except Exception as e:
        log_error(f"Failed to load recipients: {e}")
        sys.exit(1)

    # Dry run
    if args.dry_run:
        run_dry_run(mailer, recipients, valid_attachments)
        return

    # Live Send
    if args.send:
        history_path = config["base_dir"] / config["paths"].get("sent_history_csv", "data/sent_history.csv")
        cooldown_days = config["safety"].get("cooldown_days", 30)
        tracker = DeliveryTracker(history_path, cooldown_days=cooldown_days)
        run_campaign(mailer, tracker, recipients, valid_attachments, args.limit, config["safety"])


if __name__ == "__main__":
    main()
