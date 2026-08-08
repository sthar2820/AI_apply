"""
Analyzes resume.yml and about YAML to extract a structured profile
used throughout the pipeline for job matching and tailoring.
"""
from __future__ import annotations

import json
import os
import yaml
import anthropic


class ProfileAnalyzer:
    def __init__(self, resume_yml_path: str, about_yml_path: str | None = None):
        self.resume_path = resume_yml_path
        self.about_path = about_yml_path
        self.client = anthropic.Anthropic()
        self._profile: dict | None = None

        with open(resume_yml_path, "r", encoding="utf-8") as f:
            self.resume_data: dict = yaml.safe_load(f)

        self.about_data: dict = {}
        if about_yml_path and os.path.exists(about_yml_path):
            with open(about_yml_path, "r", encoding="utf-8") as f:
                self.about_data = yaml.safe_load(f) or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> dict:
        """Extract a structured profile from the resume using Claude.

        Returns a dict with keys:
          name, email, phone, linkedin, website, location,
          experience_level, years_of_experience,
          target_roles, core_skills, domains,
          preferred_locations, summary
        """
        if self._profile:
            return self._profile

        resume_text = yaml.dump(self.resume_data, default_flow_style=False)
        prompt = f"""Analyze this resume YAML and return ONLY a JSON object (no markdown fences).

RESUME:
{resume_text}

Return exactly this JSON structure:
{{
  "name": "...",
  "email": "...",
  "phone": "...",
  "linkedin": "...",
  "website": "...",
  "location": "...",
  "experience_level": "entry|mid|senior",
  "years_of_experience": 3,
  "target_roles": ["Software Engineer", "Full Stack Developer", "ML Engineer"],
  "core_skills": ["Python", "React", "TypeScript", "LangChain"],
  "domains": ["fullstack", "machine learning", "data engineering"],
  "preferred_locations": ["Remote", "New York"],
  "summary": "Two-sentence professional summary."
}}"""

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text.strip()
        # Strip any accidental markdown fences
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.split("```")[0].strip()

        self._profile = json.loads(content)
        return self._profile

    def get_resume_data(self) -> dict:
        return self.resume_data

    def get_about_data(self) -> dict:
        return self.about_data

    def get_plain_skills(self) -> str:
        """Return all skills as a flat comma-separated string."""
        skills = self.resume_data.get("skills", [])
        all_skills: list[str] = []
        for cat in skills:
            if isinstance(cat, dict):
                items = cat.get("items", "")
                all_skills.extend(s.strip() for s in items.split(",") if s.strip())
        return ", ".join(all_skills)

    def get_search_queries(self) -> list[str]:
        """Return job search queries derived from target roles."""
        profile = self.analyze()
        return profile.get("target_roles", [])[:5]
