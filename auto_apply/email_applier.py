"""
Email-based job applier.

For job postings that provide a contact email (e.g. "send resume to jobs@company.com"),
sends a tailored email with resume and cover letter as PDF attachments via Gmail SMTP.
"""
from __future__ import annotations


import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from auto_apply.base_applier import BaseApplier
from pipeline.job_searcher import Job
from pipeline.profile_analyzer import ProfileAnalyzer


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class EmailApplier(BaseApplier):
    def __init__(self, profile_analyzer: ProfileAnalyzer):
        super().__init__(profile_analyzer, headless=True)
        self.gmail_address = os.environ.get("GMAIL_ADDRESS", "")
        self.gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
        if not self.gmail_address or not self.gmail_password:
            raise ValueError(
                "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables."
            )

    def apply(self, job: Job, resume_pdf: str, cover_letter_pdf: str | None = None) -> bool:
        """Send application email with PDF attachments."""
        if not job.apply_url or "@" not in job.apply_url:
            print(f"[EmailApplier] No email address found for {job.company}. Skipping.")
            return False

        recipient = job.apply_url.strip()
        personal = self.profile.get_resume_data().get("personal", {})
        name = personal.get("name", "Rohan Shrestha")
        phone = personal.get("phone", "")

        subject = f"Application for {job.title} – {name}"
        body = self._build_body(name, phone, job)

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{name} <{self.gmail_address}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg["Reply-To"] = self.gmail_address
            msg.attach(MIMEText(body, "plain"))

            # Attach resume
            if resume_pdf and os.path.exists(resume_pdf):
                with open(resume_pdf, "rb") as f:
                    att = MIMEApplication(f.read(), _subtype="pdf")
                    att.add_header(
                        "Content-Disposition", "attachment",
                        filename=f"{name.replace(' ', '_')}_Resume.pdf"
                    )
                    msg.attach(att)

            # Attach cover letter
            if cover_letter_pdf and os.path.exists(cover_letter_pdf):
                with open(cover_letter_pdf, "rb") as f:
                    att = MIMEApplication(f.read(), _subtype="pdf")
                    att.add_header(
                        "Content-Disposition", "attachment",
                        filename=f"{name.replace(' ', '_')}_CoverLetter.pdf"
                    )
                    msg.attach(att)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_password)
                server.sendmail(self.gmail_address, recipient, msg.as_string())

            print(f"[EmailApplier] ✓ Email sent to {recipient} for {job.title} @ {job.company}")
            return True

        except Exception as e:
            print(f"[EmailApplier] Failed to send email: {e}")
            return False

    def _build_body(self, name: str, phone: str, job: Job) -> str:
        personal = self.profile.get_resume_data().get("personal", {})
        linkedin = personal.get("linkedin", "")
        website = personal.get("website", "")
        return f"""Dear Hiring Team,

I am writing to apply for the {job.title} position at {job.company}. Please find my resume and cover letter attached.

I look forward to the opportunity to discuss how my background in data analytics and business intelligence can contribute to your team.

Best regards,
{name}
{phone}
{linkedin}
{website}
"""
