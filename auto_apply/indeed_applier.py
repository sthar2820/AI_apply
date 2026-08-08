"""
Indeed Quick Apply automation.

Works through Indeed's Instant Apply / Quick Apply flow.
Requires being logged in (uses persistent browser profile).
"""
from __future__ import annotations


import os
import random
import time

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from auto_apply.base_applier import BaseApplier
from pipeline.job_searcher import Job
from pipeline.profile_analyzer import ProfileAnalyzer


INDEED_USER_DATA_DIR = os.environ.get(
    "INDEED_USER_DATA_DIR",
    os.path.expanduser("~/.config/indeed-profile"),
)


class IndeedApplier(BaseApplier):
    def __init__(self, profile_analyzer: ProfileAnalyzer, headless: bool = False):
        super().__init__(profile_analyzer, headless)

    def apply(self, job: Job, resume_pdf: str, cover_letter_pdf: str | None = None) -> bool:
        print(f"\n[Indeed] Applying to: {job.title} @ {job.company}")

        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=INDEED_USER_DATA_DIR,
                headless=self.headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1440, "height": 900},
            )
            page = ctx.new_page()

            try:
                page.goto(job.url, wait_until="domcontentloaded", timeout=20000)
                self._random_sleep(2, 3)

                # Click "Apply now" / "Easily apply"
                if not self._click_apply_button(page):
                    print("[Indeed] No apply button found.")
                    ctx.close()
                    return False

                # Indeed may open a new tab for the application
                pages = ctx.pages
                app_page = pages[-1] if len(pages) > 1 else page

                success = self._handle_application(app_page, resume_pdf, cover_letter_pdf)

                if success:
                    print(f"[Indeed] Successfully applied to {job.title} @ {job.company}")
                else:
                    self._screenshot(app_page, f"indeed_failed_{job.id}")

                ctx.close()
                return success

            except Exception as e:
                print(f"[Indeed] Error: {e}")
                self._screenshot(page, f"indeed_error_{job.id}")
                ctx.close()
                return False

    def _click_apply_button(self, page: Page) -> bool:
        selectors = [
            "button#indeedApplyButton",
            "button[aria-label*='Apply']",
            "a.indeed-apply-button",
            "button:has-text('Apply now')",
            "button:has-text('Easily apply')",
        ]
        for sel in selectors:
            try:
                btn = page.wait_for_selector(sel, timeout=5000)
                if btn and btn.is_visible():
                    btn.click()
                    self._random_sleep(2, 3)
                    return True
            except PWTimeout:
                continue
        return False

    def _handle_application(
        self, page: Page, resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        max_steps = 12
        for step in range(max_steps):
            self._random_sleep(1, 2)

            # Upload resume if prompted
            try:
                file_input = page.query_selector("input[type='file']")
                if file_input and os.path.exists(resume_pdf):
                    file_input.set_input_files(resume_pdf)
                    self._random_sleep(1, 2)
            except Exception:
                pass

            # Fill text fields
            self._fill_contact_fields(page)
            self._answer_screening_questions(page)

            # Check for submit
            submitted = self._try_submit(page)
            if submitted:
                return True

            # Try next
            if not self._click_continue(page):
                break

        return False

    def _fill_contact_fields(self, page: Page) -> None:
        personal = self.profile.get_resume_data().get("personal", {})
        fields = {
            "input[name*='name'], input[id*='name']": personal.get("name", ""),
            "input[name*='email'], input[id*='email']": personal.get("email", ""),
            "input[name*='phone'], input[id*='phone']": personal.get("phone", ""),
        }
        for sel, value in fields.items():
            if not value:
                continue
            try:
                el = page.query_selector(sel)
                if el:
                    current = el.input_value() or ""
                    if not current.strip():
                        self._slow_type(el, value)
                        self._random_sleep(0.2, 0.4)
            except Exception:
                continue

    def _answer_screening_questions(self, page: Page) -> None:
        try:
            questions = page.query_selector_all("div.ia-Questions-item, div[class*='question']")
            for q_div in questions:
                label_el = q_div.query_selector("label, legend, h3, p")
                question_text = label_el.inner_text().strip() if label_el else ""
                if not question_text:
                    continue

                # Radio / checkbox
                radios = q_div.query_selector_all("input[type='radio']")
                if radios:
                    options = []
                    for r in radios:
                        lbl = q_div.query_selector(f"label[for='{r.get_attribute('id')}']")
                        if lbl:
                            options.append(lbl.inner_text().strip())
                    if options:
                        answer = self.answer_screening_question(question_text, options)
                        best = _best_match(answer, options)
                        if best:
                            for r in radios:
                                lbl = q_div.query_selector(f"label[for='{r.get_attribute('id')}']")
                                if lbl and lbl.inner_text().strip() == best:
                                    r.click()
                                    break
                    continue

                # Text / number input
                input_el = q_div.query_selector("input[type='text'], input[type='number'], textarea")
                if input_el:
                    current = input_el.input_value() or ""
                    if not current.strip():
                        answer = self.answer_screening_question(question_text)
                        self._slow_type(input_el, answer)
                        self._random_sleep(0.2, 0.4)

                # Select
                select_el = q_div.query_selector("select")
                if select_el:
                    opts = select_el.query_selector_all("option")
                    option_texts = [o.inner_text().strip() for o in opts if o.inner_text().strip()]
                    answer = self.answer_screening_question(question_text, option_texts)
                    best = _best_match(answer, option_texts)
                    if best:
                        select_el.select_option(label=best)

        except Exception as e:
            print(f"[Indeed] Question answering error: {e}")

    def _click_continue(self, page: Page) -> bool:
        for sel in [
            "button:has-text('Continue')",
            "button:has-text('Next')",
            "button[type='submit']:not(:has-text('Submit'))",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.click()
                    self._random_sleep(1.5, 2.5)
                    return True
            except Exception:
                continue
        return False

    def _try_submit(self, page: Page) -> bool:
        for sel in [
            "button:has-text('Submit your application')",
            "button:has-text('Submit application')",
            "button[type='submit']:has-text('Submit')",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.click()
                    self._random_sleep(2, 3)
                    return True
            except Exception:
                continue
        return False


def _best_match(answer: str, options: list[str]) -> str | None:
    answer_lower = answer.lower().strip()
    for opt in options:
        if opt.lower().strip() == answer_lower:
            return opt
    for opt in options:
        if answer_lower in opt.lower() or opt.lower() in answer_lower:
            return opt
    return options[0] if options else None
