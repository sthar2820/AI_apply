"""
Pipeline configuration — edit this file to switch candidates or target roles.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# Active candidate
# ------------------------------------------------------------------

CANDIDATE = dict(
    name="Rohan Shrestha",
    resume_yml=BASE_DIR / "resume" / "resume_da.yml",
    about_yml=None,  # set path if you have a full about YAML
    coverletter_yml=BASE_DIR / "coverletter" / "coverletter_rohan.yml",
)

# ------------------------------------------------------------------
# Job search settings
# ------------------------------------------------------------------

TARGET_ROLES = [
    "Data Analyst",
    "Business Intelligence Analyst",
    "Data Engineer",
    "BI Developer",
    "Analytics Engineer",
]

DEFAULT_LOCATION = "United States"
DEFAULT_SOURCES = ["jobright"]   # "jobright", "linkedin", "indeed"
DEFAULT_LIMIT = 5                # jobs to process per run
MIN_MATCH_SCORE = 70             # 0-100; skip jobs below this threshold

# ------------------------------------------------------------------
# Browser settings
# ------------------------------------------------------------------

# Path to a persistent Chromium profile where you're already logged in
# to LinkedIn/Indeed. Run `playwright install chromium` first, then log in
# once via: python -m pipeline.orchestrator --login linkedin
import os
JOBRIGHT_PROFILE_DIR = os.environ.get(
    "JOBRIGHT_USER_DATA_DIR",
    str(Path.home() / ".config" / "jobright-pw-profile"),  # Playwright Chromium profile (separate from Chrome)
)
JOBRIGHT_SESSION_ID = os.environ.get("JOBRIGHT_SESSION_ID", "")
JOBRIGHT_USER_ID = os.environ.get("JOBRIGHT_USER_ID", "")

# ------------------------------------------------------------------
# Gmail settings (confirmation tracking + email applications)
# ------------------------------------------------------------------
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "sthar2820@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
LINKEDIN_PROFILE_DIR = os.environ.get(
    "LINKEDIN_USER_DATA_DIR",
    str(Path.home() / ".config" / "linkedin-profile"),
)
INDEED_PROFILE_DIR = os.environ.get(
    "INDEED_USER_DATA_DIR",
    str(Path.home() / ".config" / "indeed-profile"),
)

# ------------------------------------------------------------------
# ATS account credentials (Workday, etc.)
# ------------------------------------------------------------------
ATS_EMAIL = os.environ.get("ATS_EMAIL", "sthar2820@gmail.com")
ATS_PASSWORD = os.environ.get("ATS_PASSWORD", "321@QWEaszxxc")
