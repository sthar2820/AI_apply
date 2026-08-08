import yaml
import os
import subprocess
from datetime import datetime
from generators.base import DocumentGenerator


class ResumeGenerator(DocumentGenerator):
    def __init__(self, yaml_file):
        super().__init__(yaml_file)
        self.yaml_file = yaml_file  # Store the yaml_file path
        with open(yaml_file, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)
        self.latex_preamble = self.get_latex_preamble()

    def get_latex_preamble(self):
        """Returns the LaTeX preamble with all package imports and custom commands"""
        personal = getattr(self, 'data', {}).get("personal", {})
        name = personal.get("name", "Professional Resume")

        return (
            r"""\documentclass[letterpaper,10pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{setspace}
\usepackage[T1]{fontenc}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
% ATS-friendly packages
\input{glyphtounicode}
\pdfgentounicode=1
\usepackage{accsupp}
\usepackage[hidelinks,pdfusetitle]{hyperref}
\hypersetup{
  pdftitle={Professional Resume},
  pdflang={en-US},
  pdfcreator={pdfLaTeX},
  pdfduplex={Simplex},
  pdftoolbar=false,
  pdffitwindow=true,
  pdfnewwindow=true,
  colorlinks=false,
  linktoc=all,
  pdfpagemode=UseNone,
  pdfdisplaydoctitle=true,
  pdfborder={0 0 0}
}

% Add PDF metadata for ATS systems using hypersetup instead of pdfinfo
\hypersetup{
  pdftitle={"""
            + name
            + r""" - Professional Resume},
  pdfsubject={Professional Experience and Qualifications},
  pdfkeywords={resume, qualifications, skills, experience, professional}
}

% Page setup
\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Margins: balanced top/bottom (0.3in) and standard side (0.5in) per user pref
% Smaller top/bottom buys budget for inter-bullet breathing room in Experience
\usepackage[top=0.3in,bottom=0.3in,left=0.5in,right=0.5in]{geometry}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Section formatting (industry standard \large smallcaps per Jake template)
% Small inter-section breathing room via less negative pre-section vspace
\titleformat{\section}{
  \vspace{-2pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Custom commands
\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{1pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{\small#1} & \small#2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-5pt}
}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}
"""
        )

    def escape_latex(self, text):
        """Escape special LaTeX characters"""
        if not isinstance(text, str):
            text = str(text)

        # Define replacements in order of precedence
        replacements = [
            ("#", "\\#"),  # Escape the # character
            ("&", "\\&"),
            # Only escape % if it's not already escaped
            ("\\%", "PERCENT_PLACEHOLDER"),  # Temporarily replace already escaped %
            ("%", "\\%"),
            ("PERCENT_PLACEHOLDER", "\\%"),  # Restore already escaped %
            # ('$', '\\$'),
            ("_", "\\_"),
            # ('{', '\\{'),
            # ('}', '\\}'),
            ("~", "\\textasciitilde{}"),
            # ('^', '\\textasciicircum{}'),
            ("<", "\\textless{}"),
            (">", "\\textgreater{}"),
            ("|", "\\textbar{}"),
            ('"', "''"),
            ("...", "\\ldots{}"),
            ("−", "-"),  # Replace en-dash with hyphen
            ("–", "-"),  # Replace em-dash with hyphen
        ]

        # Apply replacements
        for old, new in replacements:
            text = text.replace(old, new)

        # Fix ATS spacing: replace \textbf{word} with {\bfseries word}
        # to preserve word boundaries in PDF text extraction
        import re
        text = re.sub(r'\\textbf\{([^}]*)\}', r'{\\bfseries \1}', text)

        return text

    def generate_header(self, personal):
        """Generate the header section with personal information"""
        return f"""\\begin{{center}}
        \\textbf{{\\LARGE {self.escape_latex(personal['name'])}}} \\\\ \\vspace{{0.2pt}}
        \\small {self.escape_latex(personal['phone'])} $|$
        \\href{{mailto:{self.escape_latex(personal['email'])}}}{{{self.escape_latex(personal['email'])}}} $|$
        \\href{{{self.escape_latex(personal['website'])}}}{{{self.escape_latex(personal['website'].replace('https://www.', ''))}}} $|$
        \\href{{{self.escape_latex(personal['linkedin'])}}}{{{self.escape_latex(personal['linkedin'].replace('https://', ''))}}}
        $|$
        {self.escape_latex(personal['location'])}
    \\end{{center}}
    """

    def generate_education(self, education):
        """Generate the education section"""
        content = []
        content.append("\\section*{\\textbf{Education}}")
        content.append("\\resumeSubHeadingListStart")

        for school in education or []:
            if not isinstance(school, dict):
                continue
            content.append("\\resumeSubheading")
            name = school.get('name', '')
            location = school.get('location', '')
            degree = school.get('degree', '')
            gpa = school.get('GPA', '')
            date = school.get('date', '')
            courses = school.get('courses')
            content.append(f"{{{name}}}{{{location}}}")
            degree_line = f"{degree}, {{GPA: {gpa}}}" if gpa else degree
            content.append(
                f"{{{degree_line}}}{{{date}}}"
            )

            if courses:
                content.append("\\resumeItemListStart")
                content.append(f"\\resumeItem{{{courses}}}")
                content.append("\\resumeItemListEnd")

        content.append("\\resumeSubHeadingListEnd")
        return "\n".join(content)

    def generate_experience(self, experience):
        """Generate the experience section"""
        content = []
        content.append("\\section*{\\textbf{Experience}}")
        content.append("\\resumeSubHeadingListStart")

        for job in experience or []:
            if not isinstance(job, dict):
                continue
            content.append("\\resumeSubheading")
            title = self.escape_latex(job.get('title', ''))
            date = job.get('date', '')
            company = self.escape_latex(job.get('company', ''))
            location = self.escape_latex(job.get('location', ''))
            content.append(f"{{{title}}}{{{date}}}")
            content.append(f"{{{company}}}{{{location}}}")

            content.append("\\resumeItemListStart")
            for achievement in (job.get("achievements") or []):
                # Remove any leading dash and whitespace for clean bulleting
                achievement_clean = achievement.lstrip("- ").strip()
                escaped_achievement = self.escape_latex(achievement_clean)
                content.append(f"\\resumeItem{{{escaped_achievement}}}")
            content.append("\\resumeItemListEnd")

            # Uniform 1pt breathing (matches projects + skills for consistency)
            content.append("\\vspace{1pt}")

        content.append("\\resumeSubHeadingListEnd")
        return "\n".join(content)

    def generate_projects(self, projects):
        """Generate the projects section"""
        content = []
        content.append("\\section*{\\textbf{Projects}}")
        content.append("\\resumeItemListStart{}")
        for project in projects or []:
            if not isinstance(project, dict):
                continue
            name = self.escape_latex(project.get("name", ""))
            description = self.escape_latex(project.get("description", ""))
            link = project.get("link")
            if link:
                # Make the project name itself a hyperlink (no visual indication in PDF)
                item = f"\\resumeItem{{\\href{{{link}}}{{\\textbf{{{name}}}}} $|$ {description}}}"
            else:
                item = f"\\resumeItem{{\\textbf{{{name}}} $|$ {description}}}"
            content.append(item)
            # Uniform 1pt breathing (matches roles + skills for consistency)
            content.append("\\vspace{1pt}")
        content.append("\\resumeItemListEnd")
        return "\n".join(content)

    def generate_skills(self, skills):
        """Generate the skills section"""
        content = []
        content.append("\\section*{\\textbf{Skills}}")
        content.append("\\begin{itemize}[leftmargin=0.15in, label={}, itemsep=1pt, topsep=0pt, parsep=0pt]")

        for category in skills or []:
            if not isinstance(category, dict):
                continue
            name = self.escape_latex(category.get("name", ""))
            items = self.escape_latex(category.get("items", ""))
            # Prevent double escaping on pre-escaped ampersands (e.g., "\&" in YAML)
            name = name.replace("\\\\&", "\\&")
            items = items.replace("\\\\&", "\\&")
            content.append(f"\\item \\textbf{{{name}}}: {items}")

        content.append("\\end{itemize}")
        return "\n".join(content)

    def extract_keywords(self):
        """Extract potential keywords from skills and experience for ATS optimization"""
        keywords = set()
        import re

        # Extract from skills
        for skill_category in self.data.get("skills", []):
            # Split by commas and clean up
            skills = [s.strip() for s in skill_category["items"].split(",")]
            keywords.update(skills)

        # Extract job titles and company names
        for job in self.data.get("experience", []):
            keywords.add(job["title"])
            keywords.add(job["company"])

            # Extract technical terms from achievements
            for achievement in job["achievements"]:
                # Find words in textbf that are likely technical terms
                tech_terms = re.findall(r"\\textbf\{([^}]+)\}", achievement)
                keywords.update(tech_terms)

                # Also extract important tech and numerical metrics
                tech_matches = re.findall(
                    r"\b(?:[A-Z][A-Za-z0-9./+_-]+|[0-9]+[xX]|\d+%|\d+[KkMmGgTt][Bb])\b",
                    achievement,
                )
                keywords.update(tech_matches)

                # Add common action verbs that ATS systems look for
                action_verbs = [
                    "led",
                    "managed",
                    "developed",
                    "created",
                    "designed",
                    "implemented",
                    "built",
                    "optimized",
                    "improved",
                    "reduced",
                    "increased",
                    "achieved",
                    "deployed",
                    "architected",
                    "streamlined",
                    "collaborated",
                    "coordinated",
                ]
                for verb in action_verbs:
                    if re.search(r"\b" + verb + r"\b", achievement.lower()):
                        keywords.add(verb.capitalize())

        # Add project technologies
        for project in self.data.get("projects", []):
            description = project.get("description", "")
            tech_terms = re.findall(r"\\textbf\{([^}]+)\}", description)
            keywords.update(tech_terms)

            # Extract other tech terms and metrics from projects
            tech_matches = re.findall(
                r"\b(?:[A-Z][A-Za-z0-9./+_-]+|[0-9]+[xX]|\d+%|\d+[KkMmGgTt][Bb])\b",
                description,
            )
            keywords.update(tech_matches)

        # Filter out common non-technical terms and short terms
        filtered_keywords = [
            k
            for k in keywords
            if len(k) > 2
            and not k.lower() in {"the", "and", "with", "for", "from", "that", "this"}
        ]

        return sorted(filtered_keywords)

    def generate_keywords_section(self):
        """Generate a hidden keywords section for ATS optimization"""
        keywords = self.extract_keywords()
        if not keywords:
            return ""

        content = []
        # Hidden section not visible in the PDF but readable by ATS
        content.append("\\begin{comment}")
        content.append("Keywords for ATS Optimization:")
        # Join keywords with commas for better ATS parsing
        keywords_text = ", ".join([self.escape_latex(k) for k in keywords])
        content.append(keywords_text)
        content.append("\\end{comment}")
        return "\n".join(content)

    def generate_certifications(self, certifications):
        """Generate the certifications section"""
        content = []
        content.append("\\section*{\\textbf{Certifications}}")
        content.append("\\resumeItemListStart{}")
        for cert in certifications:
            title = self.escape_latex(cert.get("title") or cert.get("name", ""))
            issuer = self.escape_latex(cert.get("issuer", ""))
            date = self.escape_latex(cert.get("date", ""))

            issuer_part = f", {issuer}" if issuer else ""
            formatted_cert = (
                f"\\resumeItem{{"
                f"\\textbf{{{title}}}{issuer_part} "
                f"\\hfill {date}"
                f"}}"
            )

            content.append(formatted_cert)
        content.append("\\resumeItemListEnd")
        return "\n".join(content)

    def generate_leadership(self, leadership, awards=None):
        """Generate the leadership section with optional awards"""
        content = []
        content.append("\\section*{\\textbf{Leadership \\& Awards}}")
        content.append("\\resumeItemListStart{}")

        for item in leadership or []:
            name = self.escape_latex(item.get("name", ""))
            description = (
                self.escape_latex(item.get("description", ""))
                if "description" in item
                else ""
            )
            date = self.escape_latex(item.get("date", ""))

            if description:
                formatted_item = (
                    f"\\resumeItem{{"
                    f"\\textbf{{{name}}} "
                    f"\\hfill {date}\\\\"
                    f"{description}"
                    f"}}"
                )
            else:
                formatted_item = (
                    f"\\resumeItem{{"
                    f"\\textbf{{{name}}} "
                    f"\\hfill {date}"
                    f"}}"
                )

            content.append(formatted_item)

        titles = []
        for award in awards or []:
            if not isinstance(award, dict):
                continue
            title = award.get("title")
            if title:
                titles.append(self.escape_latex(title))

        if titles:
            joined_titles = ", ".join(titles)
            content.append(
                f"\\resumeItem{{\\textbf{{Awards}}: {joined_titles}}}"
            )

        content.append("\\resumeItemListEnd")
        return "\n".join(content)

    def generate_activities(self, activities):
        """Generate the activities section"""
        content = []
        content.append("\\section*{\\textbf{Activities \\& Club Involvement}}")
        content.append("\\resumeItemListStart{}")
        for activity in activities:
            name = self.escape_latex(activity["name"])
            description = (
                self.escape_latex(activity["description"])
                if "description" in activity
                else ""
            )
            date = self.escape_latex(activity["date"])

            formatted_activity = (
                f"\\resumeItem{{"
                f"\\textbf{{{name}}} "  # Bold name
                f"\\hfill {date}\\\\"  # Right-aligned date
                f"{description}"  # Description on new line
                f"}}"
            )

            content.append(formatted_activity)
        content.append("\\resumeItemListEnd")
        return "\n".join(content)

    def generate_resume(self, yaml_file):
        """Generate the complete LaTeX resume from YAML"""
        # Optional sections
        summary_text = self.data.get("summary")
        activities = self.data.get("activities", [])
        leadership = self.data.get("leadership", [])
        certifications = self.data.get("certifications", [])
        awards = self.data.get("awards", [])

        content = [
            self.latex_preamble,
            "\\begin{document}",
            self.generate_header(self.data.get("personal", {})),
        ]

        if summary_text:
            content.append("\\section*{\\textbf{Summary}}")
            content.append("\\small{" + self.escape_latex(summary_text.strip()) + "}")

        # Cofounder / Founding-Engineer order per [[feedback_resume_bullet_patterns_research]]:
        # Summary -> Experience -> Projects -> Skills -> Education -> Leadership
        # Cofounder evidence outranks school for AI startup / non-FAANG audiences.
        content.extend(
            [
                self.generate_experience(self.data.get("experience", [])),
                self.generate_projects(self.data.get("projects", [])),
                self.generate_skills(self.data.get("skills", [])),
                self.generate_education(self.data.get("education", [])),
            ]
        )

        # Add certifications section if present
        if certifications:
            content.append(self.generate_certifications(certifications))

        # Add leadership section if present
        if leadership or awards:
            content.append(self.generate_leadership(leadership, awards))

        # Add activities section if present (for backward compatibility)
        if activities:
            content.append(self.generate_activities(activities))

        # Add keywords section for ATS optimization (invisible in rendered PDF)
        content.append(self.generate_keywords_section())

        content.append("\\end{document}")

        return "\n\n".join(content)

    def save_resume(self, yaml_file, output_file_path):
        """Save the generated LaTeX resume to a specific file"""
        output_dir = os.path.dirname(output_file_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        latex_content = self.generate_resume(yaml_file)
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(latex_content)

        return output_file_path

    def compile_pdf(self, tex_file):
        """Compile LaTeX file to PDF using pdflatex with ATS-friendly settings"""
        try:
            # Get the directory containing the tex file
            output_dir = os.path.dirname(tex_file)

            # Try to find pdflatex in common locations
            pdflatex_paths = [
                "pdflatex",  # If it's in PATH
                "/usr/local/texlive/2024/bin/universal-darwin/pdflatex",
                "/usr/local/texlive/2024/bin/x86_64-darwin/pdflatex",
                "/Library/TeX/texbin/pdflatex",
            ]

            pdflatex_cmd = None
            for path in pdflatex_paths:
                if os.path.exists(path) or path == "pdflatex":
                    try:
                        subprocess.run(
                            [path, "--version"], check=True, capture_output=True
                        )
                        pdflatex_cmd = path
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

            if not pdflatex_cmd:
                raise Exception(
                    "pdflatex not found. Please install LaTeX (MacTeX) or add it to PATH"
                )

            # Run pdflatex twice to ensure proper generation of references
            for _ in range(2):
                subprocess.run(
                    [
                        pdflatex_cmd,
                        "-interaction=nonstopmode",
                        "-output-directory=" + output_dir,
                        # ATS-friendly settings - remove -dPDFA flag since it's causing issues
                        tex_file,
                    ],
                    check=True,
                    capture_output=True,
                )

            # Clean up auxiliary files
            base_name = os.path.splitext(tex_file)[0]
            for ext in [".aux", ".log", ".out"]:
                aux_file = base_name + ext
                if os.path.exists(aux_file):
                    os.remove(aux_file)

            pdf_file = base_name + ".pdf"
            if os.path.exists(pdf_file):
                return pdf_file
            else:
                raise Exception("PDF file was not generated")

        except subprocess.CalledProcessError as e:
            print(f"Error during PDF compilation: {e}")
            print(f"LaTeX output: {e.output.decode()}")
            raise
        except Exception as e:
            print(f"Error: {str(e)}")
            raise

    def generate_pdf(self, output_file_path, output_dir="output"):
        """Generate both LaTeX and PDF files from YAML with custom filename"""
        try:
            # Use the provided output file path for the final PDF
            base_name = os.path.splitext(output_file_path)[0]
            tex_file = base_name + ".tex"
            
            # Generate LaTeX content
            latex_content = self.generate_resume(self.yaml_file)
            
            # Write LaTeX file
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # Compile to PDF
            pdf_file = self.compile_pdf(tex_file)

            # Delete the tex file
            if os.path.exists(tex_file):
                os.remove(tex_file)

            return pdf_file

        except Exception as e:
            print(f"Failed to generate PDF: {str(e)}")
            raise

    def generate_tex(self):
        """
        Implement the abstract method from DocumentGenerator.
        This method generates the complete text content of the resume.
        """
        return self.generate_resume(self.yaml_file)


if __name__ == "__main__":
    try:
        generator = ResumeGenerator()
        tex_file, pdf_file = generator.generate_pdf("resume.yml")
    except Exception as e:
        print(f"Failed to generate resume: {str(e)}")
