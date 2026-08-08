"""
Uses Claude to tailor the resume YAML for a specific job,
then compiles it to PDF using the existing ResumeGenerator.
"""

import copy
import json
import os
import re
import tempfile
import yaml
import anthropic

from pipeline.job_searcher import Job
from pipeline.profile_analyzer import ProfileAnalyzer


class ResumeTailor:
    def __init__(self, profile_analyzer: ProfileAnalyzer):
        self.profile = profile_analyzer
        self.client = anthropic.Anthropic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tailor(self, job: Job, output_dir: str) -> str:
        """Tailor resume for a job and return path to generated PDF."""
        base_data = self.profile.get_resume_data()
        tailored_data = self._tailor_with_claude(job, base_data)
        return self._generate_pdf(tailored_data, job, output_dir)

    def tailor_to_dict(self, job: Job) -> dict:
        """Return tailored resume as a YAML-compatible dict (no PDF)."""
        return self._tailor_with_claude(job, self.profile.get_resume_data())

    # ------------------------------------------------------------------
    # Claude tailoring
    # ------------------------------------------------------------------

    def _tailor_with_claude(self, job: Job, base_data: dict) -> dict:
        resume_yaml = yaml.dump(base_data, default_flow_style=False, allow_unicode=True)

        prompt = f"""You are an expert resume editor. Tailor this resume YAML for the job below.

JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description[:3000] if job.description else 'Not provided'}

CURRENT RESUME YAML:
{resume_yaml[:6000]}

INSTRUCTIONS:
1. Rewrite the "summary" (2 sentences max) to directly address this role and company.
2. For experience entries, rewrite bullet points to front-load keywords from the job description,
   emphasize relevant technologies and impact metrics, and use strong action verbs.
   - For the FIRST (most recent) experience entry: keep ALL bullet points unchanged in count.
   - For all other experience entries: select and keep the 2 most relevant bullet points only.
   CRITICAL: Do NOT invent new roles, companies, dates, or metrics not in the original.
3. Reorder skills categories so the most relevant ones appear first.
4. Select the 2 most relevant projects only (keep their original names but tweak
   the description to emphasize overlap with the job).
5. Keep all personal info, education, certifications, leadership, awards UNCHANGED.
6. Return ONLY valid YAML. No markdown fences, no commentary.
7. Preserve all LaTeX commands (e.g., \\textbf{{}}, \\%) exactly as-is.
8. CRITICAL: The final resume MUST fit on exactly ONE page. Be concise."""

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:yaml)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        try:
            tailored = yaml.safe_load(raw)
            if not isinstance(tailored, dict):
                raise ValueError("Claude returned non-dict YAML")
            # Safety: always preserve personal info from original
            tailored["personal"] = base_data.get("personal", tailored.get("personal", {}))
            tailored["education"] = base_data.get("education", tailored.get("education", []))
            return tailored
        except Exception as e:
            print(f"[ResumeTailor] YAML parse error, falling back to base resume: {e}")
            return copy.deepcopy(base_data)

    # ------------------------------------------------------------------
    # PDF generation
    # ------------------------------------------------------------------

    def _generate_pdf(self, resume_data: dict, job: Job, output_dir: str) -> str:
        """Write tailored YAML to a temp file and compile via ResumeGenerator."""
        # Lazy import to avoid circular deps
        from resume.generator import ResumeGenerator

        os.makedirs(output_dir, exist_ok=True)

        # Write tailored YAML to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as tmp:
            yaml.dump(resume_data, tmp, default_flow_style=False, allow_unicode=True)
            tmp_path = tmp.name

        try:
            # Filename convention: Name_Resume_CompanyRole.pdf
            name = resume_data.get("personal", {}).get("name", "Resume")
            name_slug = name.replace(" ", "_")
            company_slug = re.sub(r"[^A-Za-z0-9]+", "", job.company)
            role_slug = re.sub(r"[^A-Za-z0-9]+", "", job.title)
            filename = f"{name_slug}_Resume_{company_slug}_{role_slug}.pdf"
            output_path = os.path.join(output_dir, filename)

            generator = ResumeGenerator(tmp_path)
            pdf_path = generator.generate_pdf(output_path, output_dir)
            print(f"[ResumeTailor] Resume PDF: {pdf_path}")
            return pdf_path
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
