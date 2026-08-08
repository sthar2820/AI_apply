"""
Base class for automated job application bots.
Provides shared Playwright utilities: slow typing, smart waiting,
screenshot-on-error, and Claude-powered question answering.
"""
from __future__ import annotations


import json
import os
import random
import time
from abc import ABC, abstractmethod

import anthropic
from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

from pipeline.job_searcher import Job
from pipeline.profile_analyzer import ProfileAnalyzer


class BaseApplier(ABC):
    def __init__(self, profile_analyzer: ProfileAnalyzer, headless: bool = False):
        """
        headless=False lets you watch (and intervene) during application.
        Set headless=True for fully unattended runs after you've verified it works.
        """
        self.profile = profile_analyzer
        self.client = anthropic.Anthropic()
        self.headless = headless

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def apply(self, job: Job, resume_pdf: str, cover_letter_pdf: str | None = None) -> bool:
        """Apply to a single job. Returns True if submitted successfully."""
        ...

    # ------------------------------------------------------------------
    # Playwright utilities
    # ------------------------------------------------------------------

    def _slow_type(self, locator: Locator, text: str, delay_ms: int = 60) -> None:
        """Type text character by character to mimic human input."""
        locator.click()
        time.sleep(0.3)
        for ch in text:
            locator.type(ch, delay=delay_ms)
            time.sleep(random.uniform(0.01, 0.04))

    def _wait_and_click(self, page: Page, selector: str, timeout: int = 10000) -> bool:
        try:
            el = page.wait_for_selector(selector, timeout=timeout)
            if el:
                el.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.3, 0.7))
                el.click()
                return True
        except PWTimeout:
            pass
        return False

    def _fill_field(self, page: Page, selector: str, value: str, clear: bool = True) -> bool:
        try:
            el = page.wait_for_selector(selector, timeout=5000)
            if el:
                el.scroll_into_view_if_needed()
                if clear:
                    el.click(click_count=3)
                    time.sleep(0.1)
                self._slow_type(el, value)
                return True
        except PWTimeout:
            pass
        return False

    def _screenshot(self, page: Page, label: str, output_dir: str = "debug") -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{label}.png")
        page.screenshot(path=path)
        print(f"[Applier] Screenshot saved: {path}")

    def _human_scroll(self, page: Page, distance: int = 600) -> None:
        page.mouse.wheel(0, distance)
        time.sleep(random.uniform(0.4, 0.9))

    def _random_sleep(self, lo: float = 1.0, hi: float = 2.5) -> None:
        time.sleep(random.uniform(lo, hi))

    # ------------------------------------------------------------------
    # Claude: answer screening questions
    # ------------------------------------------------------------------

    def answer_screening_question(self, question: str, options: list[str] | None = None) -> str:
        """Use Claude to answer a screening/application question."""
        profile = self.profile.analyze()
        resume_data = self.profile.get_resume_data()

        experience = resume_data.get("experience", [])
        exp_text = "\n".join(
            f"- {e.get('title')} at {e.get('company')} ({e.get('date')})"
            for e in experience[:4]
            if isinstance(e, dict)
        )

        skills_text = self.profile.get_plain_skills()
        personal = resume_data.get("personal", {})

        options_text = (
            f"\nAvailable options: {json.dumps(options)}" if options else ""
        )

        prompt = f"""You are filling out a job application for {personal.get('name')}.
Answer the following screening question concisely and professionally.

CANDIDATE PROFILE:
- Experience Level: {profile.get('experience_level')} ({profile.get('years_of_experience')} years)
- Location: {personal.get('location')}
- Skills: {skills_text[:400]}
- Recent Experience:
{exp_text}

QUESTION: {question}{options_text}

Rules:
- If options are provided, return ONLY one of the exact option strings.
- For yes/no: answer "Yes" unless clearly inappropriate.
- For numeric fields (years of experience, salary): give realistic numbers.
- For location/authorization: assume US work authorized.
- For open-ended: 1-3 concise sentences.
- Return ONLY the answer, no explanation."""

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def get_years_of_experience_for_skill(self, skill: str) -> str:
        """Return years of experience for a given skill as a string."""
        profile = self.profile.analyze()
        total_years = profile.get("years_of_experience", 2)

        resume_data = self.profile.get_resume_data()
        skills_text = self.profile.get_plain_skills().lower()

        # Core skills: full years; secondary skills: half
        if skill.lower() in skills_text:
            return str(total_years)
        return str(max(1, total_years // 2))
