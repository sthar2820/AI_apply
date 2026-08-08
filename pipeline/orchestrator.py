"""
Full automated job application pipeline.

Usage:
  # Search only — find and score matching jobs, save to state file
  python -m pipeline.orchestrator --search

  # Full pipeline — search, tailor, generate docs, apply
  python -m pipeline.orchestrator --apply

  # Apply to a specific job URL (LinkedIn or Indeed)
  python -m pipeline.orchestrator --apply --url "https://www.linkedin.com/jobs/view/..."

  # Dry run — tailor + generate docs but do NOT submit
  python -m pipeline.orchestrator --dry-run

Options:
  --queries "Software Engineer" "ML Engineer"   Override default search queries
  --location "New York, NY"                     Job location filter
  --limit 5                                     Max jobs to process
  --headless                                    Run browser in headless mode
  --min-score 70                                Minimum match score to apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env if present
def _load_env():
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

# Allow running as `python -m pipeline.orchestrator` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.profile_analyzer import ProfileAnalyzer
from pipeline.job_searcher import JobSearcher, Job
from pipeline.resume_tailor import ResumeTailor
from pipeline.cover_letter_ai import CoverLetterAI
from pipeline.config import (
    CANDIDATE, TARGET_ROLES, DEFAULT_LOCATION,
    DEFAULT_SOURCES, DEFAULT_LIMIT, MIN_MATCH_SCORE,
)

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RESUME_YML = CANDIDATE["resume_yml"]
ABOUT_YML = CANDIDATE.get("about_yml")
COVERLETTER_YML = CANDIDATE["coverletter_yml"]
APPLICATIONS_DIR = BASE_DIR / "applications"
STATE_FILE = APPLICATIONS_DIR / "pipeline_state.json"


# ------------------------------------------------------------------
# State management
# ------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"applications": [], "last_run": None}


def save_state(state: dict) -> None:
    APPLICATIONS_DIR.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def already_applied(state: dict, job: Job) -> bool:
    for app in state["applications"]:
        if app["url"] == job.url and app["status"] in ("applied", "submitted"):
            return True
    return False


def update_state(state: dict, job: Job, status: str, docs: dict | None = None) -> None:
    # Check if entry exists
    for app in state["applications"]:
        if app["url"] == job.url:
            app["status"] = status
            app["updated_at"] = datetime.now().isoformat()
            if docs:
                app.update(docs)
            return

    entry = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "source": job.source,
        "match_score": job.match_score,
        "match_reason": job.match_reason,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    if docs:
        entry.update(docs)
    state["applications"].append(entry)


# ------------------------------------------------------------------
# Pipeline stages
# ------------------------------------------------------------------

def stage_search(
    profile: ProfileAnalyzer,
    queries: list[str] | None,
    location: str,
    limit: int,
    headless: bool,
    sources: list[str],
) -> list[Job]:
    print("\n=== STAGE 1: Job Search ===")
    searcher = JobSearcher(profile, headless=headless)
    jobs = searcher.find_best_jobs(
        queries=queries,
        location=location,
        limit=limit,
        sources=sources,
    )
    print(f"\nFound {len(jobs)} matching jobs:")
    for i, job in enumerate(jobs, 1):
        print(f"  {i:2}. [{job.match_score:3}] {job.title} @ {job.company} ({job.location})")
        if job.match_reason:
            print(f"       → {job.match_reason}")
    return jobs


def stage_tailor(
    profile: ProfileAnalyzer,
    job: Job,
    output_dir: str,
) -> str | None:
    print(f"\n=== STAGE 2: Tailoring Resume for {job.company} ===")
    try:
        tailor = ResumeTailor(profile)
        pdf = tailor.tailor(job, output_dir)
        return pdf
    except Exception as e:
        print(f"[Orchestrator] Resume tailoring failed: {e}")
        return None


def stage_cover_letter(
    profile: ProfileAnalyzer,
    job: Job,
    output_dir: str,
) -> str | None:
    print(f"\n=== STAGE 3: Generating Cover Letter for {job.company} ===")
    try:
        cl_ai = CoverLetterAI(profile, str(COVERLETTER_YML))
        pdf = cl_ai.generate(job, output_dir)
        return pdf
    except Exception as e:
        print(f"[Orchestrator] Cover letter generation failed: {e}")
        return None


def stage_apply(
    profile: ProfileAnalyzer,
    job: Job,
    resume_pdf: str,
    cover_letter_pdf: str | None,
    headless: bool,
) -> bool:
    print(f"\n=== STAGE 4: Applying to {job.title} @ {job.company} ===")
    # Email application (apply_url contains an @ sign)
    if job.apply_url and "@" in job.apply_url:
        from auto_apply.email_applier import EmailApplier
        applier = EmailApplier(profile)
        return applier.apply(job, resume_pdf, cover_letter_pdf)

    if job.source == "jobright":
        from auto_apply.jobright_applier import JobrightApplier
        applier = JobrightApplier(profile, headless=headless)
    elif job.source == "linkedin":
        from auto_apply.linkedin_applier import LinkedInApplier
        applier = LinkedInApplier(profile, headless=headless)
    elif job.source == "indeed":
        from auto_apply.indeed_applier import IndeedApplier
        applier = IndeedApplier(profile, headless=headless)
    else:
        print(f"[Orchestrator] Unknown source: {job.source}. Skipping apply.")
        return False

    return applier.apply(job, resume_pdf, cover_letter_pdf)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    state = load_state()

    # Load profile
    print("\n=== Loading Profile ===")
    profile = ProfileAnalyzer(
        str(RESUME_YML),
        str(ABOUT_YML) if ABOUT_YML and Path(ABOUT_YML).exists() else None,
    )
    profile_data = profile.analyze()
    print(f"Profile: {profile_data.get('name')} | {profile_data.get('experience_level')} | "
          f"{', '.join(profile_data.get('domains', []))}")

    # If a specific URL is provided, create a synthetic job
    if args.url:
        job = Job(
            id="manual",
            title=args.title or "Position",
            company=args.company or "Company",
            location=args.location or "Remote",
            url=args.url,
            source="linkedin" if "linkedin.com" in args.url else "indeed",
        )
        jobs = [job]
    else:
        # Search for jobs
        queries = args.queries if args.queries else TARGET_ROLES
        sources = args.sources if args.sources else DEFAULT_SOURCES
        jobs = stage_search(
            profile,
            queries=queries,
            location=args.location,
            limit=args.limit,
            headless=args.headless,
            sources=sources,
        )

    # Filter by minimum score (skip for manually specified URL)
    if not args.url:
        jobs = [j for j in jobs if j.match_score >= args.min_score]
        if not jobs:
            print(f"\nNo jobs found with match score >= {args.min_score}.")
            return

    # Process each job
    for job in jobs:
        print(f"\n{'='*60}")
        print(f"Processing: {job.title} @ {job.company}")
        print(f"Score: {job.match_score} | {job.match_reason}")

        if already_applied(state, job) and not args.url:
            print(f"Already applied. Skipping.")
            continue

        # Output directory per company
        company_slug = job.company.replace(" ", "_").replace("/", "_")
        role_slug = job.title.replace(" ", "_").replace("/", "_")
        job_output_dir = str(APPLICATIONS_DIR / company_slug)
        os.makedirs(job_output_dir, exist_ok=True)

        update_state(state, job, "processing")
        save_state(state)

        # Tailor resume
        resume_pdf = stage_tailor(profile, job, job_output_dir)
        if not resume_pdf:
            update_state(state, job, "failed", {"error": "resume_tailor_failed"})
            save_state(state)
            continue

        # Generate cover letter
        cover_letter_pdf = stage_cover_letter(profile, job, job_output_dir)
        if not cover_letter_pdf:
            print("[Orchestrator] Cover letter failed. Continuing without it.")

        update_state(state, job, "tailored", {
            "resume_pdf": resume_pdf,
            "cover_letter_pdf": cover_letter_pdf,
        })
        save_state(state)

        # Apply (unless dry-run or search-only)
        if args.apply or args.url:
            if args.dry_run:
                print("[Orchestrator] Dry run: skipping submission.")
                update_state(state, job, "dry_run")
            else:
                success = stage_apply(profile, job, resume_pdf, cover_letter_pdf, args.headless)
                status = "applied" if success else "apply_failed"
                update_state(state, job, status)

            save_state(state)

    print(f"\n=== Pipeline complete. State saved to: {STATE_FILE} ===")
    _print_summary(state)

    # Optional: scan Gmail for confirmations on recently applied jobs
    if getattr(args, "track", False) or getattr(args, "apply", False):
        _stage_track_confirmations(state)


def _stage_track_confirmations(state: dict) -> None:
    """Check Gmail for confirmation/rejection/interview emails for applied jobs."""
    applied = [a for a in state.get("applications", []) if a["status"] in ("applied", "confirmed", "tailored")]
    if not applied:
        return
    print("\n=== STAGE 5: Gmail Confirmation Check ===")
    try:
        from pipeline.gmail_tracker import GmailTracker
        tracker = GmailTracker()
        companies = [a["company"] for a in applied]
        results = tracker.scan_all_confirmations(companies, days_back=14)
        updated = False
        for app in applied:
            result = results.get(app["company"])
            if result:
                icon = {"interview": "🎉", "confirmed": "✓", "rejected": "✗"}.get(result["status"], "·")
                print(f"  {icon} {app['company']}: {result['status'].upper()} — {result['subject']}")
                app["gmail_status"] = result["status"]
                app["gmail_subject"] = result["subject"]
                app["gmail_date"] = result["date"]
                if result["status"] == "interview":
                    app["status"] = "interview"
                elif result["status"] == "rejected":
                    app["status"] = "rejected"
                updated = True
        if updated:
            save_state(state)
            print("  State updated with Gmail results.")
        else:
            print("  No confirmation emails found yet.")
    except Exception as e:
        print(f"  [GmailTracker] Skipped: {e}")


def _print_summary(state: dict) -> None:
    apps = state.get("applications", [])
    if not apps:
        return
    print("\n--- Application Summary ---")
    for app in apps[-20:]:
        icon = {"applied": "✓", "tailored": "⚙", "failed": "✗", "dry_run": "~"}.get(
            app["status"], "·"
        )
        print(f"  {icon} [{app.get('match_score', '?'):3}] {app['title']} @ {app['company']} → {app['status']}")


# ------------------------------------------------------------------
# Login helper
# ------------------------------------------------------------------

def _login_browser(service: str) -> None:
    """Open a persistent browser profile so the user can log in manually."""
    from playwright.sync_api import sync_playwright
    from pipeline.config import JOBRIGHT_PROFILE_DIR, LINKEDIN_PROFILE_DIR

    urls = {
        "jobright": ("https://jobright.ai/login", JOBRIGHT_PROFILE_DIR),
        "linkedin": ("https://www.linkedin.com/login", JOBRIGHT_PROFILE_DIR),
    }
    url, profile_dir = urls[service]
    print(f"\nOpening {service} login page...")
    print(f"Profile dir: {profile_dir}")
    print("Log in manually, then close the browser window.\n")

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--no-sandbox"],
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.goto(url)
        input("Press ENTER here once you've logged in and the browser is ready...")
        ctx.close()
    print(f"Session saved to {profile_dir}. You can now run --apply.")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Automated job application pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--search", action="store_true", help="Search only, no apply")
    parser.add_argument("--apply", action="store_true", help="Search + tailor + apply")
    parser.add_argument("--track", action="store_true", help="Check Gmail for confirmations on past applications")
    parser.add_argument("--dry-run", action="store_true",
                        help="Tailor + generate docs but don't submit")
    parser.add_argument("--login", type=str, choices=["linkedin", "jobright"],
                        help="Open browser to log in to a service (saves session to profile)")

    parser.add_argument("--url", type=str, help="Apply to a specific job URL")
    parser.add_argument("--title", type=str, help="Job title (used with --url)")
    parser.add_argument("--company", type=str, help="Company name (used with --url)")

    parser.add_argument("--queries", nargs="+",
                        help=f"Job search queries (default: {TARGET_ROLES})")
    parser.add_argument("--location", type=str, default=DEFAULT_LOCATION,
                        help="Job location filter")
    parser.add_argument("--sources", nargs="+", default=DEFAULT_SOURCES,
                        choices=["jobright", "linkedin", "indeed"], help="Job sources to search")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="Max jobs to process per run")
    parser.add_argument("--min-score", type=int, default=MIN_MATCH_SCORE,
                        help="Minimum Claude match score (0-100) to apply")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser headless (default: visible)")

    args = parser.parse_args()

    # --login: open browser for manual login
    if args.login:
        _login_browser(args.login)
        return

    # Default to search if no mode specified
    if not any([args.search, args.apply, args.dry_run, args.url, args.track]):
        args.search = True

    # --track only: just scan Gmail and exit
    if args.track and not any([args.search, args.apply, args.dry_run, args.url]):
        state = load_state()
        _stage_track_confirmations(state)
        _print_summary(state)
        return

    run(args)


if __name__ == "__main__":
    main()
