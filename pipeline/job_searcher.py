"""
Playwright-based job searcher.

Primary source: jobright.ai/jobs/recommend (AI-matched recommendations).
Fallback sources: LinkedIn Jobs, Indeed.
Uses Claude to score each job against the candidate profile.
"""
from __future__ import annotations

import json
import re
import time
import random
from dataclasses import dataclass, field, asdict
from typing import Optional

import anthropic
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from pipeline.profile_analyzer import ProfileAnalyzer


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str                  # jobright / LinkedIn / Indeed job page URL
    apply_url: str = ""       # direct ATS / company apply URL (extracted from jobright)
    description: str = ""
    source: str = "jobright"
    match_score: int = 0
    match_reason: str = ""
    status: str = "found"  # found | tailored | applied | failed | skipped

    def to_dict(self) -> dict:
        return asdict(self)


class JobSearcher:
    LINKEDIN_BASE = "https://www.linkedin.com/jobs/search/"
    INDEED_BASE = "https://www.indeed.com/jobs"
    JOBRIGHT_RECOMMEND = "https://jobright.ai/jobs/recommend"

    def __init__(self, profile_analyzer: ProfileAnalyzer, headless: bool = True):
        self.profile = profile_analyzer
        self.client = anthropic.Anthropic()
        self.headless = headless

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_best_jobs(
        self,
        queries: list[str] | None = None,
        location: str = "United States",
        limit: int = 10,
        sources: list[str] | None = None,
    ) -> list[Job]:
        """Search multiple sources and return top-scored jobs."""
        if queries is None:
            queries = self.profile.get_search_queries()
        if sources is None:
            sources = ["jobright"]

        all_jobs: list[Job] = []

        from pipeline.config import JOBRIGHT_PROFILE_DIR
        with sync_playwright() as pw:
            # jobright requires login — use persistent profile
            if "jobright" in sources:
                ctx = pw.chromium.launch_persistent_context(
                    user_data_dir=JOBRIGHT_PROFILE_DIR,
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                    viewport={"width": 1440, "height": 900},
                )
                page = ctx.new_page()
                # Inject session cookie on every run to ensure auth persists
                import os as _os
                _sid = _os.environ.get("JOBRIGHT_SESSION_ID", "")
                _uid = _os.environ.get("JOBRIGHT_USER_ID", "")
                if _sid:
                    page.goto("https://jobright.ai", wait_until="domcontentloaded", timeout=15000)
                    ctx.add_cookies([{
                        "name": "SESSION_ID", "value": _sid,
                        "domain": "jobright.ai", "path": "/",
                        "httpOnly": True, "secure": True,
                    }])
                    if _uid:
                        page.evaluate(f"() => localStorage.setItem('JR_userid', '{_uid}')")
                jobs = self._search_jobright(page, limit=limit * 2)
                all_jobs.extend(jobs)
                ctx.close()
            else:
                browser = pw.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )
                ctx = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1440, "height": 900},
                )
                page = ctx.new_page()
                for query in queries:
                    if "linkedin" in sources:
                        jobs = self._search_linkedin(page, query, location, per_query=5)
                        all_jobs.extend(jobs)
                    if "indeed" in sources:
                        jobs = self._search_indeed(page, query, location, per_query=5)
                        all_jobs.extend(jobs)
                browser.close()

            # De-duplicate by URL
            seen: set[str] = set()
            unique: list[Job] = []
            for job in all_jobs:
                if job.url not in seen:
                    seen.add(job.url)
                    unique.append(job)

            # Fetch full descriptions for top candidates (non-jobright only)
            if "jobright" not in sources:
                for job in unique[:20]:
                    if not job.description:
                        self._fetch_description(page, job)
                    _sleep(1, 2)

        # Score all jobs against the profile
        scored = self._score_jobs(unique)
        scored.sort(key=lambda j: j.match_score, reverse=True)
        return scored[:limit]

    # ------------------------------------------------------------------
    # Jobright search
    # ------------------------------------------------------------------

    def _search_jobright(self, page: Page, limit: int = 20) -> list[Job]:
        """Scrape AI-matched recommendations from jobright.ai/jobs/recommend."""
        try:
            page.goto(self.JOBRIGHT_RECOMMEND, wait_until="domcontentloaded", timeout=25000)
            _sleep(3, 4)

            # Check login
            if "login" in page.url.lower() or page.query_selector("input[type='email']"):
                print("[JobSearcher] Not logged into jobright.ai — open the browser and log in, then rerun.")
                return []

            jobs: list[Job] = []
            seen_urls: set[str] = set()
            scroll_attempts = 0

            while len(jobs) < limit and scroll_attempts < 8:
                # Collect all job cards currently visible
                # jobright uses various card structures — try multiple selectors
                # Top-level job cards have a job title h2 inside them
                all_cards = page.query_selector_all("div[class*='job-card']")
                cards = [c for c in all_cards if c.query_selector("h2[class*='job-title']")]

                for card in cards:
                    if len(jobs) >= limit:
                        break
                    try:
                        job = self._parse_jobright_card(card, page)
                        if job and job.url not in seen_urls:
                            seen_urls.add(job.url)
                            jobs.append(job)
                    except Exception:
                        continue

                if len(jobs) >= limit:
                    break

                # Scroll down to load more
                page.mouse.wheel(0, 1200)
                _sleep(2, 3)
                scroll_attempts += 1

            print(f"[JobSearcher] Jobright: found {len(jobs)} jobs")
            return jobs

        except PWTimeout:
            print("[JobSearcher] Jobright timeout")
            return []
        except Exception as e:
            print(f"[JobSearcher] Jobright error: {e}")
            return []

    def _parse_jobright_card(self, card, page: Page) -> Job | None:
        """Extract job info from a single jobright card."""
        # Job ID is stored in the card's HTML id attribute
        job_id = card.get_attribute("id") or ""

        # Title
        title_el = card.query_selector("h2[class*='job-title']") or card.query_selector("h2")
        title = title_el.inner_text().strip() if title_el else ""

        # Company
        company_el = card.query_selector("div[class*='company-name']")
        company = company_el.inner_text().strip() if company_el else ""

        # Location — first span after the position icon
        location = ""
        try:
            loc_img = card.query_selector("img[alt='position']")
            if loc_img:
                loc_parent = loc_img.evaluate_handle("el => el.parentElement")
                loc_sibling = loc_parent.evaluate_handle("el => el.nextElementSibling")
                location = loc_sibling.inner_text().strip()
        except Exception:
            pass

        # Description from "Why this job is a match" section
        description = ""
        try:
            desc_el = card.query_selector("[class*='rating-desc']")
            if desc_el:
                description = desc_el.inner_text().strip()[:4000]
        except Exception:
            pass

        if not title:
            return None

        job_url = f"https://jobright.ai/jobs/info/{job_id}" if job_id else ""
        if not job_url:
            return None

        return Job(
            id=job_id or _slug(f"{company}-{title}"),
            title=title,
            company=company,
            location=location,
            url=job_url,
            apply_url="",
            description=description,
            source="jobright",
        )

    # ------------------------------------------------------------------
    # LinkedIn search
    # ------------------------------------------------------------------

    def _search_linkedin(
        self, page: Page, query: str, location: str, per_query: int = 5
    ) -> list[Job]:
        params = f"?keywords={_encode(query)}&location={_encode(location)}&f_TPR=r86400"
        url = self.LINKEDIN_BASE + params
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            _sleep(2, 3)
            page.mouse.wheel(0, 800)
            _sleep(1, 2)

            cards = page.query_selector_all("ul.jobs-search__results-list > li")
            jobs: list[Job] = []
            for card in cards[:per_query]:
                try:
                    title_el = card.query_selector("h3.base-search-card__title")
                    company_el = card.query_selector("h4.base-search-card__subtitle")
                    location_el = card.query_selector("span.job-search-card__location")
                    link_el = card.query_selector("a.base-card__full-link")

                    title = title_el.inner_text().strip() if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    location_text = location_el.inner_text().strip() if location_el else ""
                    href = link_el.get_attribute("href") if link_el else ""

                    if not title or not href:
                        continue

                    job_id = _slug(f"{company}-{title}")
                    jobs.append(
                        Job(
                            id=job_id,
                            title=title,
                            company=company,
                            location=location_text,
                            url=href.split("?")[0],
                            source="linkedin",
                        )
                    )
                except Exception:
                    continue
            return jobs
        except PWTimeout:
            print(f"[JobSearcher] LinkedIn timeout for query: {query}")
            return []
        except Exception as e:
            print(f"[JobSearcher] LinkedIn error: {e}")
            return []

    # ------------------------------------------------------------------
    # Indeed search
    # ------------------------------------------------------------------

    def _search_indeed(
        self, page: Page, query: str, location: str, per_query: int = 5
    ) -> list[Job]:
        params = f"?q={_encode(query)}&l={_encode(location)}&fromage=1"
        url = self.INDEED_BASE + params
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            _sleep(2, 3)

            cards = page.query_selector_all("div.job_seen_beacon")
            jobs: list[Job] = []
            for card in cards[:per_query]:
                try:
                    title_el = card.query_selector("h2.jobTitle span[title]")
                    company_el = card.query_selector("span.companyName")
                    location_el = card.query_selector("div.companyLocation")
                    link_el = card.query_selector("a[id^='job_']")

                    title = title_el.get_attribute("title") if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    location_text = location_el.inner_text().strip() if location_el else ""
                    href = link_el.get_attribute("href") if link_el else ""

                    if not title or not href:
                        continue

                    full_url = f"https://www.indeed.com{href}" if href.startswith("/") else href
                    job_id = _slug(f"{company}-{title}")
                    jobs.append(
                        Job(
                            id=job_id,
                            title=title,
                            company=company,
                            location=location_text,
                            url=full_url.split("&")[0],
                            source="indeed",
                        )
                    )
                except Exception:
                    continue
            return jobs
        except PWTimeout:
            print(f"[JobSearcher] Indeed timeout for query: {query}")
            return []
        except Exception as e:
            print(f"[JobSearcher] Indeed error: {e}")
            return []

    # ------------------------------------------------------------------
    # Fetch full job description
    # ------------------------------------------------------------------

    def _fetch_description(self, page: Page, job: Job) -> None:
        try:
            page.goto(job.url, wait_until="domcontentloaded", timeout=15000)
            _sleep(2, 3)

            if job.source == "linkedin":
                # Try to expand description
                see_more = page.query_selector("button.show-more-less-html__button--more")
                if see_more:
                    see_more.click()
                    _sleep(0.5, 1)
                desc_el = page.query_selector("div.show-more-less-html__markup")
                if not desc_el:
                    desc_el = page.query_selector("section.description")

            elif job.source == "indeed":
                desc_el = page.query_selector("div#jobDescriptionText")

            else:
                desc_el = None

            if desc_el:
                text = desc_el.inner_text().strip()
                job.description = text[:4000]  # Cap to keep Claude prompts manageable
        except Exception as e:
            print(f"[JobSearcher] Could not fetch description for {job.url}: {e}")

    # ------------------------------------------------------------------
    # Claude scoring
    # ------------------------------------------------------------------

    def _score_jobs(self, jobs: list[Job]) -> list[Job]:
        if not jobs:
            return jobs

        profile = self.profile.analyze()
        skills_text = self.profile.get_plain_skills()

        jobs_payload = [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "description": j.description[:1500] if j.description else "(no description)",
            }
            for j in jobs
        ]

        prompt = f"""You are evaluating job matches for a candidate. Return ONLY a JSON array.

CANDIDATE PROFILE:
- Name: {profile.get('name')}
- Experience Level: {profile.get('experience_level')} ({profile.get('years_of_experience')} years)
- Target Roles: {', '.join(profile.get('target_roles', []))}
- Domains: {', '.join(profile.get('domains', []))}
- Core Skills: {skills_text[:800]}

JOBS TO SCORE:
{json.dumps(jobs_payload, indent=2)[:6000]}

For each job return:
[
  {{
    "id": "...",
    "match_score": 85,
    "match_reason": "One sentence why this is a good/bad fit."
  }},
  ...
]

Score 0-100. 80+ = strong match. Be realistic."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.split("```")[0].strip()

            scores: list[dict] = json.loads(content)
            score_map = {s["id"]: s for s in scores}
            for job in jobs:
                if job.id in score_map:
                    job.match_score = score_map[job.id].get("match_score", 0)
                    job.match_reason = score_map[job.id].get("match_reason", "")
        except Exception as e:
            print(f"[JobSearcher] Scoring error: {e}")

        return jobs


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _encode(text: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(text)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower())[:60].strip("-")


def _sleep(lo: float, hi: float = 0) -> None:
    duration = lo if hi == 0 else random.uniform(lo, hi)
    time.sleep(duration)
