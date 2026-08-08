"""
Gmail-based application confirmation tracker.

Searches the inbox for confirmation emails from companies we've applied to
and updates the pipeline state accordingly.
"""
from __future__ import annotations

import email
import imaplib
import os
import re
from datetime import datetime, timedelta


IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

CONFIRMATION_KEYWORDS = [
    "application received",
    "thank you for applying",
    "we received your application",
    "your application has been",
    "application submitted",
    "application confirmation",
    "thanks for your application",
    "we got your application",
]

REJECTION_KEYWORDS = [
    "we have decided",
    "not moving forward",
    "not be moving forward",
    "other candidates",
    "position has been filled",
    "unfortunately",
    "we will not",
    "won't be moving",
]

INTERVIEW_KEYWORDS = [
    "interview",
    "next steps",
    "schedule a call",
    "would like to speak",
    "move you forward",
    "pleased to invite",
]


class GmailTracker:
    def __init__(self):
        self.address = os.environ.get("GMAIL_ADDRESS", "")
        self.password = os.environ.get("GMAIL_APP_PASSWORD", "")
        if not self.address or not self.password:
            raise ValueError(
                "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_confirmation(self, company: str, days_back: int = 7) -> dict | None:
        """
        Search Gmail for a confirmation/rejection/interview email from `company`
        within the last `days_back` days.

        Returns a dict with keys: status, subject, date, snippet
        or None if nothing found.
        """
        try:
            mail = self._connect()
            mail.select("inbox")

            since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            company_slug = company.split()[0]  # Use first word to broaden search

            # Search by company name in subject or from
            _, msg_ids = mail.search(
                None,
                f'(SINCE "{since}" SUBJECT "{company_slug}")',
            )

            results = []
            for mid in (msg_ids[0].split() if msg_ids[0] else []):
                _, data = mail.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                subject = self._decode_header(msg.get("Subject", ""))
                sender = msg.get("From", "")
                date_str = msg.get("Date", "")
                body = self._get_body(msg)

                combined = (subject + " " + body).lower()
                status = self._classify(combined)

                if status:
                    results.append({
                        "status": status,
                        "subject": subject,
                        "from": sender,
                        "date": date_str,
                        "snippet": body[:200].strip(),
                    })

            mail.logout()

            # Return the most relevant result (prefer interview > confirmed > rejected)
            priority = {"interview": 0, "confirmed": 1, "rejected": 2}
            results.sort(key=lambda r: priority.get(r["status"], 9))
            return results[0] if results else None

        except Exception as e:
            print(f"[GmailTracker] Error checking {company}: {e}")
            return None

    def scan_all_confirmations(self, companies: list[str], days_back: int = 14) -> dict:
        """
        Check multiple companies at once. Returns {company: result_dict}.
        """
        results = {}
        try:
            mail = self._connect()
            mail.select("inbox")
            since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

            for company in companies:
                company_slug = company.split()[0]
                _, msg_ids = mail.search(None, f'(SINCE "{since}" SUBJECT "{company_slug}")')
                found = None
                for mid in (msg_ids[0].split() if msg_ids[0] else []):
                    _, data = mail.fetch(mid, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    subject = self._decode_header(msg.get("Subject", ""))
                    body = self._get_body(msg)
                    combined = (subject + " " + body).lower()
                    status = self._classify(combined)
                    if status:
                        found = {
                            "status": status,
                            "subject": subject,
                            "from": msg.get("From", ""),
                            "date": msg.get("Date", ""),
                            "snippet": body[:200].strip(),
                        }
                        if status == "interview":
                            break  # Best possible result
                if found:
                    results[company] = found

            mail.logout()
        except Exception as e:
            print(f"[GmailTracker] Scan error: {e}")

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(self.address, self.password)
        return mail

    def _classify(self, text: str) -> str | None:
        if any(kw in text for kw in INTERVIEW_KEYWORDS):
            return "interview"
        if any(kw in text for kw in CONFIRMATION_KEYWORDS):
            return "confirmed"
        if any(kw in text for kw in REJECTION_KEYWORDS):
            return "rejected"
        return None

    def _get_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except Exception:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except Exception:
                pass
        return body[:2000]

    def _decode_header(self, value: str) -> str:
        parts = email.header.decode_header(value)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(enc or "utf-8", errors="ignore"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)
