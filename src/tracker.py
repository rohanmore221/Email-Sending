import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set

HISTORY_HEADERS = ["timestamp", "hr_email", "company_name", "job_role", "status", "error_message"]

class DeliveryTracker:
    def __init__(self, history_file_path: Path, cooldown_days: int = 30):
        self.history_path = history_file_path
        self.cooldown_days = cooldown_days
        self._ensure_history_file()

    def _ensure_history_file(self):
        """Creates the history file with headers if it doesn't already exist."""
        if not self.history_path.exists():
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(HISTORY_HEADERS)

    def get_recently_contacted_emails(self) -> Set[str]:
        """Returns lowercase emails that were successfully contacted within the cooldown window."""
        recently_contacted = set()
        if not self.history_path.exists():
            return recently_contacted

        cutoff = datetime.now() - timedelta(days=self.cooldown_days)

        with open(self.history_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("status") == "SUCCESS":
                    timestamp_str = row.get("timestamp", "")
                    try:
                        sent_time = datetime.fromisoformat(timestamp_str)
                        if sent_time >= cutoff:
                            email = row.get("hr_email", "").strip().lower()
                            if email:
                                recently_contacted.add(email)
                    except ValueError:
                        # Fallback: if timestamp can't be parsed, treat as contacted
                        email = row.get("hr_email", "").strip().lower()
                        if email:
                            recently_contacted.add(email)

        return recently_contacted

    def log_result(self, hr_email: str, company_name: str, job_role: str, status: str, error_message: str = ""):
        """Appends a new send attempt result into the history CSV."""
        with open(self.history_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                hr_email.strip(),
                company_name.strip(),
                job_role.strip(),
                status,
                error_message
            ])
