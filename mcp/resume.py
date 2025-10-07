from mcp.server.fastmcp import FastMCP as App
import yaml
from functools import lru_cache
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

app = App()
resume_path = "/Users/dineshchhantyal/Documents/ResumeCoverLetterGenerator/mcp/about_dinesh_chhantyal.yml"
xml_knowledge_path = "/Users/dineshchhantyal/Documents/ResumeCoverLetterGenerator/mcp/knowledge_source.xml"


@lru_cache(maxsize=1)
def load_resume_data():
    with open(resume_path, "r") as file:
        return yaml.safe_load(file)


def get_section_from_resume(section: str) -> str:
    data = load_resume_data()
    if section.lower() == "all":
        return yaml.dump(data, default_flow_style=False)
    keys = section.split(".")
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return ""
    return yaml.dump(data, default_flow_style=False) if data else ""


# ------------------ Helper formatters ------------------


def _get_dict(path: str) -> Optional[Dict[str, Any]]:
    """Return a nested dict for a given dot-path from YAML, or None."""
    data: Any = load_resume_data()
    for key in path.split("."):
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data if isinstance(data, dict) else None


def _about_me_brief_text() -> str:
    personal = _get_dict("resume.personal") or {}
    summary = get_section_from_resume("resume.summary").strip()
    name = personal.get("name", "")
    location = personal.get("location", "")
    email = personal.get("email", "")
    website = personal.get("website", "")
    linkedin = personal.get("linkedin", "")
    github = personal.get("github", "")
    lines = []
    if name:
        lines.append(f"Name: {name}")
    if location:
        lines.append(f"Location: {location}")
    if summary:
        lines.append(f"Summary: {summary}")
    contact_bits = [b for b in [email, website, linkedin, github] if b]
    if contact_bits:
        lines.append("Contact: " + " | ".join(contact_bits))
    return "\n".join(lines) if lines else "No personal information found."


def _about_me_detailed_text() -> str:
    personal = _get_dict("resume.personal") or {}
    education = _get_dict("resume.education")
    top_experience = get_section_from_resume("resume.experience.job").strip()
    skills = get_section_from_resume("resume.skills").strip()
    projects = get_section_from_resume("resume.projects").strip()
    lines = []
    if personal.get("name"):
        lines.append(f"Name: {personal['name']}")
    if personal.get("location"):
        lines.append(f"Location: {personal['location']}")
    summary = get_section_from_resume("resume.summary").strip()
    if summary:
        lines.append(f"Summary: {summary}")
    if education:
        edu_name = (
            education.get("institution", {}).get("name", "")
            if isinstance(education, dict)
            else ""
        )
        edu_degree = (
            education.get("institution", {}).get("degree", "")
            if isinstance(education, dict)
            else ""
        )
        edu_gpa = (
            education.get("institution", {}).get("gpa", "")
            if isinstance(education, dict)
            else ""
        )
        edu_date = (
            education.get("institution", {}).get("date", "")
            if isinstance(education, dict)
            else ""
        )
        edu_line = ", ".join(
            [
                p
                for p in [
                    edu_name,
                    edu_degree,
                    f"GPA {edu_gpa}" if edu_gpa else "",
                    edu_date,
                ]
                if p
            ]
        )
        if edu_line:
            lines.append(f"Education: {edu_line}")
    if top_experience:
        lines.append("Experience (highlights):\n" + top_experience)
    if skills:
        lines.append("Skills:\n" + skills)
    if projects:
        lines.append("Projects (selected):\n" + projects)
    return "\n\n".join(lines) if lines else "No details found."


def _xml_root() -> Optional[ET.Element]:
    try:
        tree = ET.parse(xml_knowledge_path)
        return tree.getroot()
    except Exception:
        return None


# ------------------ Basic Tools ------------------


@app.tool(
    name="get_personal_section",
    description="Get the personal/contact section from the YAML knowledge source.",
)
def get_personal_section():
    content = get_section_from_resume("resume.personal")
    return (
        f"Personal Section:\n{content}"
        if content
        else "No content found for personal section."
    )


@app.tool(
    name="get_experience_section",
    description="Retrieve the 'experience' section from the resume YAML file. This section includes detailed information about the user's professional work experience, including roles, companies, dates, and achievements.",
)
def get_experience_section():
    content = get_section_from_resume("resume.experience")
    return (
        f"Experience Section:\n{content}"
        if content
        else "No content found for experience section."
    )


@app.tool(
    name="get_projects_section",
    description="Retrieve the 'projects' section from the resume YAML file. This section highlights the user's key projects, including descriptions, accomplishments, and technologies used.",
)
def get_projects_section():
    content = get_section_from_resume("resume.projects")
    return (
        f"Projects Section:\n{content}"
        if content
        else "No content found for projects section."
    )


@app.tool(
    name="get_skills_section",
    description="Get the skills section from the resume YAML file.",
)
def get_skills_section():
    content = get_section_from_resume("resume.skills")
    return (
        f"Skills Section:\n{content}"
        if content
        else "No content found for skills section."
    )


@app.tool(
    name="get_summary_section",
    description="Get the summary section from the resume YAML file.",
)
def get_summary_section():
    content = get_section_from_resume("resume.summary")
    return (
        f"Summary Section:\n{content}"
        if content
        else "No content found for summary section."
    )


@app.tool(
    name="get_involvements_section",
    description="Get the involvements section from the resume YAML file.",
)
def get_involvements_section():
    content = get_section_from_resume("resume.involvements")
    return (
        f"Involvements Section:\n{content}"
        if content
        else "No content found for involvements section."
    )


@app.tool(
    name="get_awards_section",
    description="Get the awards section from the resume YAML file.",
)
def get_awards_section():
    content = get_section_from_resume("resume.awards")
    return (
        f"Awards Section:\n{content}"
        if content
        else "No content found for awards section."
    )


@app.tool(
    name="get_certifications_section",
    description="Get all the certifications from the resume YAML file.",
)
def get_certifications_section():
    content = get_section_from_resume("resume.certifications")
    return (
        f"Certifications Section:\n{content}"
        if content
        else "No content found for certifications section."
    )


# ------------------ Additional Sections ------------------


@app.tool(
    name="get_open_source_contributions_section",
    description="Get the open source contributions section from the resume YAML file.",
)
def get_open_source_contributions_section():
    content = get_section_from_resume("resume.open_source_contributions")
    return (
        f"Open Source Contributions Section:\n{content}"
        if content
        else "No content found for open source contributions section."
    )


@app.tool(
    name="get_kaggle_competitions_section",
    description="Get the Kaggle competitions section from the resume YAML file.",
)
def get_kaggle_competitions_section():
    content = get_section_from_resume("resume.kaggle_competitions")
    return (
        f"Kaggle Competitions Section:\n{content}"
        if content
        else "No content found for Kaggle competitions section."
    )


@app.tool(
    name="get_competitive_programming_section",
    description="Get the competitive programming section from the resume YAML file.",
)
def get_competitive_programming_section():
    content = get_section_from_resume("resume.competitive_programming")
    return (
        f"Competitive Programming Section:\n{content}"
        if content
        else "No content found for competitive programming section."
    )


@app.tool(
    name="get_scholarships_section",
    description="Get the scholarships section from the resume YAML file.",
)
def get_scholarships_section():
    content = get_section_from_resume("resume.scholarships")
    return (
        f"Scholarships Section:\n{content}"
        if content
        else "No content found for scholarships section."
    )


# ------------------ About Me Tools (YAML as source of truth) ------------------


@app.tool(
    name="about_me_brief",
    description="Return a short, easy bio about Dinesh Chhantyal (name, location, one-line summary, and key contacts) from YAML.",
)
def about_me_brief():
    return _about_me_brief_text()


@app.tool(
    name="about_me_detailed",
    description="Return a detailed overview about Dinesh Chhantyal with education, highlights of experience, skills, and selected projects from YAML.",
)
def about_me_detailed():
    return _about_me_detailed_text()


@app.tool(
    name="about_me_answer",
    description="Answer natural-language questions about Dinesh using the YAML knowledge source. Routes to relevant sections automatically.",
)
def about_me_answer(question: str):
    q = (question or "").lower()
    # Simple routing based on keywords; YAML is the source of truth.
    if any(
        k in q
        for k in [
            "contact",
            "email",
            "phone",
            "linkedin",
            "github",
            "website",
            "where are you",
            "location",
        ]
    ):
        return get_personal_section()
    if any(
        k in q
        for k in [
            "summary",
            "bio",
            "about you",
            "about me",
            "who is dinesh",
            "who are you",
            "dinesh chhantyal",
        ]
    ):
        return about_me_brief()
    if any(k in q for k in ["education", "degree", "gpa", "university", "school"]):
        return get_section_from_resume("resume.education") or "No education info found."
    if any(k in q for k in ["experience", "work", "intern", "job", "employment"]):
        return get_experience_section()
    if any(k in q for k in ["project", "projects", "portfolio", "built"]):
        return get_projects_section()
    if any(k in q for k in ["skill", "skills", "tech", "stack"]):
        return get_skills_section()
    if any(k in q for k in ["award", "awards", "honor", "recognition"]):
        return get_awards_section()
    if any(k in q for k in ["cert", "certification", "certifications"]):
        return get_certifications_section()
    if any(k in q for k in ["leadership", "involvement", "club", "organization"]):
        return get_involvements_section()
    if any(k in q for k in ["kaggle", "competition", "leaderboard"]):
        return get_kaggle_competitions_section()
    if any(k in q for k in ["competitive programming", "icpc", "coding contest"]):
        return get_competitive_programming_section()
    if any(k in q for k in ["scholarship", "scholarships"]):
        return get_scholarships_section()
    # Fallback to generic QA over YAML dump
    return ask_resume_question(question)


# ------------------ Refinement Tools ------------------


@app.tool(
    name="experience_tool",
    description="Refine experience section based on job description",
)
def experience_tool(job_description: str, resume_experience: str) -> str:
    return f"""
You are a professional resume editor. Your task is to rewrite the candidate's experience section to align with the following job description:

Job Description:
{job_description}

Candidate’s Experience:
{resume_experience}

Instructions:
- Emphasize experience that directly relates to the role.
- Highlight accomplishments using metrics, technologies, or business outcomes.
- Use strong action verbs and concise bullet points.
- Remove unrelated or redundant content.
- Maintain professional tone.

Return ONLY the improved experience section.
"""


@app.tool(
    name="summary_tool", description="Refine summary section based on job description"
)
def summary_tool(job_description: str, summary: str) -> str:
    return f"""
You are a resume summary specialist. Improve the candidate's professional summary based on this job description:

Job Description:
{job_description}

Current Summary:
{summary}

Instructions:
- Keep it concise and impactful (2-3 sentences).
- Align it with the job's key qualifications.
- Emphasize key skills or experiences.

Return ONLY the improved summary.
"""


@app.tool(
    name="projects_tool", description="Refine projects section based on job description"
)
def projects_tool(job_description: str, projects: str) -> str:
    return f"""
Revise the following projects section to better match the job description below:

Job Description:
{job_description}

Projects:
{projects}

Instructions:
- Highlight relevant technologies and outcomes.
- Focus on relevance to the job.
- Keep it action- and impact-oriented.

Return ONLY the revised projects section.
"""


@app.tool(
    name="involvements_tool",
    description="Refine involvements section based on job description",
)
def involvements_tool(job_description: str, involvements: str) -> str:
    return f"""
You are refining the candidate’s involvements section for the job below:

Job Description:
{job_description}

Involvements:
{involvements}

Instructions:
- Focus on leadership, teamwork, or initiatives that match the job’s values.
- Emphasize transferable skills and impact.

Return ONLY the improved involvements section.
"""


@app.tool(
    name="skills_tool", description="Refine skills section based on job description"
)
def skills_tool(job_description: str, skills: str) -> str:
    return f"""
Update the skills section to prioritize skills listed in the job description:

Job Description:
{job_description}

Current Skills:
{skills}

Instructions:
- Prioritize hard/technical skills relevant to the job.
- Maintain readability (comma-separated or bulleted).
- Remove outdated or irrelevant skills.

Return ONLY the revised skills list.
"""


# ------------------ Generic QA Tool ------------------


@app.tool(
    name="ask_resume_question",
    description="Ask any question about the resume and get an answer.",
)
def ask_resume_question(question: str):
    full_text = get_section_from_resume("all")
    return f"""
You are a resume assistant. Here's the full resume:

{full_text}

Question: {question}

Please answer concisely and based only on the resume.
"""


# ------------------ XML Extractor Tools (optional, fallback only) ------------------


@app.tool(
    name="get_xml_personal",
    description="Extract personal/contact info from knowledge_source.xml (fallback; YAML is the source of truth).",
)
def get_xml_personal():
    root = _xml_root()
    if root is None:
        return "XML not available."
    personal = root.find("personal")
    if personal is None:
        return "No personal info in XML."
    fields = [
        ("name", personal.findtext("name", default="")),
        ("location", personal.findtext("location", default="")),
        ("phone", personal.findtext("phone", default="")),
        ("email", personal.findtext("email", default="")),
        ("website", personal.findtext("website", default="")),
        ("linkedin", personal.findtext("linkedin", default="")),
        ("github", personal.findtext("github", default="")),
    ]
    lines = [f"{k}: {v}" for k, v in fields if v]
    return "\n".join(lines) if lines else "No personal fields populated in XML."


@app.tool(
    name="get_xml_summary",
    description="Extract the summary from knowledge_source.xml (fallback; YAML is primary).",
)
def get_xml_summary():
    root = _xml_root()
    if root is None:
        return "XML not available."
    summary = root.findtext("summary", default="").strip()
    return summary or "No summary in XML."


@app.tool(
    name="get_xml_experience_titles",
    description="List experience titles and companies from knowledge_source.xml (fallback).",
)
def get_xml_experience_titles():
    root = _xml_root()
    if root is None:
        return "XML not available."
    exp = root.find("experience")
    if exp is None:
        return "No experience in XML."
    rows = []
    for job in exp.findall("job"):
        title = (job.findtext("title") or "").strip()
        company = (job.findtext("company") or "").strip()
        if title or company:
            rows.append(" - ".join([p for p in [title, company] if p]))
    return "\n".join(rows) if rows else "No job titles found in XML."


@app.tool(
    name="get_xml_projects_names",
    description="List project placeholders/names from knowledge_source.xml (fallback).",
)
def get_xml_projects_names():
    root = _xml_root()
    if root is None:
        return "XML not available."
    projects = root.find("projects")
    if projects is None:
        return "No projects in XML."
    names = []
    for proj in projects.findall("project"):
        # Some entries may lack name; attempt to read a <name> node if present
        name_node = proj.findtext("name")
        if name_node and name_node.strip():
            names.append(name_node.strip())
    return "\n".join(names) if names else "No project names in XML."


@app.tool(
    name="get_xml_skill_categories",
    description="List skill category names from knowledge_source.xml (fallback).",
)
def get_xml_skill_categories():
    root = _xml_root()
    if root is None:
        return "XML not available."
    skills = root.find("skills")
    if skills is None:
        return "No skills in XML."
    cats = []
    for sc in skills.findall("skill_category"):
        name = sc.attrib.get("name", "").strip()
        if name:
            cats.append(name)
    return "\n".join(cats) if cats else "No skill categories in XML."


# ------------------ Refine All ------------------


@app.tool(
    name="refine_all",
    description="Refine multiple resume sections using a job description.",
)
def refine_all(
    job_description: str,
    experience: str = "",
    projects: str = "",
    involvements: str = "",
    skills: str = "",
    summary: str = "",
):
    output = {}
    if summary:
        output["summary"] = summary_tool(job_description, summary)
    if experience:
        output["experience"] = experience_tool(job_description, experience)
    if projects:
        output["projects"] = projects_tool(job_description, projects)
    if involvements:
        output["involvements"] = involvements_tool(job_description, involvements)
    if skills:
        output["skills"] = skills_tool(job_description, skills)
    return output


if __name__ == "__main__":
    app.run(transport="stdio")
