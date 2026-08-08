"""
Jobright-based applier.

Opens the job detail on jobright.ai, extracts the real apply URL,
then routes to the appropriate ATS handler:
  - LinkedIn Easy Apply
  - Greenhouse (boards.greenhouse.io)
  - Lever (jobs.lever.co)
  - Workday (myworkdayjobs.com)
  - UKG/UltiPro (recruiting.ultipro.com)
  - iCIMS
  - Generic (fill name / email / phone / upload resume)
"""
from __future__ import annotations


import os
import re
import time
import random

from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PWTimeout

from auto_apply.base_applier import BaseApplier
from pipeline.job_searcher import Job
from pipeline.profile_analyzer import ProfileAnalyzer


class JobrightApplier(BaseApplier):
    def __init__(self, profile_analyzer: ProfileAnalyzer, headless: bool = False):
        super().__init__(profile_analyzer, headless)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def apply(self, job: Job, resume_pdf: str, cover_letter_pdf: str | None = None) -> bool:
        print(f"\n[Jobright] Applying to: {job.title} @ {job.company}")

        from pipeline.config import JOBRIGHT_PROFILE_DIR, JOBRIGHT_SESSION_ID, JOBRIGHT_USER_ID

        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=JOBRIGHT_PROFILE_DIR,
                headless=self.headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1440, "height": 900},
            )
            page = ctx.new_page()

            # Inject Jobright auth so the detail page loads correctly
            if JOBRIGHT_SESSION_ID:
                page.goto("https://jobright.ai", wait_until="domcontentloaded", timeout=15000)
                ctx.add_cookies([{
                    "name": "SESSION_ID", "value": JOBRIGHT_SESSION_ID,
                    "domain": "jobright.ai", "path": "/",
                    "httpOnly": True, "secure": True,
                }])
                if JOBRIGHT_USER_ID:
                    page.evaluate(f"() => localStorage.setItem('JR_userid', '{JOBRIGHT_USER_ID}')")

            try:
                apply_url = job.apply_url

                # If we don't have an apply URL yet, get it from the jobright page
                if not apply_url:
                    apply_url = self._extract_apply_url(page, job)

                if not apply_url:
                    print("[Jobright] Could not find apply URL. Skipping.")
                    self._screenshot(page, f"jobright_no_url_{job.id}")
                    ctx.close()
                    return False

                print(f"[Jobright] Apply URL: {apply_url}")

                # Open apply URL in a new page
                apply_page = ctx.new_page()
                apply_page.goto(apply_url, wait_until="domcontentloaded", timeout=30000)
                self._random_sleep(2, 3)

                ats = self._detect_ats(apply_url, apply_page)
                print(f"[Jobright] ATS detected: {ats}")

                success = False
                if ats == "linkedin":
                    success = self._apply_linkedin(apply_page, ctx, job, resume_pdf, cover_letter_pdf)
                elif ats == "greenhouse":
                    success = self._apply_greenhouse(apply_page, job, resume_pdf, cover_letter_pdf)
                elif ats == "lever":
                    success = self._apply_lever(apply_page, job, resume_pdf, cover_letter_pdf)
                elif ats == "workday":
                    success = self._apply_workday(apply_page, job, resume_pdf, cover_letter_pdf)
                elif ats == "ukg":
                    success = self._apply_ukg(apply_page, job, resume_pdf, cover_letter_pdf)
                else:
                    success = self._apply_generic(apply_page, job, resume_pdf, cover_letter_pdf)

                if success:
                    print(f"[Jobright] ✓ Applied to {job.title} @ {job.company}")
                else:
                    self._screenshot(apply_page, f"jobright_failed_{job.id}")
                    print(f"[Jobright] ✗ Application incomplete for {job.title} @ {job.company}")

                ctx.close()
                return success

            except Exception as e:
                print(f"[Jobright] Error: {e}")
                self._screenshot(page, f"jobright_error_{job.id}")
                ctx.close()
                return False

    # ------------------------------------------------------------------
    # Extract apply URL from jobright job page
    # ------------------------------------------------------------------

    def _extract_apply_url(self, page: Page, job: Job) -> str:
        """Extract the ATS apply URL from the Jobright job detail page."""
        try:
            page.goto(job.url, wait_until="domcontentloaded", timeout=20000)
            self._random_sleep(2, 3)

            # Wait for the "Original Job Post" link to appear (handles SPA side-panel load)
            try:
                orig_link = page.wait_for_selector("a:has-text('Original Job Post')", timeout=8000)
                if orig_link:
                    href = orig_link.get_attribute("href") or ""
                    if href.startswith("http") and "jobright" not in href:
                        return href
            except PWTimeout:
                pass

            # Fallback: click apply button and capture the URL it opens
            apply_selectors = [
                "button:has-text('APPLY WITH AUTOFILL')", "a:has-text('APPLY WITH AUTOFILL')",
                "button:has-text('APPLY NOW')", "a:has-text('APPLY NOW')",
                "button:has-text('Apply Now')", "a:has-text('Apply Now')",
                "button:has-text('Apply now')", "a:has-text('Apply now')",
            ]
            for sel in apply_selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        # Listen for a popup (new tab)
                        try:
                            with page.context.expect_page(timeout=5000) as popup_info:
                                btn.click()
                            popup = popup_info.value
                            popup.wait_for_load_state("domcontentloaded", timeout=10000)
                            url = popup.url
                            popup.close()
                            if url and "jobright" not in url and url.startswith("http"):
                                return url
                        except Exception:
                            # No popup — check if current page navigated
                            self._random_sleep(2, 3)
                            current = page.url
                            if "jobright" not in current and current.startswith("http"):
                                return current
                        break
                except Exception:
                    continue

            # Fallback: any external link matching known ATS domains
            links = page.query_selector_all("a[href*='http']")
            for link in links:
                href = link.get_attribute("href") or ""
                if "jobright" in href:
                    continue
                if any(ats in href for ats in [
                    "greenhouse.io", "lever.co", "workday.com", "icims.com",
                    "linkedin.com/jobs", "myworkdayjobs", "taleo", "jobvite",
                    "smartrecruiters", "bamboohr", "ultipro.com",
                ]):
                    return href

        except Exception as e:
            print(f"[Jobright] Extract apply URL error: {e}")
        return ""

    # ------------------------------------------------------------------
    # ATS detection
    # ------------------------------------------------------------------

    def _detect_ats(self, url: str, page: Page) -> str:
        url_lower = url.lower()
        current = page.url.lower()
        for u in [url_lower, current]:
            if "linkedin.com" in u:
                return "linkedin"
            if "greenhouse.io" in u or "boards.greenhouse" in u:
                return "greenhouse"
            if "lever.co" in u:
                return "lever"
            if "workday" in u or "myworkdayjobs" in u:
                return "workday"
            if "ultipro.com" in u or "ukg.com" in u or "recruiting.ultipro" in u:
                return "ukg"
            if "icims.com" in u:
                return "icims"
        return "generic"

    # ------------------------------------------------------------------
    # ATS handlers
    # ------------------------------------------------------------------

    def _apply_linkedin(
        self, page: Page, ctx: BrowserContext, job: Job,
        resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        """Reuse LinkedIn Easy Apply logic."""
        from auto_apply.linkedin_applier import LinkedInApplier
        applier = LinkedInApplier(self.profile, self.headless)
        # LinkedIn applier opens its own context — use the page we already have
        if not applier._click_easy_apply(page):
            return False
        return applier._handle_modal(page, resume_pdf, cover_letter_pdf)

    def _apply_greenhouse(
        self, page: Page, job: Job, resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        """Apply via Greenhouse ATS (boards.greenhouse.io)."""
        personal = self.profile.get_resume_data().get("personal", {})
        try:
            self._fill_field(page, "input#first_name", personal.get("name", "").split()[0])
            self._fill_field(page, "input#last_name", " ".join(personal.get("name", "").split()[1:]))
            self._fill_field(page, "input#email", personal.get("email", ""))
            self._fill_field(page, "input#phone", personal.get("phone", ""))

            # Resume upload
            resume_input = page.query_selector("input[type='file']")
            if resume_input and os.path.exists(resume_pdf):
                resume_input.set_input_files(resume_pdf)
                self._random_sleep(1, 2)

            # Cover letter
            cl_input = page.query_selector("input[data-source='cover_letter'], input[name*='cover']")
            if cl_input and cover_letter_pdf and os.path.exists(cover_letter_pdf):
                cl_input.set_input_files(cover_letter_pdf)
                self._random_sleep(1, 2)

            # Answer custom questions
            self._answer_greenhouse_questions(page)

            # Submit
            return self._wait_and_click(page, "input[type='submit'], button[type='submit']")

        except Exception as e:
            print(f"[Greenhouse] Error: {e}")
            return False

    def _answer_greenhouse_questions(self, page: Page) -> None:
        try:
            fields = page.query_selector_all("div.field")
            for field_div in fields:
                label_el = field_div.query_selector("label")
                question = label_el.inner_text().strip() if label_el else ""
                if not question:
                    continue

                input_el = field_div.query_selector("input[type='text'], textarea, select")
                if not input_el:
                    continue

                tag = input_el.evaluate("el => el.tagName.toLowerCase()")
                current = input_el.input_value() if tag != "select" else ""
                if current.strip():
                    continue

                if tag == "select":
                    options = [o.inner_text().strip() for o in input_el.query_selector_all("option")]
                    answer = self.answer_screening_question(question, options)
                    best = _best_match(answer, options)
                    if best:
                        input_el.select_option(label=best)
                else:
                    answer = self.answer_screening_question(question)
                    self._slow_type(input_el, answer)
                self._random_sleep(0.3, 0.6)
        except Exception:
            pass

    def _apply_lever(
        self, page: Page, job: Job, resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        """Apply via Lever ATS (jobs.lever.co)."""
        personal = self.profile.get_resume_data().get("personal", {})
        try:
            name_parts = personal.get("name", "").split()
            self._fill_field(page, "input[name='name']", personal.get("name", ""))
            self._fill_field(page, "input[name='email']", personal.get("email", ""))
            self._fill_field(page, "input[name='phone']", personal.get("phone", ""))
            self._fill_field(page, "input[name='urls[LinkedIn]']", personal.get("linkedin", ""))
            self._fill_field(page, "input[name='urls[Portfolio]']", personal.get("website", ""))

            # Resume upload
            resume_input = page.query_selector("input[type='file']")
            if resume_input and os.path.exists(resume_pdf):
                resume_input.set_input_files(resume_pdf)
                self._random_sleep(1, 2)

            # Custom questions
            self._answer_lever_questions(page)

            # Submit
            return self._wait_and_click(
                page, "button[type='submit'], input[type='submit'], button:has-text('Submit')"
            )
        except Exception as e:
            print(f"[Lever] Error: {e}")
            return False

    def _answer_lever_questions(self, page: Page) -> None:
        try:
            cards = page.query_selector_all("div.application-question, div[class*='question']")
            for card in cards:
                label_el = card.query_selector("label, p")
                question = label_el.inner_text().strip() if label_el else ""
                if not question:
                    continue
                input_el = card.query_selector("input[type='text'], textarea, select")
                if not input_el:
                    continue
                current = input_el.input_value() or ""
                if current.strip():
                    continue
                answer = self.answer_screening_question(question)
                self._slow_type(input_el, answer)
                self._random_sleep(0.2, 0.5)
        except Exception:
            pass

    def _apply_workday(
        self, page: Page, job: Job, resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        """Apply via Workday ATS — complex multi-step, handles common flow."""
        personal = self.profile.get_resume_data().get("personal", {})
        try:
            # Workday job pages often land on a description first — click "Apply"
            apply_link = page.query_selector("a[data-automation-id='adventureButton'], a:has-text('Apply'), button:has-text('Apply')")
            if apply_link and not page.query_selector("input[type='file']"):
                apply_link.click()
                self._random_sleep(3, 4)

            # Workday shows a modal: "Autofill with Resume", "Apply Manually", etc.
            autofill_btn = page.query_selector("a[data-automation-id='autofillWithResume']")
            if autofill_btn and autofill_btn.is_visible():
                autofill_btn.click()
                self._random_sleep(3, 4)

            # Handle Workday Create Account / Sign In page
            self._handle_workday_auth(page)

            # Workday often starts with a resume upload to auto-fill
            resume_input = page.query_selector("input[type='file']")
            if resume_input and os.path.exists(resume_pdf):
                resume_input.set_input_files(resume_pdf)
                self._random_sleep(2, 3)

            max_steps = 10
            for _ in range(max_steps):
                self._random_sleep(1, 2)

                # Fill visible text fields
                self._fill_workday_fields(page, personal)

                # Answer questions
                self._answer_workday_questions(page)

                # Check for submit
                submit = page.query_selector("button[data-automation-id='bottom-navigation-next-button']")
                if not submit:
                    submit = page.query_selector("button:has-text('Submit')")

                if submit:
                    label = submit.inner_text().lower()
                    submit.click()
                    self._random_sleep(2, 3)
                    if "submit" in label:
                        return True
                else:
                    break
            return False
        except Exception as e:
            print(f"[Workday] Error: {e}")
            return False

    def _handle_workday_auth(self, page: Page) -> None:
        """Handle Workday Create Account or Sign In page."""
        from pipeline.config import ATS_EMAIL, ATS_PASSWORD

        # Check if we're on a create account or sign in page
        create_account_heading = page.query_selector("h2:has-text('Create Account'), h1:has-text('Create Account')")
        sign_in_heading = page.query_selector("h2:has-text('Sign In'), h1:has-text('Sign In')")

        if create_account_heading and create_account_heading.is_visible():
            print("[Workday] Create Account page detected — filling credentials")
            # Fill email
            email_input = page.query_selector("input[data-automation-id='email']")
            if email_input and not (email_input.input_value() or "").strip():
                self._slow_type(email_input, ATS_EMAIL)
                self._random_sleep(0.3, 0.5)

            # Fill password
            pw_input = page.query_selector("input[data-automation-id='password']")
            if pw_input and not (pw_input.input_value() or "").strip():
                self._slow_type(pw_input, ATS_PASSWORD)
                self._random_sleep(0.3, 0.5)

            # Fill verify password
            verify_input = page.query_selector("input[data-automation-id='verifyPassword']")
            if verify_input and not (verify_input.input_value() or "").strip():
                self._slow_type(verify_input, ATS_PASSWORD)
                self._random_sleep(0.3, 0.5)

            # Check the terms checkbox
            checkbox = page.query_selector("input[data-automation-id='createAccountCheckbox']")
            if checkbox:
                try:
                    if not checkbox.is_checked():
                        checkbox.check()
                        self._random_sleep(0.2, 0.3)
                except Exception:
                    pass

            # Click Create Account button
            create_btn = page.query_selector("button[data-automation-id='createAccountSubmitButton']")
            if create_btn:
                create_btn.click()
                self._random_sleep(5, 6)

            # If account already exists, Workday may show sign-in instead
            sign_in_link = page.query_selector("button[data-automation-id='signInLink']")
            if sign_in_link and sign_in_link.is_visible():
                print("[Workday] Account may already exist — trying sign in")
                sign_in_link.click()
                self._random_sleep(2, 3)
                self._workday_sign_in(page, ATS_EMAIL, ATS_PASSWORD)

        elif sign_in_heading and sign_in_heading.is_visible():
            print("[Workday] Sign In page detected — signing in")
            self._workday_sign_in(page, ATS_EMAIL, ATS_PASSWORD)

    def _workday_sign_in(self, page: Page, email: str, password: str) -> None:
        """Fill and submit Workday sign-in form."""
        email_input = page.query_selector("input[data-automation-id='email']")
        if email_input and not (email_input.input_value() or "").strip():
            self._slow_type(email_input, email)
            self._random_sleep(0.3, 0.5)

        pw_input = page.query_selector("input[data-automation-id='password']")
        if pw_input and not (pw_input.input_value() or "").strip():
            self._slow_type(pw_input, password)
            self._random_sleep(0.3, 0.5)

        sign_in_btn = page.query_selector("button[data-automation-id='signInSubmitButton']")
        if sign_in_btn:
            sign_in_btn.click()
            self._random_sleep(5, 6)

    def _fill_workday_fields(self, page: Page, personal: dict) -> None:
        mapping = {
            "[data-automation-id='legalNameSection_firstName']": personal.get("name", "").split()[0],
            "[data-automation-id='legalNameSection_lastName']": " ".join(personal.get("name", "").split()[1:]),
            "[data-automation-id='email']": personal.get("email", ""),
            "[data-automation-id='phone-number']": personal.get("phone", ""),
        }
        for sel, val in mapping.items():
            if not val:
                continue
            try:
                el = page.query_selector(sel)
                if el and not (el.input_value() or "").strip():
                    self._slow_type(el, val)
                    self._random_sleep(0.2, 0.4)
            except Exception:
                continue

    def _answer_workday_questions(self, page: Page) -> None:
        try:
            questions = page.query_selector_all("[data-automation-id*='formField']")
            for q in questions:
                label_el = q.query_selector("label")
                question = label_el.inner_text().strip() if label_el else ""
                if not question:
                    continue
                inp = q.query_selector("input[type='text'], textarea")
                if inp and not (inp.input_value() or "").strip():
                    answer = self.answer_screening_question(question)
                    self._slow_type(inp, answer)
                    self._random_sleep(0.2, 0.4)
        except Exception:
            pass

    def _apply_ukg(
        self, page: Page, job: Job, resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        """Apply via UKG/UltiPro ATS."""
        personal = self.profile.get_resume_data().get("personal", {})
        try:
            # UKG has an "Apply" button on the opportunity detail page
            apply_btn = page.query_selector("a[id*='apply'], button[id*='apply'], a:has-text('Apply for this Job'), a:has-text('Apply Now')")
            if apply_btn:
                apply_btn.click()
                self._random_sleep(2, 3)

            # Fill basic fields
            name_parts = personal.get("name", "").split()
            first = name_parts[0] if name_parts else ""
            last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            self._fill_field(page, "input[id*='FirstName'], input[name*='FirstName']", first)
            self._fill_field(page, "input[id*='LastName'], input[name*='LastName']", last)
            self._fill_field(page, "input[type='email'], input[id*='Email'], input[name*='Email']", personal.get("email", ""))
            self._fill_field(page, "input[type='tel'], input[id*='Phone'], input[name*='Phone']", personal.get("phone", ""))

            # Resume upload
            file_input = page.query_selector("input[type='file']")
            if file_input and os.path.exists(resume_pdf):
                file_input.set_input_files(resume_pdf)
                self._random_sleep(1, 2)

            # Submit
            return self._wait_and_click(
                page, "button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Apply')"
            )
        except Exception as e:
            print(f"[UKG] Error: {e}")
            return False

    def _apply_generic(
        self, page: Page, job: Job, resume_pdf: str, cover_letter_pdf: str | None
    ) -> bool:
        """Fallback: click apply, dismiss cookie banners, fill form, submit."""
        personal = self.profile.get_resume_data().get("personal", {})
        try:
            # Dismiss cookie consent banners
            for cookie_sel in [
                "button:has-text('Accept All')", "button:has-text('Accept all')",
                "button:has-text('Accept All Cookies')", "button[id*='cookie'] button",
                "button:has-text('I Accept')", "button:has-text('Agree')",
            ]:
                try:
                    btn = page.query_selector(cookie_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        self._random_sleep(0.5, 1)
                        break
                except Exception:
                    pass

            # Click the Apply button if we're on a job description page
            for apply_sel in [
                "a:has-text('Apply for this Job')", "a:has-text('Apply Now')",
                "button:has-text('Apply for this Job')", "button:has-text('Apply Now')",
                "a[href*='apply']", "button:has-text('Apply')",
            ]:
                try:
                    btn = page.query_selector(apply_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        self._random_sleep(2, 3)
                        break
                except Exception:
                    pass

            name_parts = personal.get("name", "").split()

            field_map = {
                "input[name*='first'], input[id*='first'], input[placeholder*='First']": name_parts[0] if name_parts else "",
                "input[name*='last'], input[id*='last'], input[placeholder*='Last']": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                "input[name*='name']:not([name*='first']):not([name*='last'])": personal.get("name", ""),
                "input[type='email'], input[name*='email'], input[id*='email']": personal.get("email", ""),
                "input[type='tel'], input[name*='phone'], input[id*='phone']": personal.get("phone", ""),
                "input[name*='linkedin'], input[placeholder*='LinkedIn']": personal.get("linkedin", ""),
                "input[name*='website'], input[placeholder*='website'], input[placeholder*='portfolio']": personal.get("website", ""),
            }
            for sel, val in field_map.items():
                if not val:
                    continue
                try:
                    el = page.query_selector(sel)
                    if el and not (el.input_value() or "").strip():
                        self._slow_type(el, val)
                        self._random_sleep(0.2, 0.4)
                except Exception:
                    continue

            # Upload resume
            file_input = page.query_selector("input[type='file']")
            if file_input and os.path.exists(resume_pdf):
                file_input.set_input_files(resume_pdf)
                self._random_sleep(1, 2)

            # Submit
            submitted = self._wait_and_click(
                page,
                "button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Apply')"
            )
            return submitted

        except Exception as e:
            print(f"[Generic] Error: {e}")
            return False


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _best_match(answer: str, options: list[str]) -> str | None:
    a = answer.lower().strip()
    for opt in options:
        if opt.lower().strip() == a:
            return opt
    for opt in options:
        if a in opt.lower() or opt.lower() in a:
            return opt
    return options[0] if options else None
