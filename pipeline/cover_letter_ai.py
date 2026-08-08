"""
Uses Claude to generate a tailored cover letter body for a job,
then compiles it to PDF using the existing CoverLetterGenerator.
"""

import os
import re
import yaml
import anthropic

from pipeline.job_searcher import Job
from pipeline.profile_analyzer import ProfileAnalyzer


class CoverLetterAI:
    def __init__(self, profile_analyzer: ProfileAnalyzer, coverletter_yml_path: str):
        self.profile = profile_analyzer
        self.cl_template_path = coverletter_yml_path
        self.client = anthropic.Anthropic()

        with open(coverletter_yml_path, "r", encoding="utf-8") as f:
            self.cl_template: dict = yaml.safe_load(f)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, job: Job, output_dir: str) -> str:
        """Generate tailored cover letter PDF. Returns path to PDF."""
        cl_data = self._build_cl_data(job)
        return self._generate_pdf(cl_data, job, output_dir)

    def generate_to_dict(self, job: Job) -> dict:
        """Return cover letter data dict without writing to disk."""
        return self._build_cl_data(job)

    # ------------------------------------------------------------------
    # Build cover letter data
    # ------------------------------------------------------------------

    def _build_cl_data(self, job: Job) -> dict:
        import copy
        data = copy.deepcopy(self.cl_template)

        # Generate body via Claude
        body = self._generate_body(job)

        # Update letter fields
        from datetime import datetime
        data["letter"]["date"] = datetime.now().strftime("%B %d, %Y")
        data["letter"]["body"] = body
        data["letter"]["opening"] = f"Dear Hiring Committee:"

        # Update recipient
        data["recipient"]["company"] = job.company
        data["recipient"]["title"] = job.title
        data["recipient"]["name"] = "Hiring Committee"
        data["recipient"]["address"] = job.location

        return data

    def _generate_body(self, job: Job) -> str:
        profile = self.profile.analyze()
        resume_data = self.profile.get_resume_data()
        personal = resume_data.get("personal", {})

        # Summarize top experience for context
        experience = resume_data.get("experience", [])
        exp_summary = ""
        for exp in experience[:3]:
            if isinstance(exp, dict):
                achievements = exp.get("achievements", [])
                bullets = " ".join(str(a) for a in achievements[:2])
                exp_summary += f"- {exp.get('title')} at {exp.get('company')}: {bullets}\n"

        prompt = f"""Write a professional cover letter body for this job application.

CANDIDATE:
- Name: {personal.get('name')}
- Email: {personal.get('email')}
- Phone: {personal.get('phone')}
- Location: {personal.get('location')}
- Website: {personal.get('website')}
- LinkedIn: {personal.get('linkedin')}

CANDIDATE PROFILE:
{profile.get('summary', '')}

TOP EXPERIENCE HIGHLIGHTS:
{exp_summary}

JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description[:2500] if job.description else 'Not provided'}

INSTRUCTIONS:
Write exactly 3 paragraphs separated by blank lines:

1. Opening paragraph: Catchy, memorable opening. State the position and company.
   Immediately lead with your strongest hook (an award, metric, or unique achievement).
   Make the reader want to keep reading.

2. Body paragraph: Connect 2-3 specific experiences/projects to the job's key requirements.
   Use real metrics and technology names from the resume. Be specific, not generic.

3. Closing paragraph: Express enthusiasm for the company's mission (reference something
   specific about the company if possible). Request an interview. Include phone and email.

RULES:
- No dashes (-) or em-dashes (—) in sentences. Use commas, periods, or rewrite.
- Keep each paragraph to 3-4 sentences.
- Professional but personable tone.
- Return ONLY the body text (3 paragraphs). No salutation, no signature."""

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    # ------------------------------------------------------------------
    # PDF generation
    # ------------------------------------------------------------------

    def _generate_pdf(self, cl_data: dict, job: Job, output_dir: str) -> str:
        from coverletter.generator import CoverLetterGenerator
        import tempfile

        os.makedirs(output_dir, exist_ok=True)

        # Write modified CL YAML to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as tmp:
            yaml.dump(cl_data, tmp, default_flow_style=False, allow_unicode=True)
            tmp_path = tmp.name

        try:
            name = cl_data.get("personal_information", {}).get("name", "Name")
            name_slug = name.replace(" ", "_")
            company_slug = re.sub(r"[^A-Za-z0-9]+", "", job.company)
            role_slug = re.sub(r"[^A-Za-z0-9]+", "", job.title)
            filename = f"{name_slug}_CoverLetter_{company_slug}_{role_slug}.pdf"
            output_path = os.path.join(output_dir, filename)

            generator = CoverLetterGenerator(tmp_path)
            pdf_path = generator.generate_pdf(output_path, output_dir, job.company)
            print(f"[CoverLetterAI] Cover letter PDF: {pdf_path}")
            return pdf_path
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
