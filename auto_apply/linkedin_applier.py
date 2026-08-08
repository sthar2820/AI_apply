"""
LinkedIn Easy Apply automation.

Navigates to a LinkedIn job posting, clicks "Easy Apply", and works
through all form steps: contact info → resume upload → cover letter →
screening questions → review → submit.

Requires the user to be logged in to LinkedIn in a persistent browser
profile (set LINKEDIN_USER_DATA_DIR in your environment or pass it in).
"""
from __future__ import annotations


import os
import random
import time

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from auto_apply.base_applier import BaseApplier
from pipeline.job_searcher import Job
from pipeline.profile_analyzer import ProfileAnalyzer


LINKEDIN_USER_DATA_DIR = os.environ.get(
    "LINKEDIN_USER_DATA_DIR",
    os.path.expanduser("~/.config/linkedin-profile"),
)


class LinkedInApplier(BaseApplier):
    def __init__(self, profile_analyzer: ProfileAnalyzer, headless: bool = False):
        super().__init__(profile_analyzer, headless)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def apply(self, job: Job, resume_pdf: str, cover_letter_pdf: str | None = None) -> bool:
        """Apply to a LinkedIn job via Easy Apply. Returns True on success."""
        print(f"\n[LinkedIn] Applying to: {job.title} @ {job.company}")
        print(f"[LinkedIn] URL: {job.url}")

        with sync_playwright() as pw:
            # Use persistent context so LinkedIn session is preserved
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=LINKEDIN_USER_DATA_DIR,
                headless=self.headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1440, "height": 900},
            )
            page = ctx.new_page()

            try:
                page.goto(job.url, wait_until="domcontentloaded", timeout=20000)
                self._random_sleep(2, 3)

                # Check if we need to log in
                if self._needs_login(page):
                    print("[LinkedIn] Not logged in. Please log in manually and rerun.")
                    self._screenshot(page, "linkedin_login_required")
                    ctx.close()
                    return False

                # Click Easy Apply button
                if not self._click_easy_apply(page):
                    print("[LinkedIn] No Easy Apply button found. Skipping.")
                    ctx.close()
                    return False

                # Work through modal steps
                success = self._handle_modal(page, resume_pdf, cover_letter_pdf)

                if success:
                    print(f"[LinkedIn] Successfully applied to {job.title} @ {job.company}")
                else:
                    print(f"[LinkedIn] Application incomplete for {job.title} @ {job.company}")
                    self._screenshot(page, f"linkedin_failed_{job.id}")

                ctx.close()
                return success

            except Exception as e:
                print(f"[LinkedIn] Error: {e}")
                self._screenshot(page, f"linkedin_error_{job.id}")
                ctx.close()
                return False

    # ------------------------------------------------------------------
    # Login check
    # ------------------------------------------------------------------

    def _needs_login(self, page: Page) -> bool:
        return bool(
            page.query_selector("a[href*='/login']") or
            page.query_selector("input[name='session_key']")
        )

    # ------------------------------------------------------------------
    # Click Easy Apply
    # ------------------------------------------------------------------

    def _click_easy_apply(self, page: Page) -> bool:
        # Wait for page to fully render before looking for the button
        self._random_sleep(2, 3)
        selectors = [
            "button.jobs-apply-button",
            "button[aria-label*='Easy Apply']",
            "button.artdeco-button--primary:has-text('Easy Apply')",
            "button:has-text('Easy Apply')",
            ".jobs-apply-button--top-card",
        ]
        for sel in selectors:
            try:
                btn = page.wait_for_selector(sel, timeout=8000)
                if btn and btn.is_visible():
                    btn.scroll_into_view_if_needed()
                    self._random_sleep(0.5, 1)
                    btn.click()
                    self._random_sleep(2, 3)
                    # Confirm modal opened
                    modal = page.query_selector("[role='dialog'], .jobs-easy-apply-modal")
                    return modal is not None
            except PWTimeout:
                continue
        return False

    # ------------------------------------------------------------------
    # Handle the Easy Apply modal
    # ------------------------------------------------------------------

    def _handle_modal(
        self, page: Page, resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        max_steps = 15
        step = 0

        while step < max_steps:
            step += 1
            self._random_sleep(1, 2)

            # Check if we hit the "Review" / final step
            if self._is_review_step(page):
                return self._submit_application(page)

            # Fill current step
            self._fill_current_step(page, resume_pdf, cover_letter_pdf)

            # Click Next / Continue
            if not self._click_next(page):
                # Maybe we're already done or stuck
                if self._is_review_step(page):
                    return self._submit_application(page)
                print(f"[LinkedIn] Could not advance at step {step}")
                return False

        print("[LinkedIn] Max steps reached without submitting.")
        return False

    # ------------------------------------------------------------------
    # Step filling
    # ------------------------------------------------------------------

    def _fill_current_step(
        self, page: Page, resume_pdf: str, cover_letter_pdf: str | None
    ) -> None:
        # Resume upload
        self._handle_resume_upload(page, resume_pdf)

        # Cover letter upload or textarea
        if cover_letter_pdf:
            self._handle_cover_letter_upload(page, cover_letter_pdf)
        self._handle_cover_letter_textarea(page)

        # Contact info / basic fields
        self._fill_contact_fields(page)

        # Screening questions (text, number, radio, select)
        self._answer_screening_questions(page)

    def _handle_resume_upload(self, page: Page, resume_pdf: str) -> None:
        try:
            upload_input = page.query_selector("input[type='file'][accept*='pdf'], input[type='file']")
            if upload_input and os.path.exists(resume_pdf):
                upload_input.set_input_files(resume_pdf)
                self._random_sleep(1, 2)
                print("[LinkedIn] Resume uploaded.")
        except Exception as e:
            print(f"[LinkedIn] Resume upload error: {e}")

    def _handle_cover_letter_upload(self, page: Page, cover_letter_pdf: str) -> None:
        try:
            # LinkedIn sometimes has a separate cover letter upload
            cl_btn = page.query_selector("button:has-text('Upload cover letter')")
            if cl_btn and os.path.exists(cover_letter_pdf):
                cl_btn.click()
                self._random_sleep(0.5, 1)
                upload_input = page.query_selector("input[type='file']")
                if upload_input:
                    upload_input.set_input_files(cover_letter_pdf)
                    self._random_sleep(1, 2)
                    print("[LinkedIn] Cover letter uploaded.")
        except Exception:
            pass

    def _handle_cover_letter_textarea(self, page: Page) -> None:
        try:
            textarea = page.query_selector("textarea[name*='coverLetter'], textarea[id*='cover-letter']")
            if textarea:
                profile = self.profile.analyze()
                text = (
                    f"Please find my tailored cover letter attached. "
                    f"I am excited about the opportunity to bring my {profile.get('experience_level')} "
                    f"background in {', '.join(profile.get('domains', [])[:2])} to your team."
                )
                self._slow_type(textarea, text)
        except Exception:
            pass

    def _fill_contact_fields(self, page: Page) -> None:
        personal = self.profile.get_resume_data().get("personal", {})
        profile = self.profile.analyze()

        field_map = {
            "input[id*='phone']": personal.get("phone", ""),
            "input[id*='email']": personal.get("email", ""),
            "input[id*='firstName']": personal.get("name", "").split()[0] if personal.get("name") else "",
            "input[id*='lastName']": " ".join(personal.get("name", "").split()[1:]) if personal.get("name") else "",
            "input[id*='city'], input[id*='location']": personal.get("location", ""),
            "input[id*='linkedin'], input[placeholder*='LinkedIn']": personal.get("linkedin", ""),
            "input[id*='website'], input[placeholder*='website'], input[placeholder*='portfolio']": personal.get("website", ""),
        }

        for selector, value in field_map.items():
            if not value:
                continue
            try:
                el = page.query_selector(selector)
                if el:
                    current = el.input_value() or ""
                    if not current.strip():
                        self._slow_type(el, value)
                        self._random_sleep(0.2, 0.5)
            except Exception:
                continue

    def _answer_screening_questions(self, page: Page) -> None:
        """Find and answer all screening question inputs on the current step."""
        # Text / number inputs with labels
        try:
            labels = page.query_selector_all("label")
            for label in labels:
                question_text = label.inner_text().strip()
                if not question_text or len(question_text) < 5:
                    continue

                label_for = label.get_attribute("for")
                if not label_for:
                    continue

                input_el = page.query_selector(f"#{label_for}")
                if not input_el:
                    continue

                tag = input_el.evaluate("el => el.tagName.toLowerCase()")
                input_type = input_el.get_attribute("type") or "text"

                if tag == "input" and input_type in ("text", "number", "tel"):
                    current = input_el.input_value() or ""
                    if current.strip():
                        continue  # Already filled
                    answer = self.answer_screening_question(question_text)
                    self._slow_type(input_el, answer)
                    self._random_sleep(0.3, 0.6)

                elif tag == "select":
                    # Get options
                    options = input_el.query_selector_all("option")
                    option_texts = [o.inner_text().strip() for o in options if o.inner_text().strip()]
                    if not option_texts:
                        continue
                    answer = self.answer_screening_question(question_text, option_texts)
                    # Find best matching option
                    best = _best_match(answer, option_texts)
                    if best:
                        input_el.select_option(label=best)
                        self._random_sleep(0.2, 0.4)

        except Exception as e:
            print(f"[LinkedIn] Question answering error: {e}")

        # Radio buttons
        try:
            fieldsets = page.query_selector_all("fieldset")
            for fieldset in fieldsets:
                legend = fieldset.query_selector("legend")
                question_text = legend.inner_text().strip() if legend else ""
                if not question_text:
                    continue

                radio_labels = fieldset.query_selector_all("label")
                options = [r.inner_text().strip() for r in radio_labels if r.inner_text().strip()]
                if not options:
                    continue

                answer = self.answer_screening_question(question_text, options)
                best = _best_match(answer, options)
                if best:
                    for rl in radio_labels:
                        if rl.inner_text().strip() == best:
                            rl.click()
                            self._random_sleep(0.2, 0.4)
                            break
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _click_next(self, page: Page) -> bool:
        next_selectors = [
            "button[aria-label='Continue to next step']",
            "button[aria-label='Review your application']",
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Review')",
        ]
        for sel in next_selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.scroll_into_view_if_needed()
                    self._random_sleep(0.5, 1)
                    btn.click()
                    self._random_sleep(1.5, 2.5)
                    return True
            except Exception:
                continue
        return False

    def _is_review_step(self, page: Page) -> bool:
        submit_selectors = [
            "button[aria-label='Submit application']",
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
        ]
        for sel in submit_selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    return True
            except Exception:
                continue
        return False

    def _submit_application(self, page: Page) -> bool:
        submit_selectors = [
            "button[aria-label='Submit application']",
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
        ]
        for sel in submit_selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.scroll_into_view_if_needed()
                    self._random_sleep(0.5, 1)
                    btn.click()
                    self._random_sleep(2, 3)
                    # Check for success modal
                    success = page.query_selector(
                        "div[data-test-modal*='success'], h3:has-text('Application submitted')"
                    )
                    if success:
                        return True
                    # LinkedIn closes the modal and shows the job page with "Application submitted"
                    try:
                        page.wait_for_selector(
                            "span:has-text('Application submitted'), "
                            ".artdeco-inline-feedback:has-text('Application submitted'), "
                            "div:has-text('Application submitted')",
                            timeout=4000,
                        )
                        return True
                    except PWTimeout:
                        pass
                    # Also check if the Easy Apply button changed to "Applied"
                    applied = page.query_selector(
                        "button[aria-label*='Applied'], span:has-text('Applied')"
                    )
                    return applied is not None
            except Exception:
                continue
        return False


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def _best_match(answer: str, options: list[str]) -> str | None:
    """Return the option that best matches the answer (case-insensitive)."""
    answer_lower = answer.lower().strip()
    # Exact match
    for opt in options:
        if opt.lower().strip() == answer_lower:
            return opt
    # Partial match
    for opt in options:
        if answer_lower in opt.lower() or opt.lower() in answer_lower:
            return opt
    # Default to first non-empty option for yes/no style
    if options:
        return options[0]
    return None
